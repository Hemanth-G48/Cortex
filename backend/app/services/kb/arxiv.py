"""arXiv metadata lookup (Idea 5, phrases 45–48).

Fetches title/authors/abstract from the arXiv Atom API with an httpx timeout,
caches by ID, and fails gracefully offline — a network error never 500s the
request; the document still ingests with text only.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

ARXIV_API = "http://export.arxiv.org/api/query"
ARXIV_ID_RE = re.compile(r"(?:arxiv\.org/(?:abs|pdf)/)?(\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE)

_ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}
_CACHE: dict[str, dict] = {}


def extract_arxiv_id(text: str | None) -> str | None:
    """Pull an arXiv ID out of a filename, URL, or first-page text."""
    m = ARXIV_ID_RE.search(text or "")
    return m.group(1) if m else None


def _parse_atom(xml_text: str, arxiv_id: str) -> dict | None:
    try:
        root = ET.fromstring(xml_text)
        entry = root.find("a:entry", _ATOM_NS)
        if entry is None:
            return None

        def _text(tag: str) -> str | None:
            node = entry.find(f"a:{tag}", _ATOM_NS)
            return (node.text or "").strip() if node is not None and node.text else None

        authors = [
            (author.findtext("a:name", default="", namespaces=_ATOM_NS) or "").strip()
            for author in entry.findall("a:author", _ATOM_NS)
        ]
        return {
            "arxiv_id": arxiv_id,
            "title": _text("title"),
            "authors": [a for a in authors if a],
            "abstract": _text("summary"),
        }
    except ET.ParseError as exc:
        logger.warning("arXiv Atom parse failed for %s: %s", arxiv_id, exc)
        return None


def fetch_arxiv_metadata(arxiv_id: str, timeout: float = 15.0) -> dict | None:
    """Return ``{arxiv_id, title, authors, abstract}`` or None on any failure."""
    arxiv_id = (arxiv_id or "").strip().lower()
    if not arxiv_id:
        return None
    if arxiv_id in _CACHE:
        return _CACHE[arxiv_id]
    try:
        resp = httpx.get(ARXIV_API, params={"id_list": arxiv_id}, timeout=timeout)
        if resp.status_code != 200:
            logger.warning("arXiv returned %s for %s", resp.status_code, arxiv_id)
            return None
        meta = _parse_atom(resp.text, arxiv_id)
        if meta and meta.get("title"):
            _CACHE[arxiv_id] = meta
        return meta
    except Exception as exc:  # noqa: BLE001 — offline / DNS / timeout
        logger.warning("arXiv lookup failed for %s: %s", arxiv_id, exc)
        return None
