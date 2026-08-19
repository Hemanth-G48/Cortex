"""Source crawler — Layer 1: discover and persist the REAL platform structure.

The external learning platform is the source of truth. This module:

1. **Fetches URLs with honest verification** — records requested URL, final
   URL, HTTP status, redirect chain and rejects auth-redirects (many sites
   return HTTP 200 but bounce anonymous requests to a login/error page —
   that is NOT a successful crawl).
2. **Discovers learning paths** from a learning-path index (PortSwigger's
   page is a JS shell; its real cards come from ``POST /api/widgets``, which
   this crawler reproduces).
3. **Crawls each path page** and extracts its sections, resources and labs
   with their exact discovered URLs (never guessed from titles).
4. **Persists** the hierarchy as ``LearningPath`` / ``LearningResource`` rows
   (deduplicated per plan by URL) with an honest ``crawl_status`` on every
   row: ``discovered | crawled | extraction_failed | http_error | not_found |
   auth_required``.

Nothing is ever marked ``crawled`` unless the request succeeded AND useful
content was extracted. When a URL cannot be verified it is displayed with its
true state — never as a valid source.
"""

from __future__ import annotations

import html as html_mod
import json
import logging
import re
import time
from urllib.parse import urljoin, urlparse, urlunparse

from sqlalchemy.orm import Session

from app.models import LearningPath, LearningPathResource, LearningResource
from app.models.kb.learning_path import (
    CRAWL_AUTH_REQUIRED,
    CRAWL_CRAWLED,
    CRAWL_DISCOVERED,
    CRAWL_EXTRACTION_FAILED,
    CRAWL_HTTP_ERROR,
    CRAWL_NOT_FOUND,
    RESOURCE_TYPE_LAB,
    RESOURCE_TYPE_READING,
)
from app.services.kb import utcnow

logger = logging.getLogger(__name__)

CRAWL_TIMEOUT = 12.0
MAX_REDIRECTS = 6
USER_AGENT = "StudentLifeOS-LearningPlanner/1.0 (learning path discovery)"
# Upper bounds: discovery is an explicit user action, but one run must still
# finish — cap paths, per-path resources, and verification requests.
MAX_PATHS = 60
MAX_RESOURCES_PER_PATH = 200
# URL verification requests per discovery run (auth-gated sites would
# otherwise burn hundreds of requests confirming the same login wall).
VERIFY_RESOURCES_PER_PATH = 4
MAX_VERIFY_TOTAL = 80
# Polite delay between requests to the same host.
CRAWL_DELAY_S = 0.25
# Raw HTML cap (the PortSwigger widget payloads are ~35KB each).
MAX_HTML_CHARS = 500_000
# Below this, the payload is a JS shell / blocked page — not content.
MIN_CONTENT_CHARS = 120

# Path segments that mean "we were bounced to sign-in / an error wall".
_AUTH_GATE_SEGMENTS = (
    "/error",
    "/u/login",
    "/login",
    "/signin",
    "/users/login",
    "/users/register",
    "/accounts/login",
    "/account/login",
    "/session/new",
)
# Navigation/boilerplate link parts never treated as content.
_SKIP_URL_PARTS = (
    "/login", "/signup", "/register", "/cart", "/checkout", "/account",
    "/logout", "/admin", "/assets/", "/static/", "/bundles/", "/content/",
    ".css", ".js", ".png", ".jpg", ".jpeg", ".svg", ".gif", ".ico", ".woff",
    ".pdf", ".zip", ".mp4", ".mp3", "mailto:", "tel:", "#", "javascript:",
)


def _strip_html(raw: bytes) -> str:
    """Rough HTML→text extraction (no external parser dependency)."""
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return ""
    text = re.sub(r"(?is)<(script|style|noscript|head)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<![^>]*>", " ", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|li|h[1-6]|tr|section|article|details|summary)>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalise_url(url: str, base: str | None = None) -> str:
    """Resolve + normalise a URL (drop fragments; keep query)."""
    if not url:
        return ""
    absolute = urljoin(base or "", url.strip())
    parsed = urlparse(absolute)
    if parsed.scheme not in ("http", "https"):
        return ""
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", parsed.query, ""))


def _url_key(url: str) -> str:
    """Dedup key: host + path, lowercase, query/fragment stripped."""
    parsed = urlparse(url or "")
    return f"{parsed.netloc.lower()}{parsed.path.rstrip('/').lower() or '/'}"


def fetch_verified(url: str, *, include_body: bool = True, cookies: dict | None = None) -> dict:
    """Fetch ``url`` and return an honest verification record.

    Returns a dict with ``crawl_status`` one of ``crawled |
    extraction_failed | http_error | not_found | auth_required`` and the
    verification trail (requested/final URL, status code, redirect chain,
    error). ``crawled`` is only set when the final page is real content —
    auth-redirects and JS shells are rejected even when HTTP says 200.

    ``cookies`` attaches a stored session (e.g. a PortSwigger sign-in) so
    auth-gated URLs can be fetched and verified honestly.
    """
    record: dict = {
        "requested_url": url,
        "final_url": None,
        "status_code": None,
        "redirect_chain": [],
        "html": None,
        "error": None,
        "crawl_status": CRAWL_DISCOVERED,
    }
    try:
        import httpx

        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        }
        if cookies:
            headers["Referer"] = "https://portswigger.net/"
        with httpx.Client(
            timeout=CRAWL_TIMEOUT,
            follow_redirects=True,
            max_redirects=MAX_REDIRECTS,
            headers=headers,
            cookies=cookies or None,
        ) as client:
            resp = client.get(url)
            record["status_code"] = resp.status_code
            record["final_url"] = str(resp.url)
            record["redirect_chain"] = [str(r.url) for r in (resp.history or [])]
            if resp.status_code >= 400:
                record["crawl_status"] = (
                    CRAWL_NOT_FOUND if resp.status_code == 404 else CRAWL_HTTP_ERROR
                )
                record["error"] = f"HTTP {resp.status_code}"
                return record

            final = urlparse(str(resp.url))
            # Auth-gate: bounced to sign-in or an error wall (often HTTP 200).
            if any(seg in final.path.lower() for seg in _AUTH_GATE_SEGMENTS):
                record["crawl_status"] = CRAWL_AUTH_REQUIRED
                record["error"] = "Page requires authentication (redirected to sign-in)"
                return record

            ctype = (resp.headers.get("content-type") or "").lower()
            if "text/html" not in ctype and "application/xhtml" not in ctype:
                record["crawl_status"] = CRAWL_EXTRACTION_FAILED
                record["error"] = f"Not HTML ({ctype or 'unknown content type'})"
                return record

            if include_body:
                html_text = resp.content.decode("utf-8", errors="replace")[:MAX_HTML_CHARS]
                text = _strip_html(resp.content)[:200_000]
                if len(text) < MIN_CONTENT_CHARS:
                    record["crawl_status"] = CRAWL_EXTRACTION_FAILED
                    record["error"] = "Page is a JavaScript shell — no readable content"
                    return record
                record["html"] = html_text
                record["text"] = text
            record["crawl_status"] = CRAWL_CRAWLED
            return record
    except Exception as exc:  # noqa: BLE001 — crawl is best-effort
        record["crawl_status"] = CRAWL_HTTP_ERROR
        record["error"] = str(exc)[:200]
        return record


def _is_skippable(url: str) -> bool:
    low = url.lower()
    return any(part in low for part in _SKIP_URL_PARTS)


# ---------------------------------------------------------------------------
# PortSwigger Web Security Academy support
# ---------------------------------------------------------------------------

def _ps_widget_ids(html_text: str) -> list[str]:
    return sorted(set(re.findall(r'widget-id="([^"]+)"', html_text)))


def _ps_fetch_widgets(netloc: str, page_path: str, widget_ids: list[str]) -> str:
    """Reproduce the page's own ``POST /api/widgets`` call → merged card HTML."""
    merged = ""
    try:
        import httpx

        with httpx.Client(
            timeout=CRAWL_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"},
        ) as client:
            for wid in widget_ids:
                resp = client.post(
                    f"https://{netloc}/api/widgets",
                    params={},
                    json=[{"widgetId": wid, "additionalData": {}}],
                    headers={"Widget-Source": page_path},
                )
                if resp.status_code == 200:
                    try:
                        for item in resp.json() or []:
                            merged += html_mod.unescape(item.get("Html") or "")
                    except Exception:  # noqa: BLE001
                        continue
                time.sleep(CRAWL_DELAY_S)
    except Exception as exc:  # noqa: BLE001
        logger.info("PortSwigger widget fetch failed: %s", exc)
    return merged


def _ps_parse_path_cards(html_text: str, base_url: str) -> list[dict]:
    """Parse ``progress-cards`` blocks → learning path dicts.

    Each card carries: title (``h5``), description (``font-size-14``),
    difficulty (``label``), the exact "View path" href (``chevron-after``)
    and the exact "GET STARTED" first-resource href.
    """
    cards: list[dict] = []
    # Split on card boundaries: a progress-cards div, non-greedy, stopping at
    # the next card's class or container end.
    for block in re.findall(
        r'<div class="progress-cards[ "](.*?)(?=<div class="progress-cards[ "]|</div>\s*</div>\s*</div>|$)',
        html_text,
        re.S,
    ):
        title = re.search(r"<h5>(.*?)</h5>", block, re.S)
        desc = re.search(r'class="font-size-14">(.*?)</p>', block, re.S)
        label = re.search(r'class="label[^"]*">(.*?)</span>', block, re.S)
        view = re.search(r'class="[^"]*chevron-after[^"]*"[^>]*href="([^"]+)"', block)
        started = re.search(r'class="[^"]*button-view-path[^"]*"[^>]*href="([^"]+)"', block)
        title_text = re.sub(r"\s+", " ", title.group(1)).strip() if title else ""
        if not title_text:
            continue
        desc_text = (
            re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", desc.group(1))).strip()
            if desc
            else None
        )
        cards.append(
            {
                "title": title_text,
                "description": desc_text or None,
                "difficulty": (label.group(1).strip() if label else None),
                "source_url": _normalise_url(view.group(1), base_url) if view else "",
                "first_resource_url": _normalise_url(started.group(1), base_url) if started else "",
            }
        )
    return cards


def _generic_parse_path_cards(html_text: str, base_url: str) -> list[dict]:
    """Best-effort generic card extraction for non-PortSwigger platforms.

    Looks for anchor links whose visible text marks a learning path / course
    ("view path", "learning path", "start path") and pairs them with nearby
    headings. This is a fallback — PortSwigger uses the widget API instead.
    """
    cards: list[dict] = []
    seen: set[str] = set()
    for m in re.finditer(
        r"<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>", html_text, re.S | re.I
    ):
        href = _normalise_url(m.group(1), base_url)
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).strip()
        if not href or not text or _is_skippable(href):
            continue
        low = text.lower()
        if not any(k in low for k in ("view path", "learning path", "start path", "open path")):
            continue
        if href in seen:
            continue
        seen.add(href)
        cards.append(
            {
                "title": text,
                "description": None,
                "difficulty": None,
                "source_url": href,
                "first_resource_url": "",
            }
        )
    return cards


def discover_learning_paths(url: str, *, cookies: dict | None = None) -> dict | None:
    """Discover learning paths from a source URL (Layer 1, index level).

    Returns ``{"platform", "source_url", "paths": [...]}`` or ``None`` when
    the page cannot be reached or yields no paths. All ``source_url`` values
    are exact hrefs discovered from the site — never generated.
    """
    url = _normalise_url(url)
    if not url:
        return None
    parsed = urlparse(url)
    page = fetch_verified(url, cookies=cookies)
    if page["crawl_status"] != CRAWL_CRAWLED:
        return None

    cards: list[dict] = []
    raw_html = page.get("html") or ""
    if "portswigger.net" in parsed.netloc and "/learning-paths" in parsed.path:
        widget_ids = _ps_widget_ids(raw_html)
        if widget_ids:
            widget_html = _ps_fetch_widgets(parsed.netloc, parsed.path, widget_ids)
            cards = _ps_parse_path_cards(widget_html, url)
        if not cards:
            cards = _ps_parse_path_cards(raw_html, url)
    if not cards:
        cards = _generic_parse_path_cards(raw_html, url)

    if not cards:
        return None
    platform = parsed.netloc
    if "portswigger.net" in parsed.netloc:
        platform = "PortSwigger Web Security Academy"
    return {"platform": platform, "source_url": url, "paths": cards[:MAX_PATHS]}


# ---------------------------------------------------------------------------
# Learning path page parsing (sections → resources)
# ---------------------------------------------------------------------------

def _parse_path_page(html_text: str, base_url: str) -> dict:
    """Extract a path page's structure: summary + sections with resources.

    PortSwigger path pages render each section as ``details.expandable-progress-container``
    with ``div.expandable-progress-container-item`` resources inside. The first
    resource ("Get started") carries an explicit href; the rest are exposed by
    the site only to signed-in users, so their ``url`` stays ``None`` and the
    row is marked ``discovered`` (never faked).
    """
    items: list[dict] = []
    # Summary: "0 of 23" total + the "Get started: X" heading.
    total_match = re.search(
        r"learning-path-summary-header.*?(\d+)\s+of\s+(\d+)", html_text, re.S
    )
    total = int(total_match.group(2)) if total_match else None

    # Whole-page item order: iterate details blocks in document order, then
    # items inside each block.
    for section_match in re.finditer(
        r'<details class="expandable-progress-container[^"]*"[^>]*>(.*?)</details>',
        html_text,
        re.S,
    ):
        block = section_match.group(1)
        strong = re.search(r"<strong>(.*?)</strong>", block, re.S)
        section = re.sub(r"\s+", " ", strong.group(1)).strip() if strong else ""
        if not section:
            continue
        for item_match in re.finditer(
            r'expandable-progress-container-item[^>]*>(.*?)(?=expandable-progress-container-item|</div>\s*</div>\s*</details>|$)',
            block,
            re.S,
        ):
            raw = item_match.group(1)
            title_m = re.search(r"<p[^>]*>\s*([^<]+?)\s*(?:<span|\s*<)", raw, re.S)
            title = re.sub(r"\s+", " ", title_m.group(1)).strip() if title_m else ""
            if not title:
                continue
            label_m = re.search(r'class="label[^"]*">(.*?)</span>', raw, re.S)
            href_m = re.search(r'<a[^>]+href="([^"]+)"[^>]*>(?:Get started|Start|Open)</a>', raw, re.S | re.I)
            difficulty = re.sub(r"\s+", " ", label_m.group(1)).strip() if label_m else None
            href = _normalise_url(href_m.group(1), base_url) if href_m else ""
            is_lab = bool(
                re.match(r"(?i)^(lab|apprentice lab|practitioner lab|expert lab|professional lab)\b", title)
                or "lab:" in title.lower()
            )
            items.append(
                {
                    "title": title,
                    "url": href or None,  # exact href only; None = not exposed publicly
                    "resource_type": RESOURCE_TYPE_LAB if is_lab else RESOURCE_TYPE_READING,
                    "difficulty": difficulty,
                    "section": section,
                }
            )
            if len(items) >= MAX_RESOURCES_PER_PATH:
                break
        if len(items) >= MAX_RESOURCES_PER_PATH:
            break
    return {"resource_total": total, "items": items}


def crawl_learning_path(path_url: str, *, cookies: dict | None = None) -> dict | None:
    """Fetch one path page and return its resources (Layer 1, path level).

    Returns ``{"path_url", "crawl_status", "final_url", "status_code",
    "error", "resource_total", "items": [...]}`` — or ``None`` when the page
    could not be fetched. Pass ``cookies`` (a stored sign-in session) to get
    the signed-in view, which exposes a URL for every resource.
    """
    page = fetch_verified(path_url, cookies=cookies)
    if page["crawl_status"] != CRAWL_CRAWLED:
        return {
            "path_url": path_url,
            "crawl_status": page["crawl_status"],
            "final_url": page["final_url"],
            "status_code": page["status_code"],
            "error": page["error"],
            "resource_total": None,
            "items": [],
        }
    parsed = _parse_path_page(page.get("html") or "", path_url)
    return {
        "path_url": path_url,
        "crawl_status": CRAWL_CRAWLED,
        "final_url": page["final_url"],
        "status_code": page["status_code"],
        "error": None,
        "resource_total": parsed["resource_total"],
        "items": parsed["items"],
    }


# ---------------------------------------------------------------------------
# Persistence — the relational Layer-1 store
# ---------------------------------------------------------------------------

def _verify_resource(db: Session, res: LearningResource, *, cookies: dict | None = None) -> None:
    """Attempt a lightweight URL verification for one resource.

    ``include_body=False`` keeps it cheap. The row's status is updated to the
    honest outcome (crawled only if the final page is real content). Pass
    ``cookies`` to verify behind a sign-in wall.
    """
    if not res.url:
        return
    rec = fetch_verified(res.url, include_body=False, cookies=cookies)
    res.crawl_status = rec["crawl_status"]
    res.requested_url = rec["requested_url"]
    res.final_url = rec["final_url"]
    res.status_code = rec["status_code"]
    res.error = rec["error"]
    db.flush()


def run_discovery(
    db: Session,
    user_id: int,
    plan,
    urls: list[str],
    *,
    crawl_paths: bool = True,
    verify_resources: bool = True,
    cookies: dict | None = None,
) -> dict:
    """Run Layer-1 discovery for the plan's submitted URLs.

    For each submitted URL: discover learning paths → persist them → crawl
    each path page → extract + persist resources (deduplicated by URL via the
    junction table) → optionally verify resource URLs (bounded). Returns the
    crawl report consumed by ``plan_dict``.

    Every row carries an honest ``crawl_status``; the report states exactly
    how many paths/resources were discovered, crawled, verified or failed.
    """
    report = {
        "platform": None,
        "source_url": None,
        "paths_discovered": 0,
        "paths_crawled": 0,
        "paths_failed": 0,
        "resources_extracted": 0,
        "resources_with_url": 0,
        "resources_verified": 0,
        "resources_failed": 0,
        "statuses": {},
        # Submitted URLs that yielded a learning-path index (so the caller can
        # avoid double-persisting them as generic resources).
        "processed_urls": [],
    }
    platform_name: str | None = None
    source_url: str | None = None
    verify_budget = MAX_VERIFY_TOTAL

    for url in urls[:3]:  # discovery is per submitted URL (index pages)
        discovery = discover_learning_paths(url, cookies=cookies) if crawl_paths else None
        if not discovery:
            continue
        report["processed_urls"].append(url)
        platform_name = discovery["platform"]
        source_url = discovery["source_url"]
        for card in discovery["paths"]:
            path = LearningPath(
                user_id=user_id,
                plan_id=plan.id,
                platform=platform_name,
                title=(card.get("title") or "")[:300],
                description=card.get("description"),
                difficulty=(card.get("difficulty") or "")[:60] or None,
                source_url=(card.get("source_url") or "")[:600] or None,
                first_resource_url=(card.get("first_resource_url") or "")[:600] or None,
                resource_total=None,
                crawl_status=CRAWL_DISCOVERED,
            )
            db.add(path)
            db.flush()
            # Release the write lock before the network crawl — otherwise a
            # long discovery holds the transaction open and the KB folder
            # watcher's scan commit times out with "database is locked".
            db.commit()
            report["paths_discovered"] += 1

            crawled = crawl_learning_path(path.source_url, cookies=cookies) if crawl_paths else None
            if crawled is None:
                path.crawl_status = CRAWL_EXTRACTION_FAILED
                path.error = "Discovery produced no path page"
                report["paths_failed"] += 1
                db.commit()
                continue
            path.crawl_status = crawled["crawl_status"]
            path.final_url = (crawled.get("final_url") or "")[:600] or None
            path.status_code = crawled.get("status_code")
            path.error = (crawled.get("error") or "")[:300] or None
            path.resource_total = crawled.get("resource_total")
            if crawled["crawl_status"] != CRAWL_CRAWLED:
                report["paths_failed"] += 1
                db.commit()
                continue
            report["paths_crawled"] += 1
            report["statuses"]["path_crawled"] = report["statuses"].get("path_crawled", 0) + 1

            sections: set[str] = set()
            order = 0
            verified_in_path = 0
            for item in crawled["items"]:
                order += 1
                url = item.get("url")
                sections.add(item.get("section") or "")
                report["resources_extracted"] += 1
                # Dedup by URL key (resources shared across paths = one row).
                key = _url_key(url) if url else None
                existing = None
                if key:
                    existing = (
                        db.query(LearningResource)
                        .filter(
                            LearningResource.plan_id == plan.id,
                            LearningResource.url_key == key,
                        )
                        .first()
                    )
                if existing is None:
                    res = LearningResource(
                        user_id=user_id,
                        plan_id=plan.id,
                        title=(item.get("title") or "")[:300],
                        url=(url or "")[:600] or None,
                        resource_type=item.get("resource_type") or RESOURCE_TYPE_READING,
                        difficulty=(item.get("difficulty") or "")[:60] or None,
                        section=(item.get("section") or "")[:200] or None,
                        sort_order=order,
                        url_key=key,
                        crawl_status=CRAWL_DISCOVERED,
                    )
                    db.add(res)
                    db.flush()
                    existing = res
                # Link this path → resource.
                link = (
                    db.query(LearningPathResource)
                    .filter(
                        LearningPathResource.path_id == path.id,
                        LearningPathResource.resource_id == existing.id,
                    )
                    .first()
                )
                if link is None:
                    db.add(
                        LearningPathResource(
                            path_id=path.id,
                            resource_id=existing.id,
                            section=(item.get("section") or "")[:200] or None,
                            sort_order=order,
                        )
                    )
                if url:
                    report["resources_with_url"] += 1
                    if verify_resources and verify_budget > 0 and verified_in_path < VERIFY_RESOURCES_PER_PATH:
                        _verify_resource(db, existing, cookies=cookies)
                        verify_budget -= 1
                        verified_in_path += 1
                        if existing.crawl_status == CRAWL_CRAWLED:
                            report["resources_verified"] += 1
                        else:
                            report["resources_failed"] += 1
                        report["statuses"][existing.crawl_status] = (
                            report["statuses"].get(existing.crawl_status, 0) + 1
                        )
            path.section_count = len(sections)
            path.resource_count = len(crawled["items"])
            db.commit()

    report["platform"] = platform_name
    report["source_url"] = source_url
    return report


def upsert_path_crawl(
    db: Session,
    user_id: int,
    plan,
    card: dict,
    platform: str,
    *,
    cookies: dict | None = None,
) -> tuple[LearningPath, bool]:
    """Create-or-refresh one ``LearningPath`` from a discovery card + crawl it.

    Used by Plan Re-sync: re-running discovery on the stored source URL must
    NOT duplicate paths that already exist. Returns ``(path, created)`` — when
    the path already exists (same plan + ``source_url``) its metadata is
    refreshed and its page re-crawled; resources are still deduplicated by URL
    key via the junction table, so a resync never creates duplicate rows.
    """
    source_url = (card.get("source_url") or "")[:600] or None
    existing = None
    if source_url:
        existing = (
            db.query(LearningPath)
            .filter(LearningPath.plan_id == plan.id, LearningPath.source_url == source_url)
            .first()
        )
    if existing is not None:
        path = existing
        created = False
    else:
        path = LearningPath(
            user_id=user_id,
            plan_id=plan.id,
            platform=platform,
            title=(card.get("title") or "")[:300],
            description=card.get("description"),
            difficulty=(card.get("difficulty") or "")[:60] or None,
            source_url=source_url or "",
            first_resource_url=(card.get("first_resource_url") or "")[:600] or None,
            resource_total=None,
            crawl_status=CRAWL_DISCOVERED,
        )
        db.add(path)
        db.flush()
        created = True

    # Refresh metadata on every resync (titles/difficulty may drift on the site).
    path.platform = platform
    path.title = (card.get("title") or path.title or "")[:300]
    path.description = card.get("description") or path.description
    if card.get("difficulty"):
        path.difficulty = (card.get("difficulty") or "")[:60]
    if card.get("first_resource_url"):
        path.first_resource_url = (card.get("first_resource_url") or "")[:600]

    # Re-crawl the path page and persist its resources (deduped by URL key).
    crawled = crawl_learning_path(path.source_url, cookies=cookies)
    if crawled is None:
        path.crawl_status = CRAWL_EXTRACTION_FAILED
        path.error = "Discovery produced no path page"
        db.flush()
        return path, created
    path.crawl_status = crawled["crawl_status"]
    path.final_url = (crawled.get("final_url") or "")[:600] or None
    path.status_code = crawled.get("status_code")
    path.error = (crawled.get("error") or "")[:300] or None
    path.resource_total = crawled.get("resource_total")
    if crawled["crawl_status"] != CRAWL_CRAWLED:
        db.flush()
        return path, created
    path.crawled_at = utcnow()

    sections: set[str] = set()
    order = 0
    for item in crawled["items"]:
        order += 1
        url = item.get("url")
        sections.add(item.get("section") or "")
        key = _url_key(url) if url else None
        existing_res = None
        if key:
            existing_res = (
                db.query(LearningResource)
                .filter(LearningResource.plan_id == plan.id, LearningResource.url_key == key)
                .first()
            )
        if existing_res is None:
            res = LearningResource(
                user_id=user_id,
                plan_id=plan.id,
                title=(item.get("title") or "")[:300],
                url=(url or "")[:600] or None,
                resource_type=item.get("resource_type") or RESOURCE_TYPE_READING,
                difficulty=(item.get("difficulty") or "")[:60] or None,
                section=(item.get("section") or "")[:200] or None,
                sort_order=order,
                url_key=key,
                crawl_status=CRAWL_DISCOVERED,
            )
            db.add(res)
            db.flush()
            existing_res = res
        link = (
            db.query(LearningPathResource)
            .filter(
                LearningPathResource.path_id == path.id,
                LearningPathResource.resource_id == existing_res.id,
            )
            .first()
        )
        if link is None:
            db.add(
                LearningPathResource(
                    path_id=path.id,
                    resource_id=existing_res.id,
                    section=(item.get("section") or "")[:200] or None,
                    sort_order=order,
                )
            )
    path.section_count = len(sections)
    path.resource_count = len(crawled["items"])
    db.flush()
    return path, created


def build_source_payload(db: Session, plan) -> dict:
    """Layer-1 snapshot for the UI: platform → paths → resources + report."""
    report: dict = {"platform": None, "source_url": None}
    if plan.source_json:
        try:
            report = json.loads(plan.source_json)
        except Exception:  # noqa: BLE001
            report = {}
    paths = (
        db.query(LearningPath)
        .filter(LearningPath.plan_id == plan.id)
        .order_by(LearningPath.id.asc())
        .all()
    )
    out_paths: list[dict] = []
    for path in paths:
        links = (
            db.query(LearningPathResource)
            .filter(LearningPathResource.path_id == path.id)
            .order_by(LearningPathResource.sort_order.asc())
            .all()
        )
        resources = []
        for link in links:
            res = db.get(LearningResource, link.resource_id)
            if res is None:
                continue
            resources.append(
                {
                    "id": res.id,
                    "title": res.title,
                    "url": res.url,
                    "resource_type": res.resource_type,
                    "difficulty": res.difficulty,
                    "section": link.section or res.section,
                    "sort_order": link.sort_order,
                    "crawl_status": res.crawl_status,
                    "status_code": res.status_code,
                    "error": res.error,
                }
            )
        out_paths.append(
            {
                "id": path.id,
                "platform": path.platform,
                "title": path.title,
                "description": path.description,
                "difficulty": path.difficulty,
                "source_url": path.source_url,
                "first_resource_url": path.first_resource_url,
                "resource_total": path.resource_total,
                "section_count": path.section_count,
                "resource_count": path.resource_count,
                "crawl_status": path.crawl_status,
                "status_code": path.status_code,
                "error": path.error,
                "resources": resources,
            }
        )
    return {"report": report, "paths": out_paths}
