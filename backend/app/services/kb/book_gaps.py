"""Book Knowledge Gap Analyzer.

The central design principle: tell the reader EXACTLY what a book can teach
them that they don't already know — not what the book is about. Pipeline:

    PDF pages → chapter/section structure → concept extraction (hybrid:
    lexicon phrase-matching always + LLM refinement when the daily budget
    allows, TF-IDF/title-case fallback otherwise) → compare every concept
    against the user's real Second Brain evidence (reusing the gap engine's
    ``_evidence``/``_level_for``) → classify KNOWN / PARTIALLY_KNOWN /
    UNKNOWN (+ HISTORICAL flag) → persist per-book items → reading queue →
    cross-book dedup via the cumulative ``BookConceptState`` store.

Everything here is concept-level (multi-word phrases with aliases), never a
keyword count: "reverse shell" is one concept, and a vault note containing
the word "shell" is NOT evidence of understanding reverse shells.
"""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models import (
    Book,
    BookConceptState,
    BookGapAnalysis,
    BookGapItem,
    BookGapTopic,
    KbConcept,
    KbDocument,
    KbEdge,
)
from app.services.kb.budget import budget_allows, record_generation
from app.services.kb import concepts as concepts_service
from app.services.kb.gap_domains import concepts_by_name

# Curated domain catalog (name → spec with aliases/importance) — static, so
# compute once at import rather than per book.
_DOMAIN_CONCEPTS = concepts_by_name()
from app.services.kb.gap_engine import (
    _build_vault_index,
    _evidence,
    _level_for,
    _match_vault_concepts,
    _normalize,
    _tokens,
)
from app.services.text_extractor import extract_pdf_pages, NoExtractableTextError

logger = logging.getLogger(__name__)

# Analysis classification (per book snapshot).
KNOWN = "KNOWN"
PARTIAL = "PARTIALLY_KNOWN"
UNKNOWN = "UNKNOWN"
NEEDS_REVIEW = "NEEDS_REVIEW"

# Stage-2 deep-analysis states per topic.
NOT_ANALYZED = "NOT_ANALYZED"
ANALYZING = "ANALYZING"
ANALYZED = "ANALYZED"
FAILED = "FAILED"

# User learning progress (cumulative).
LEARNING = "LEARNING"
LEARNED = "LEARNED"
MASTERED = "MASTERED"

MAX_CONCEPTS_PER_BOOK = 200
MAX_LEXICON_PHRASES = 1000
MIN_LLM_TEXT_CHARS = 1200
EST_MINUTES_PER_PAGE = 1.5

# TOC-first workflow limits.
MAX_TOC_TOPICS = 250
MAX_TOPIC_PAGES_FOR_LLM = 4000  # chars of page text sent to the LLM per topic
MAX_SB_CHARS_FOR_LLM = 4000  # chars of Second Brain context sent to the LLM

# ── Structure detection ──────────────────────────────────────────────────────
_CHAPTER_RE = re.compile(
    r"^\s*(?:chapter|lesson|module)\s+([0-9]+|[ivxlcdm]+)\b\s*[.:\-–—]?\s*(.*)$",
    re.IGNORECASE,
)
_PART_RE = re.compile(r"^\s*part\s+([0-9]+|[ivxlcdm]+)\b[.:\-–—]?\s*(.*)$", re.IGNORECASE)
_SECTION_RE = re.compile(r"^\s*(\d+(?:\.\d+){1,3})\s+[A-Z]")

# ── Historical/outdated indicators (requirement 18 — flag, never discard) ──
_HISTORICAL_TERMS = (
    "legacy", "deprecated", "outdated", "obsolete", "superseded", "antiquated",
    "no longer used", "not recommended", "no longer recommended",
    "windows xp", "windows 7", "windows 2000", "windows 98", "windows nt",
    "win xp", "pre-windows", "pre-2010", "old version", "older version",
)
_HISTORICAL_RE = re.compile(
    "|".join(re.escape(t) for t in _HISTORICAL_TERMS), re.IGNORECASE
)

# ── Fallback deterministic extraction ───────────────────────────────────────
_TITLE_CASE_RE = re.compile(r"\b[A-Z][A-Za-z0-9&+#.\-]*(?:\s+[A-Z][A-Za-z0-9&+#.\-]*){1,4}\b")
_SCREAMING_RE = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\b")
_FALLBACK_MIN_TOKEN_LEN = 6

_NOISE = {
    "chapter", "chapters", "section", "sections", "page", "pages", "figure",
    "figures", "table", "tables", "contents", "index", "preface", "introduction",
    "overview", "summary", "summaries", "references", "appendix", "appendices",
    "part", "parts", "module", "lesson", "copyright", "acknowledgements",
    "about the author", "about", "bibliography", "glossary", "title page",
    "foreword", "afterword", "prologue", "epilogue", "notes", "note",
    "information", "knowledge", "learning", "objectives", "key terms",
}

# Seed cybersecurity lexicon (used even when the vault is empty). These are
# multi-word / tool / technique concepts — never single generic words.
_SEED_CONCEPTS: dict[str, list[str]] = {
    "reverse shell": ["reverse shell", "reverse shells"],
    "bind shell": ["bind shell", "bind shells"],
    "shellcode": ["shellcode", "shell code"],
    "privilege escalation": ["privilege escalation", "priv esc", "privesc"],
    "ld_preload": ["LD_PRELOAD", "ld preload"],
    "port scanning": ["port scanning", "port scan", "port scans"],
    "sql injection": ["sql injection", "sql injection attack"],
    "cross-site scripting": ["cross-site scripting", "xss"],
    "cross-site request forgery": ["cross-site request forgery", "csrf", "xsrf"],
    "server-side request forgery": ["server-side request forgery", "ssrf"],
    "pass-the-hash": ["pass-the-hash", "pass the hash", "pth"],
    "pass-the-ticket": ["pass-the-ticket", "pass the ticket", "ptt"],
    "kerberos delegation": ["kerberos delegation", "kerberos delegations"],
    "active directory": ["active directory", "ad"],
    "ntlm relay": ["ntlm relay", "ntlm relaying"],
    "metasploit": ["metasploit", "msf"],
    "meterpreter": ["meterpreter"],
    "nmap": ["nmap"],
    "enumeration": ["enumeration", "enumerating"],
    "lateral movement": ["lateral movement", "lateral moving"],
    "persistence": ["persistence", "persistence mechanisms"],
    "buffer overflow": ["buffer overflow", "buffer overflows"],
    "stack overflow": ["stack overflow", "stack smashing"],
    "heap overflow": ["heap overflow", "heap spraying"],
    "ret2libc": ["ret2libc", "return-to-libc"],
    "return-oriented programming": ["return-oriented programming", "rop chain", "rop"],
    "format string vulnerability": ["format string vulnerability", "format string attack"],
    "race condition": ["race condition", "race conditions", "time-of-check time-of-use", "toctou"],
    "directory traversal": ["directory traversal", "path traversal"],
    "command injection": ["command injection", "os command injection"],
    "ldap injection": ["ldap injection", "ldap injection attack"],
    "xml external entity": ["xml external entity", "xxe"],
    "deserialization attack": ["deserialization attack", "insecure deserialization"],
    "oauth": ["oauth", "oauth 2.0"],
    "jwt": ["jwt", "json web token", "json web tokens"],
    "session hijacking": ["session hijacking", "session fixation"],
    "clickjacking": ["clickjacking", "ui redress"],
    "subdomain takeover": ["subdomain takeover", "dns takeover"],
    "dns rebinding": ["dns rebinding"],
    "phishing": ["phishing", "spear phishing", "whaling"],
    "social engineering": ["social engineering"],
    "password spraying": ["password spraying"],
    "credential stuffing": ["credential stuffing"],
    "brute force": ["brute force", "brute-force", "bruteforce"],
    "hash cracking": ["hash cracking", "password cracking"],
    "rainbow table": ["rainbow table", "rainbow tables"],
    "keylogger": ["keylogger", "key loggers"],
    "rootkit": ["rootkit", "rootkits"],
    "backdoor": ["backdoor", "back doors"],
    "trojan": ["trojan", "trojan horse", "trojans"],
    "ransomware": ["ransomware"],
    "worm": ["worm", "computer worm", "worms"],
    "malware analysis": ["malware analysis"],
    "dynamic analysis": ["dynamic analysis", "dynamic binary analysis"],
    "static analysis": ["static analysis"],
    "sandboxing": ["sandboxing", "sandbox escape"],
    "intrusion detection": ["intrusion detection", "ids"],
    "intrusion prevention": ["intrusion prevention", "ips"],
    "firewall evasion": ["firewall evasion", "firewalking"],
    "ids evasion": ["ids evasion", "evasion techniques"],
    "tcp handshake": ["tcp handshake", "three-way handshake"],
    "syn flood": ["syn flood", "syn flooding"],
    "smb relay": ["smb relay", "smb relaying"],
    "impacket": ["impacket"],
    "mimikatz": ["mimikatz"],
    "responder": ["responder", "llmnr poisoning"],
    "bloodhound": ["bloodhound"],
    "cobalt strike": ["cobalt strike", "beacon"],
    "yara": ["yara", "yara rules"],
    "volatility": ["volatility", "memory forensics"],
    "autopsy": ["autopsy", "forensic toolkit"],
    "wireshark": ["wireshark"],
    "tcpdump": ["tcpdump"],
    "burp suite": ["burp suite", "burp"],
    "sqlmap": ["sqlmap"],
    "hashcat": ["hashcat"],
    "john the ripper": ["john the ripper", "john"],
    "hydra": ["hydra"],
    "gobuster": ["gobuster"],
    "dirb": ["dirb"],
    "nikto": ["nikto"],
    "nessus": ["nessus"],
    "openvas": ["openvas"],
    "osint": ["osint", "open source intelligence"],
    "threat modeling": ["threat modeling"],
    "zero-day": ["zero-day", "zero day", "0-day"],
    "exploit development": ["exploit development"],
    "fuzzing": ["fuzzing", "fuzzer", "fuzzers"],
    "symbolic execution": ["symbolic execution"],
    "reverse engineering": ["reverse engineering", "re"],
    "disassembly": ["disassembly", "disassembler"],
    "debugging": ["debugging", "debugger"],
    "gdb": ["gdb", "gnu debugger"],
    "ida pro": ["ida pro", "ida"],
    "ghidra": ["ghidra"],
    "obfuscation": ["obfuscation", "code obfuscation"],
    "packing": ["packing", "packer", "packed binary"],
    "cryptography": ["cryptography", "crypto"],
    "public-key cryptography": ["public-key cryptography", "asymmetric cryptography"],
    "symmetric cryptography": ["symmetric cryptography", "symmetric encryption"],
    "hashing": ["hashing", "hash function", "hash functions"],
    "digital signature": ["digital signature", "digital signatures"],
    "certificate pinning": ["certificate pinning"],
    "tls handshake": ["tls handshake", "ssl handshake"],
    "man-in-the-middle": ["man-in-the-middle", "mitm", "man in the middle"],
    "arp spoofing": ["arp spoofing", "arp poisoning"],
    "dns spoofing": ["dns spoofing", "dns poisoning"],
    "packet sniffing": ["packet sniffing", "sniffing"],
    "vlan hopping": ["vlan hopping"],
    "rogue access point": ["rogue access point", "evil twin"],
    "wpa2 cracking": ["wpa2 cracking", "wpa cracking"],
    "bluetooth attack": ["bluetooth attack", "bluejacking", "bluesnarfing"],
    "mobile malware": ["mobile malware"],
    "ios jailbreak": ["ios jailbreak", "jailbreaking"],
    "android rooting": ["android rooting"],
    "api gateway": ["api gateway"],
    "rate limiting": ["rate limiting"],
    "cloud misconfiguration": ["cloud misconfiguration", "misconfigured bucket", "open s3 bucket"],
    "container escape": ["container escape"],
    "kubernetes attack": ["kubernetes attack", "k8s attack"],
    "supply chain attack": ["supply chain attack", "supply chain"],
    "dll hijacking": ["dll hijacking", "dll search order"],
    "appdomain": ["appdomain", ".net appdomain"],
    "process injection": ["process injection", "dll injection"],
    "c2": ["c2", "command and control", "c2 channel"],
    "beacon": ["beacon", "cobalt strike beacon"],
    "data exfiltration": ["data exfiltration", "exfiltration"],
    "pivoting": ["pivoting", "pivot"],
    "tunneling": ["tunneling", "ssh tunneling", "chisel"],
    "proxy chains": ["proxy chains", "proxychains"],
    "elevation of privileges": ["elevation of privileges"],
    "suid": ["suid", "setuid"],
    "sudo": ["sudo", "sudo misconfiguration"],
    "cron": ["cron", "cron job", "crontab"],
    "capabilities": ["linux capabilities"],
    "nfs": ["nfs", "network file system", "root squash"],
    "kernel exploit": ["kernel exploit", "kernel exploitation"],
    "windows registry": ["windows registry", "registry"],
    "active directory certificate services": ["active directory certificate services", "ad cs"],
    "golden ticket": ["golden ticket"],
    "silver ticket": ["silver ticket"],
    "kerberoasting": ["kerberoasting"],
    "as-rep roasting": ["as-rep roasting", "asrep roasting"],
    "dcsync": ["dcsync", "dc shadow"],
    "ntds.dit": ["ntds dit", "ntds.dit extraction"],
    "psexec": ["psexec", "psexec.py"],
    "wmi": ["wmi", "windows management instrumentation"],
    "winrm": ["winrm", "windows remote management"],
    "rdp": ["rdp", "remote desktop protocol"],
    "ssh": ["ssh", "secure shell"],
    "smb": ["smb", "server message block"],
    "ldap": ["ldap", "lightweight directory access protocol"],
    "kerberos": ["kerberos"],
    "ntlm": ["ntlm", "windows nt lan manager"],
    "netbios": ["netbios", "nbns"],
    "dns": ["dns", "domain name system"],
    "dhcp": ["dhcp", "dynamic host configuration protocol"],
    "tcp/ip": ["tcp/ip", "tcp ip"],
    "osi model": ["osi model", "osi layer"],
    "subnetting": ["subnetting", "subnet mask"],
    "network segmentation": ["network segmentation", "segmentation"],
    "zero trust": ["zero trust", "zero-trust architecture"],
    "defense in depth": ["defense in depth"],
    "security information and event management": ["security information and event management", "siem"],
    "endpoint detection and response": ["endpoint detection and response", "edr"],
    "next-generation firewall": ["next-generation firewall", "ngfw"],
    "web application firewall": ["web application firewall", "waf"],
    "sandbox evasion": ["sandbox evasion"],
    "fileless malware": ["fileless malware", "fileless attack"],
    "living off the land": ["living off the land", "lotl", "living off the land binaries"],
    "data loss prevention": ["data loss prevention", "dlp"],
    "incident response": ["incident response", "ir"],
    "digital forensics": ["digital forensics", "forensics"],
    "chain of custody": ["chain of custody"],
    "threat intelligence": ["threat intelligence", "cti"],
    "security operations center": ["security operations center", "soc"],
    "penetration testing": ["penetration testing", "pentest", "pen test"],
    "red teaming": ["red team", "red teaming"],
    "blue team": ["blue team", "blue teaming"],
    "purple team": ["purple team"],
    "bug bounty": ["bug bounty", "bug bounty hunting"],
    "responsible disclosure": ["responsible disclosure"],
    "ethical hacking": ["ethical hacking"],
    "footprinting": ["footprinting", "fingerprinting"],
    "reconnaissance": ["reconnaissance", "recon"],
    "vulnerability assessment": ["vulnerability assessment"],
    "exploitation": ["exploitation", "exploiting"],
    "post-exploitation": ["post-exploitation", "post exploitation"],
    "capture the flag": ["capture the flag", "ctf"],
}


def _book_file_path(book: Book) -> Path:
    """Map ``book.file_url`` (``/uploads/x.pdf``) to the on-disk path."""
    if not book.file_url:
        raise NoExtractableTextError("Book has no PDF file")
    return Path(settings.UPLOAD_DIR) / Path(book.file_url).name


# ---------------------------------------------------------------------------
# Structure detection
# ---------------------------------------------------------------------------

def _detect_structure(pages: list[str]) -> tuple[list[str | None], list[dict[str, Any]]]:
    """Return (page→chapter-title map, chapter meta list).

    Chapters are detected from ``Chapter N``-style headings near the top of
    each page (also ``Part`` / ``Lesson`` / ``Module``). When fewer than two
    chapters are found the book is bucketed into ~40-page pseudo-chapters so
    the UI still has a structure to browse.
    """
    chapter_map: list[str | None] = [None] * len(pages)
    chapter_titles: list[str] = []

    def _looks_like_chapter(lines: list[str]) -> str | None:
        for line in lines[:14]:
            m = _CHAPTER_RE.match(line.strip()) or _PART_RE.match(line.strip())
            if m:
                return (m.group(2) or f"{m.group(1)}").strip() or f"Chapter {m.group(1)}"
        return None

    current: str | None = None
    for i, page in enumerate(pages):
        lines = [ln for ln in page.splitlines() if ln.strip()][:20]
        title = _looks_like_chapter(lines)
        if title:
            current = title
            if title not in chapter_titles:
                chapter_titles.append(title)
        chapter_map[i] = current

    if len(chapter_titles) < 2:
        # No reliable chapter headings — bucket pages into pseudo-chapters.
        bucket = 40
        chapter_titles = []
        for start in range(0, len(pages), bucket):
            end = min(start + bucket, len(pages)) - 1
            title = f"Pages {start + 1}–{end + 1}"
            chapter_titles.append(title)
            for i in range(start, end + 1):
                chapter_map[i] = title

    chapters_meta: list[dict[str, Any]] = []
    for title in chapter_titles:
        idx = [i for i, t in enumerate(chapter_map) if t == title]
        if not idx:
            continue
        chapters_meta.append(
            {"title": title, "start_page": min(idx) + 1, "end_page": max(idx) + 1}
        )
    return chapter_map, chapters_meta


def _section_of(page: str) -> str | None:
    """Last numbered section heading on a page (e.g. ``8.4 Environment
    Variable Abuse``), or None."""
    section: str | None = None
    for line in page.splitlines():
        line = line.strip()
        m = _SECTION_RE.match(line)
        if m and len(line) > len(m.group(1)) + 2:
            section = line
    return section


# ---------------------------------------------------------------------------
# TOC-first workflow (Stage 1 — structure + topic extraction)
# ---------------------------------------------------------------------------

_LEVEL_RANK = {
    "Mastered": 0, "Strong": 1, "Familiar": 2, "Weak": 3,
    "Not Found": 4, "Prerequisite Missing": 5,
}


def _extract_toc(
    pages: list[str],
    chapter_map: list[str | None],
    chapters_meta: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Deterministic heading-based reconstruction of the book's TOC.

    Chapters (level 1) come from ``_detect_structure``; within each chapter,
    numbered headings like ``8.4 Environment Variable Abuse`` become section
    topics (level 2) and ``8.4.1 ...`` subsection topics (level 3), each with
    its own page range derived from where the next heading begins.

    This reconstructs the table of contents from the actual headings rather
    than parsing a literal Contents page — far more reliable across real
    books, and fully deterministic (no LLM).
    """
    topics: list[dict[str, Any]] = []
    for ch in chapters_meta:
        chapter_title = ch["title"]
        ch_start, ch_end = ch["start_page"], ch["end_page"]
        topics.append(
            {
                "title": chapter_title,
                "level": 1,
                "parent_title": None,
                "page_start": ch_start,
                "page_end": ch_end,
            }
        )
        # Numbered headings inside this chapter, with their immediate parent
        # (a 8.4.1 subsection's parent is the 8.4 section, not the chapter).
        current_section: str | None = None
        for i in range(ch_start - 1, ch_end):
            for line in pages[i].splitlines():
                line = line.strip()
                m = _SECTION_RE.match(line)
                if not m or len(line) <= len(m.group(1)) + 2:
                    continue
                num = m.group(1)
                # 8.4 → 2 (section), 8.4.1 → 3 (subsection); the regex already
                # requires at least one dot, so 1 + dots is the right level.
                level = min(3, 1 + num.count("."))
                title = line[len(m.group(1)):].strip(" .:-–—")
                if not title or _normalize(title) in _NOISE:
                    continue
                if level == 2:
                    current_section = title
                parent = current_section if level > 2 else chapter_title
                topics.append(
                    {
                        "title": title,
                        "level": level,
                        "parent_title": parent,
                        "page_start": i + 1,
                        "page_end": i + 1,
                    }
                )
    # Collapse a heading repeated on consecutive pages (running headers) by
    # merging page spans of adjacent identical (level, title) entries.
    merged: list[dict[str, Any]] = []
    for t in topics:
        if (
            merged
            and merged[-1]["title"] == t["title"]
            and merged[-1]["level"] == t["level"]
            and merged[-1]["parent_title"] == t["parent_title"]
        ):
            merged[-1]["page_end"] = t["page_end"]
        else:
            merged.append(dict(t))
    return merged[:MAX_TOC_TOPICS]


def _topic_forms(title: str) -> list[str]:
    """Expanded search forms for a topic title.

    Besides the title itself, adds the canonical + aliases from the curated
    domain catalog / seed lexicon when the title matches one of their aliases
    (e.g. topic "Server-Side Request Forgery" → canonical "SSRF", so a vault
    concept named "SSRF" matches even without an explicit alias row).
    """
    norm = _normalize(title)
    forms = [title] if title else []
    if norm and norm not in forms:
        forms.append(norm)

    def add(name: str | None, aliases: list[str]) -> None:
        if not name:
            return
        all_names = [name] + [str(a) for a in aliases if a]
        if not any(_normalize(n) == norm for n in all_names):
            return
        for n in all_names:
            nn = _normalize(n)
            if nn and nn not in forms:
                forms.append(nn)

    for spec in _DOMAIN_CONCEPTS.values():
        add(spec.get("name"), spec.get("aliases") or [])
    for canonical, aliases in _SEED_CONCEPTS.items():
        add(canonical, aliases)
    return forms[:8]


def _match_source_of(form: str, vault_index: list[dict]) -> tuple[str, float]:
    """Best (source, confidence) for one form against the vault index.

    exact=1.0 (normalized equality) · alias=0.95/0.85 (alias equality) ·
    token=0.8 (same token set) · subset=0.4 (target tokens ⊂ candidate).
    """
    tn = _normalize(form)
    t_toks = _tokens(form)
    for entry in vault_index:
        if entry["canon"] == tn:
            return "exact", 1.0
        if t_toks and entry["c_toks"] == t_toks:
            return "token", 0.8
        for _raw, an, a_toks in entry["aliases"]:
            if an == tn:
                return "alias", 0.95
            if t_toks and a_toks == t_toks:
                return "alias", 0.85
    for entry in vault_index:
        if t_toks and entry["c_toks"] and t_toks.issubset(entry["c_toks"]):
            return "subset", 0.4
        for _raw, an, a_toks in entry["aliases"]:
            if t_toks and a_toks and t_toks.issubset(a_toks):
                return "subset", 0.4
    return "none", 0.0


def _match_topic_to_brain(
    db: Session, user_id: int, title: str, vault_index: list[dict]
) -> dict[str, Any]:
    """Stage-1 semantic match of one TOC topic against the Second Brain.

    Uses the gap engine's matcher (exact / alias / token-set / subset) over
    the topic title + its alias-expanded forms, and the engine's real
    evidence levels. Result statuses:
      - KNOWN            strong evidence (Mastered / Strong)
      - PARTIALLY_KNOWN  some evidence (Familiar / Weak)
      - NEEDS_REVIEW     only a weak subset match with thin evidence
      - UNKNOWN          no match at all
    """
    forms = _topic_forms(title)
    targets = [{"name": f} for f in forms]
    matched, evidence = _evidence(db, user_id, targets, vault_index)

    best_level = "Not Found"
    best_source = "none"
    best_confidence = 0.0
    matched_objs: list = []
    for f in forms:
        matched_objs.extend(matched.get(f) or [])
        ev = evidence.get(f)
        lvl = _level_for(ev) if ev else "Not Found"
        if _LEVEL_RANK.get(lvl, 9) < _LEVEL_RANK.get(best_level, 9):
            best_level = lvl
        src, conf = _match_source_of(f, vault_index)
        if conf > best_confidence:
            best_confidence = conf
            best_source = src

    # Cross-book dedup: an explicit LEARNED/MASTERED marker for any matched
    # concept counts as strong evidence, exactly like the item-level flow.
    state = None
    for concept in matched_objs:
        state = _state_status(db, user_id, concept.canonical_name)
        if state is not None and state.my_status in (LEARNED, MASTERED):
            best_level = "Mastered"
            best_source = best_source if best_source != "none" else "exact"
            break

    if best_level in ("Mastered", "Strong"):
        status = KNOWN
    elif best_level in ("Familiar", "Weak"):
        status = PARTIAL
    elif best_source in ("exact", "alias", "token"):
        # Name exists in the vault but evidence is too thin to claim known.
        status = NEEDS_REVIEW
    else:
        status = UNKNOWN

    best_concept = matched_objs[0] if matched_objs else None
    return {
        "status": status,
        "match_source": best_source,
        "second_brain_match": best_concept.canonical_name if best_concept else None,
        "confidence": best_confidence,
        "level": best_level,
    }


# ---------------------------------------------------------------------------
# Lexicon + concept extraction (hybrid)
# ---------------------------------------------------------------------------

def _build_lexicon(db: Session, user_id: int) -> tuple[re.Pattern, dict[str, tuple[str, str]]]:
    """Multi-word concept lexicon: vault concepts ∪ curated domain concepts ∪
    seed. Returns a single combined regex + ``phrase_lower → (canonical, display)``.
    Longer phrases are matched first so "reverse shell" wins over "shell"."""
    phrases: dict[str, tuple[str, str]] = {}  # lower phrase → (canonical, display)

    def add(name: str, aliases: list[str] | None) -> None:
        aliases = [a for a in (aliases or []) if a and isinstance(a, str)]
        forms = [name] + aliases
        for f in forms:
            key = re.sub(r"\s+", " ", f.strip().lower())
            if not key or len(key) < 3:
                continue
            if key in phrases:
                continue
            phrases[key] = (concepts_service.canonicalize(name) or key, name.strip())

    # Vault concepts (the user's own knowledge catalog).
    for c in db.query(KbConcept).filter(KbConcept.user_id == user_id).all():
        add(c.canonical_name, json.loads(c.aliases) if c.aliases else None)
    # Curated domain concepts (gap engine catalog) — name + aliases.
    for spec in _DOMAIN_CONCEPTS.values():
        add(spec.get("name") or "", spec.get("aliases") or [])
    # Seed lexicon.
    for canonical, forms in _SEED_CONCEPTS.items():
        add(canonical, forms)

    # Sort longest-first so longer phrases match before their sub-phrases.
    ordered = sorted(phrases.items(), key=lambda kv: (-len(kv[0].split()), kv[0]))
    ordered = ordered[:MAX_LEXICON_PHRASES]
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(p) for p, _ in ordered) + r")\b",
        re.IGNORECASE,
    )
    lookup = {p: meta for p, meta in ordered}
    return pattern, lookup


def _snippet_around(page: str, start: int, end: int, max_len: int = 320) -> str:
    """One or two sentences around a match inside a page."""
    text = re.sub(r"\s+", " ", page)
    match = text[start:end]
    idx = text.find(match, 0)
    if idx < 0:
        return text[max(0, start - 40): start + max_len]
    # Sentence boundaries around the match.
    before = text[:idx]
    after = text[idx:]
    sent_start = max(before.rfind(". "), before.rfind("! "), before.rfind("? ")) + 1
    cut = after.find(". ")
    cut2 = after.find(". ", (cut + 2) if cut >= 0 else 0)
    end_idx = cut2 if cut2 >= 0 else (cut if cut >= 0 else len(after))
    snippet = text[max(0, sent_start): idx + end_idx + 1]
    if len(snippet) > max_len:
        snippet = text[max(0, idx - max_len // 2): idx + max_len // 2]
    return snippet.strip()


def _scan_pages_for_concepts(
    pages: list[str],
    chapter_map: list[str | None],
    pattern: re.Pattern,
    lookup: dict[str, tuple[str, str]],
) -> dict[str, dict[str, Any]]:
    """Phrase-match every page → per-concept occurrence map.

    Returns ``{canonical: {display, pages: [1-based], snippets: [...],
    chapters: set, sections: set}}``. A concept spanning many pages stays ONE
    entry (grouped, requirement 8)."""
    out: dict[str, dict[str, Any]] = {}
    for i, page in enumerate(pages):
        if not page:
            continue
        matched = set()
        for m in pattern.finditer(page):
            phrase = re.sub(r"\s+", " ", m.group(0).strip().lower())
            meta = lookup.get(phrase)
            if meta is None:
                continue
            canonical, display = meta
            if canonical in matched:
                continue
            matched.add(canonical)
            # Prefer the book's own spelling for display ("LD_PRELOAD",
            # "Nmap", "Pass-the-Hash") over the lexicon's lowercase form.
            actual = re.sub(r"\s+", " ", m.group(0).strip())
            if actual and actual.lower() == display.lower():
                display = actual
            entry = out.setdefault(
                canonical,
                {"display": display, "pages": [], "snippets": [], "chapters": set(), "sections": set()},
            )
            # Upgrade a lowercase seed display to the book's spelling once.
            if display != entry["display"] and entry["display"] == entry["display"].lower():
                entry["display"] = display
            entry["pages"].append(i + 1)
            entry["chapters"].add(chapter_map[i] or "")
            section = _section_of(page)
            if section:
                entry["sections"].add(section)
            snippet = _snippet_around(page, m.start(), m.end())
            if snippet and snippet not in entry["snippets"]:
                entry["snippets"].append(snippet)
    return out


def _fallback_candidates(chapter_text: str, existing: set[str]) -> list[str]:
    """Deterministic concept candidates not covered by the lexicon.

    Title-case multi-word sequences (``Active Directory``), SCREAMING tokens
    (``LD_PRELOAD``, ``SMB``), and longer lowercase tokens — filtered for
    noise and deduped. Never raises."""
    found: set[str] = set()
    for m in _TITLE_CASE_RE.finditer(chapter_text):
        phrase = m.group(0).strip()
        words = phrase.split()
        if 2 <= len(words) <= 5 and all(len(w) >= 3 for w in words):
            found.add(phrase)
    for m in _SCREAMING_RE.finditer(chapter_text):
        token = m.group(0)
        if len(token) >= 3 and not token.isdigit():
            found.add(token)
    out: list[str] = []
    for name in found:
        canonical = concepts_service.canonicalize(name)
        if not canonical or len(canonical) < 3:
            continue
        if canonical in existing or canonical in _NOISE:
            continue
        out.append(name)
    return out[:60]


def _llm_concepts(db: Session, user_id: int, chapter_title: str, text: str) -> list[dict]:
    """LLM concept extraction for one chapter (budget-gated). Returns
    ``[{concept, definition, aliases}]`` or ``[]`` when AI is off, the budget
    is exhausted, or the call fails — the pipeline then keeps the
    deterministic concepts. Never raises."""
    if not budget_allows(db, user_id):
        return []
    from app.services.ai_client import ai_available, generate_json

    if not ai_available():
        return []
    prompt = (
        "You are analyzing a cybersecurity book chapter to extract what it "
        "teaches, as CONCEPTS the reader might not know. A concept is an idea, "
        "technique, tool, protocol or attack (e.g. \"Reverse Shells\", "
        "\"LD_PRELOAD Privilege Escalation\", \"Pass-the-Hash\") — never a "
        "single generic word like \"shell\" or \"security\". Extract up to 12 "
        "concepts this chapter actually teaches.\n"
        f"Chapter: {chapter_title}\n"
        f"Text:\n{text[:4000]}\n"
        'Return ONLY a JSON array of objects: [{"concept": "...", '
        '"definition": "one sentence", "aliases": ["..."]}]'
    )
    try:
        result = generate_json(prompt, max_tokens=1400, temperature=0.2)
        items: list[dict] = []
        if isinstance(result, list):
            for item in result[:12]:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("concept") or item.get("name") or "").strip()
                if not name:
                    continue
                aliases = item.get("aliases") or []
                items.append(
                    {
                        "concept": name,
                        "definition": str(item.get("definition") or "").strip() or None,
                        "aliases": [str(a).strip() for a in aliases if str(a).strip()],
                    }
                )
        if items:
            record_generation(db, user_id, "book")
        return items
    except Exception as exc:  # noqa: BLE001 — LLM failure never breaks analysis
        logger.warning("Book chapter concept LLM extraction failed: %s", exc)
        return []


def _collect_concepts(
    db: Session, user_id: int, pages: list[str], chapter_map: list[str | None]
) -> dict[str, dict[str, Any]]:
    """Concept-level extraction for the whole book (hybrid)."""
    pattern, lookup = _build_lexicon(db, user_id)
    concepts = _scan_pages_for_concepts(pages, chapter_map, pattern, lookup)

    # Deterministic + LLM candidates from chapters not already covered.
    by_chapter: dict[str, list[int]] = defaultdict(list)
    for i, title in enumerate(chapter_map):
        if title:
            by_chapter[title].append(i)
    for title, idxs in by_chapter.items():
        chapter_text = "\n".join(pages[i] for i in idxs)
        existing = set(concepts) | _NOISE
        for name in _fallback_candidates(chapter_text, existing):
            canonical = concepts_service.canonicalize(name)
            entry = concepts.setdefault(
                canonical,
                {"display": name, "pages": [i + 1 for i in idxs], "snippets": [], "chapters": {title}, "sections": set()},
            )
            for i in idxs:
                if i + 1 not in entry["pages"]:
                    entry["pages"].append(i + 1)
                if not entry["snippets"]:
                    snippet = _snippet_around(pages[i], 0, min(80, len(pages[i])))
                    if snippet:
                        entry["snippets"].append(snippet)
            existing.add(canonical)
        # LLM refinement (budget-gated) — catches book-specific concepts.
        for item in _llm_concepts(db, user_id, title, chapter_text):
            canonical = concepts_service.canonicalize(item["concept"])
            if not canonical or canonical in existing:
                continue
            # Snippets from the chapter where the term actually appears.
            term_re = re.compile(
                r"\b" + re.escape(item["concept"]) + r"\b", re.IGNORECASE
            )
            snippet = ""
            pages_list: list[int] = []
            for i in idxs:
                m = term_re.search(pages[i])
                if m:
                    pages_list.append(i + 1)
                    if not snippet:
                        snippet = _snippet_around(pages[i], m.start(), m.end())
            if not pages_list:
                pages_list = [idxs[0] + 1]
                snippet = _snippet_around(pages[idxs[0]], 0, 80)
            entry = concepts.setdefault(
                canonical,
                {"display": item["concept"], "pages": pages_list, "snippets": [snippet] if snippet else [], "chapters": {title}, "sections": set()},
            )
            entry.setdefault("pages", pages_list)
            entry.setdefault("snippets", [snippet] if snippet else [])
            existing.add(canonical)
    return concepts


# ---------------------------------------------------------------------------
# Knowledge comparison (reuses the gap engine's real evidence)
# ---------------------------------------------------------------------------

def _vault_evidence_for(
    db: Session, user_id: int, targets: list[dict], vault_index: list[dict]
) -> dict[str, dict]:
    """One batched ``_evidence`` call for all book concepts (whole vault)."""
    matched, evidence = _evidence(db, user_id, targets, vault_index)
    return evidence


def _state_status(db: Session, user_id: int, canonical: str) -> BookConceptState | None:
    return (
        db.query(BookConceptState)
        .filter(BookConceptState.user_id == user_id, BookConceptState.concept == canonical)
        .first()
    )


def _effective_level(vault_level: str, state: BookConceptState | None) -> str:
    """Vault evidence is primary; an explicit LEARNED/MASTERED marker raises
    the level (cross-book dedup + user override)."""
    if state is None:
        return vault_level
    if state.my_status == MASTERED:
        return "Mastered"
    if state.my_status == LEARNED:
        return "Strong" if vault_level in ("Not Found", "Weak") else vault_level
    return vault_level


def _classify(
    db: Session,
    user_id: int,
    canonical: str,
    display: str,
    page_span: int,
    vault_level: str,
    evidence: dict | None,
    state: BookConceptState | None,
    chapter: str,
    snippet: str,
    book_title: str,
) -> dict[str, Any]:
    """Turn vault evidence + book depth into the item payload."""
    level = _effective_level(vault_level, state)

    if level in ("Mastered", "Strong"):
        status = KNOWN
    elif level in ("Familiar", "Weak"):
        status = PARTIAL
    else:
        status = UNKNOWN

    # Deeper-knowledge signal (requirement 9): basic vault evidence but the
    # book devotes many pages → there IS missing depth.
    deeper = page_span >= 4 and vault_level in ("Familiar", "Weak")

    # Historical / potentially outdated (requirement 18) — flagged, preserved.
    history_hit = _HISTORICAL_RE.search(snippet or "") or _HISTORICAL_RE.search(chapter or "")
    is_historical = bool(history_hit)
    historical_note = None
    if is_historical:
        historical_note = (
            "Potentially outdated implementation — read for the foundational "
            "concept, but verify the modern equivalent separately."
        )

    knowledge_level = {
        "Mastered": 5, "Strong": 4, "Familiar": 3, "Weak": 2, "Not Found": 0,
    }.get(level, 0)
    if state is not None and state.my_status == LEARNING and knowledge_level < 1:
        knowledge_level = 1

    spec = _DOMAIN_CONCEPTS.get(display) or _DOMAIN_CONCEPTS.get(canonical) or {}
    importance = spec.get("importance") or 2
    if page_span >= 6:
        difficulty = "Advanced"
    elif page_span >= 3 or importance >= 3:
        difficulty = "Intermediate"
    else:
        difficulty = "Beginner"
    est_minutes = max(5, round(page_span * EST_MINUTES_PER_PAGE))

    if status == KNOWN:
        if state is not None and state.my_status in (LEARNED, MASTERED):
            origin = (
                db.query(Book)
                .filter(Book.id == state.learned_from_book_id)
                .first()
                if state.learned_from_book_id
                else None
            )
            where = f" from “{origin.title}”" if origin else ""
            why = (
                f"You already marked {display} as learned{where}. Skip the "
                "redundant material here."
            )
        else:
            why = (
                f"Your Second Brain has strong evidence of {display} "
                f"({level}). Safe to skim or skip this material."
            )
    elif status == PARTIAL:
        if deeper:
            why = (
                f"Your notes show basic understanding of {display} "
                f"({vault_level}), but this book teaches it in depth across "
                f"{page_span} page{'s' if page_span != 1 else ''} — the deeper "
                "material (variants, internals, edge cases) is missing from "
                "your knowledge base."
            )
        else:
            why = (
                f"Your knowledge base mentions {display} but there is little "
                "evidence you understand it beyond the term. Read the book's "
                "coverage to solidify it."
            )
    else:
        why = (
            f"Your knowledge base has no evidence you understand {display}. "
            f"The book teaches it on page{'s' if page_span != 1 else ''} "
            f"{page_span} — this is exactly the material to read."
        )

    if is_historical:
        why += " ⚠ Historical: flagged as potentially outdated."

    if state is not None and state.my_status in (LEARNING, LEARNED, MASTERED):
        my_status = state.my_status
    else:
        my_status = UNKNOWN

    return {
        "concept": canonical,
        "display_name": display,
        "status": status,
        "my_status": my_status,
        "knowledge_level": knowledge_level,
        "difficulty": difficulty,
        "est_minutes": est_minutes,
        "is_historical": is_historical,
        "historical_note": historical_note,
        "why": why,
        "chapter": chapter,
        "section": None,  # set by caller from occurrence pages
    }


def _page_span_of(entry: dict[str, Any]) -> int:
    pages = entry["pages"]
    if not pages:
        return 0
    return max(pages) - min(pages) + 1


# ---------------------------------------------------------------------------
# Public pipeline
# ---------------------------------------------------------------------------

def analyze_pages(
    db: Session,
    user_id: int,
    book: Book,
    pages: list[str],
) -> dict[str, Any]:
    """Run the full pipeline over already-extracted page text (testable
    without a real PDF). Persists the analysis + items and returns the
    dashboard payload."""
    total_pages = len(pages)
    if total_pages == 0:
        raise NoExtractableTextError("Book has no extractable text")

    chapter_map, chapters_meta = _detect_structure(pages)
    concepts = _collect_concepts(db, user_id, pages, chapter_map)

    # Batched vault evidence for every concept in one call (like the engine).
    vault_concepts = db.query(KbConcept).filter(KbConcept.user_id == user_id).all()
    vault_index = _build_vault_index(vault_concepts)
    targets = [{"name": canonical} for canonical in concepts]
    evidence_map = _vault_evidence_for(db, user_id, targets, vault_index) if targets else {}

    # Build items (bounded), deduped per concept (cross-page grouping).
    items: list[BookGapItem] = []
    ordered = sorted(
        concepts.items(),
        key=lambda kv: (-_page_span_of(kv[1]), kv[0]),
    )[:MAX_CONCEPTS_PER_BOOK]

    for canonical, entry in ordered:
        pages_list = sorted(set(entry["pages"]))
        if not pages_list:
            continue
        page_span = _page_span_of(entry)
        state = _state_status(db, user_id, canonical)
        ev = evidence_map.get(canonical)
        vault_level = _level_for(ev) if ev else "Not Found"

        chapter = next((c for c in entry["chapters"] if c), None) or "Untitled"
        snippet = entry["snippets"][0] if entry["snippets"] else ""
        item_data = _classify(
            db, user_id, canonical, entry["display"], page_span,
            vault_level, ev, state, chapter, snippet, book.title,
        )
        # Section of the first occurrence page.
        first_page = pages_list[0]
        item_data["section"] = _section_of(pages[first_page - 1]) if first_page <= total_pages else None

        item = BookGapItem(
            user_id=user_id,
            book_id=book.id,
            concept=item_data["concept"],
            display_name=item_data["display_name"],
            chapter=item_data["chapter"],
            section=item_data["section"],
            page_start=min(pages_list),
            page_end=max(pages_list),
            snippet=snippet or None,
            why=item_data["why"],
            status=item_data["status"],
            my_status=item_data["my_status"],
            knowledge_level=item_data["knowledge_level"],
            difficulty=item_data["difficulty"],
            est_minutes=item_data["est_minutes"],
            is_historical=item_data["is_historical"],
            historical_note=item_data["historical_note"],
        )
        items.append(item)

    # Recommended reading pages = union of unknown + partial spans.
    recommend_pages: set[int] = set()
    for it in items:
        if it.status in (UNKNOWN, PARTIAL):
            for p in range(it.page_start or 0, (it.page_end or it.page_start or 0) + 1):
                recommend_pages.add(p)
    recommended_pct = round(len(recommend_pages) / total_pages * 100, 1) if total_pages else 0.0

    # Persist: replace items + upsert analysis (idempotent re-analysis).
    db.query(BookGapItem).filter(BookGapItem.book_id == book.id).delete()
    for it in items:
        db.add(it)
    analysis = (
        db.query(BookGapAnalysis)
        .filter(BookGapAnalysis.user_id == user_id, BookGapAnalysis.book_id == book.id)
        .first()
    )
    if analysis is None:
        analysis = BookGapAnalysis(user_id=user_id, book_id=book.id)
        db.add(analysis)
    analysis.status = "done"
    analysis.total_pages = total_pages
    analysis.chapters = len(chapters_meta)
    analysis.total_concepts = len(items)
    analysis.known = sum(1 for it in items if it.status == KNOWN)
    analysis.partial = sum(1 for it in items if it.status == PARTIAL)
    analysis.unknown = sum(1 for it in items if it.status == UNKNOWN)
    analysis.historical = sum(1 for it in items if it.is_historical)
    analysis.recommended_pages = len(recommend_pages)
    analysis.recommended_pct = recommended_pct
    analysis.errors_json = None
    db.commit()

    return {
        "analysis": _analysis_payload(analysis),
        "chapters": chapters_meta,
        "items": len(items),
    }


# ---------------------------------------------------------------------------
# TOC-first workflow (Stage 1 — deterministic structure analysis)
# ---------------------------------------------------------------------------

def analyze_toc(
    db: Session,
    user_id: int,
    book: Book,
    pages: list[str],
) -> dict[str, Any]:
    """Stage 1 — TOC/heading analysis (deterministic, NO LLM).

    Extracts the book's heading hierarchy (chapters → sections →
    subsections), matches every topic against the Second Brain semantically
    (exact / alias / token / subset, reusing the gap engine's real
    evidence), and persists one ``BookGapTopic`` row per topic. The expensive
    per-topic deep comparison is a separate explicit action
    (``analyze_topic_deep``).
    """
    total_pages = len(pages)
    if total_pages == 0:
        raise NoExtractableTextError("Book has no extractable text")

    chapter_map, chapters_meta = _detect_structure(pages)
    toc = _extract_toc(pages, chapter_map, chapters_meta)

    vault_concepts = db.query(KbConcept).filter(KbConcept.user_id == user_id).all()
    vault_index = _build_vault_index(vault_concepts)

    # Persist topics (idempotent: replace on re-analysis).
    db.query(BookGapTopic).filter(
        BookGapTopic.book_id == book.id, BookGapTopic.user_id == user_id
    ).delete()

    # Match every topic against the Second Brain first (pure, no side
    # effects) so we can apply the child-coverage rule afterwards: a parent
    # whose broad topic is known but whose specific subtopics are missing is
    # PARTIALLY_KNOWN ("you have Authentication, but not OAuth/JWT/MFA").
    matches = [
        (t, _match_topic_to_brain(db, user_id, t["title"], vault_index)) for t in toc
    ]
    status_by_title = {t["title"]: m["status"] for t, m in matches}
    for t, m in matches:
        if m["status"] in (KNOWN, PARTIAL):
            children = [c["title"] for c, _ in matches if c.get("parent_title") == t["title"]]
            if children and any(
                status_by_title.get(c) in (UNKNOWN, NEEDS_REVIEW) for c in children
            ):
                m["status"] = PARTIAL

    known = partial = unknown = needs_review = 0
    recommend_pages: set[int] = set()
    topics_payload: list[dict[str, Any]] = []
    for t, m in matches:
        topic = BookGapTopic(
            user_id=user_id,
            book_id=book.id,
            title=t["title"][:300],
            level=t["level"],
            parent_title=t.get("parent_title"),
            page_start=t["page_start"],
            page_end=t["page_end"],
            status=m["status"],
            match_source=m["match_source"],
            second_brain_match=m["second_brain_match"],
            confidence=m["confidence"],
            deep_status=NOT_ANALYZED,
        )
        db.add(topic)
        db.flush()
        if m["status"] == KNOWN:
            known += 1
        elif m["status"] == PARTIAL:
            partial += 1
        elif m["status"] == NEEDS_REVIEW:
            needs_review += 1
        else:
            unknown += 1
        if m["status"] != KNOWN:
            for p in range(t["page_start"], t["page_end"] + 1):
                recommend_pages.add(p)
        topics_payload.append(_topic_payload(topic))

    recommended_pct = round(len(recommend_pages) / total_pages * 100, 1) if total_pages else 0.0

    analysis = (
        db.query(BookGapAnalysis)
        .filter(BookGapAnalysis.user_id == user_id, BookGapAnalysis.book_id == book.id)
        .first()
    )
    if analysis is None:
        analysis = BookGapAnalysis(user_id=user_id, book_id=book.id)
        db.add(analysis)
    analysis.status = "done"
    analysis.total_pages = total_pages
    analysis.chapters = len(chapters_meta)
    analysis.total_concepts = len(toc)
    analysis.known = known
    analysis.partial = partial
    analysis.unknown = unknown
    analysis.needs_review = needs_review
    analysis.historical = 0
    analysis.recommended_pages = len(recommend_pages)
    analysis.recommended_pct = recommended_pct
    analysis.errors_json = None
    db.commit()

    return {
        "analysis": _analysis_payload(analysis),
        "chapters": chapters_meta,
        "topics": topics_payload,
        "items": 0,
    }


def _topic_payload(topic: BookGapTopic) -> dict[str, Any]:
    deep = json.loads(topic.deep_result_json) if topic.deep_result_json else None
    return {
        "id": topic.id,
        "book_id": topic.book_id,
        "title": topic.title,
        "level": topic.level,
        "parent_title": topic.parent_title,
        "page_start": topic.page_start,
        "page_end": topic.page_end,
        "status": topic.status,
        "match_source": topic.match_source,
        "second_brain_match": topic.second_brain_match,
        "confidence": round(topic.confidence or 0.0, 2),
        "deep_status": topic.deep_status,
        "deep_result": deep,
        "analyzed_at": topic.analyzed_at.isoformat() if topic.analyzed_at else None,
    }


def list_topics(db: Session, user_id: int, book_id: int) -> list[dict[str, Any]]:
    """All TOC topics for a book, in reading order."""
    topics = (
        db.query(BookGapTopic)
        .filter(BookGapTopic.book_id == book_id, BookGapTopic.user_id == user_id)
        .order_by(BookGapTopic.page_start.asc(), BookGapTopic.level.asc())
        .all()
    )
    return [_topic_payload(t) for t in topics]


def _topic_or_404(db: Session, user_id: int, book_id: int, topic_id: int) -> BookGapTopic:
    topic = (
        db.query(BookGapTopic)
        .filter(
            BookGapTopic.id == topic_id,
            BookGapTopic.book_id == book_id,
            BookGapTopic.user_id == user_id,
        )
        .first()
    )
    if topic is None:
        raise ValueError("Topic not found")
    return topic


# ---------------------------------------------------------------------------
# Stage 2 — deep topic-level analysis (explicit user action, LLM)
# ---------------------------------------------------------------------------

def _sb_context_for_topic(
    db: Session, user_id: int, topic: BookGapTopic, vault_index: list[dict]
) -> str:
    """Relevant Second Brain content for a topic (matched concept's docs).

    Returns the content of up to 3 real vault documents that MENTIONS the
    matched concept, heading-prefixed and capped for the LLM."""
    m = _match_topic_to_brain(db, user_id, topic.title, vault_index)
    matched_name = m["second_brain_match"]
    if not matched_name:
        return ""
    concept = (
        db.query(KbConcept)
        .filter(
            KbConcept.user_id == user_id,
            KbConcept.canonical_name == matched_name,
        )
        .first()
    )
    if concept is None:
        return ""
    rows = (
        db.query(KbEdge, KbDocument)
        .join(KbDocument, KbEdge.source_document_id == KbDocument.id)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.relation == "MENTIONS",
            KbEdge.target_type == "concept",
            KbEdge.target_concept_id == concept.id,
            KbDocument.status != "deleted",
        )
        .order_by(KbEdge.weight.desc())
        .limit(3)
        .all()
    )
    parts: list[str] = []
    used = 0
    for _edge, doc in rows:
        from app.services.kb.summarize import document_content

        content = document_content(db, doc)[:MAX_SB_CHARS_FOR_LLM]
        if not content.strip():
            continue
        parts.append(f"### {doc.title or doc.path_rel or f'doc {doc.id}'}\n{content}")
        used += len(content)
        if used >= MAX_SB_CHARS_FOR_LLM:
            break
    return "\n\n".join(parts)


_DEEP_PROMPT = (
    "You are comparing ONE topic from a cybersecurity book against the "
    "reader's existing Second Brain notes on that topic. Identify what the "
    "book teaches that the notes already cover, and — more importantly — the "
    "sub-concepts, techniques, mechanisms, examples and edge cases the book "
    "covers that are MISSING from the notes.\n"
    "Only report what is actually present in the book text. Do not invent "
    "concepts. Keep each missing concept short (2-6 words).\n"
    "Topic: {topic}\n"
    "Book pages:\n{book_text}\n\n"
    "Reader's Second Brain notes:\n{sb_text}\n\n"
    'Return ONLY JSON: {{"summary": "1-2 sentences", '
    '"covered": ["concept", "..."], '
    '"missing": [{"concept": "...", "why": "one sentence"}]}}'
)


def _parse_deep_result(result: object) -> dict[str, Any] | None:
    if not isinstance(result, dict):
        return None
    missing: list[dict] = []
    for item in (result.get("missing") or []):
        if not isinstance(item, dict):
            continue
        name = str(item.get("concept") or "").strip()
        if not name:
            continue
        missing.append(
            {
                "concept": name[:200],
                "why": str(item.get("why") or "").strip()[:500] or None,
            }
        )
    covered = [
        str(c).strip()[:200] for c in (result.get("covered") or [])
        if str(c).strip()
    ]
    return {
        "summary": str(result.get("summary") or "").strip()[:1000] or None,
        "covered": covered,
        "missing": missing,
    }


def _llm_deep_compare(
    db: Session, user_id: int, topic_title: str, book_text: str, sb_text: str
) -> tuple[dict[str, Any], bool]:
    """Budget-gated LLM comparison for one topic. Returns (result, ai_used).

    Never raises: on AI-off / budget-exhausted / parse failure it falls back
    to a deterministic comparison (numbered headings in the book pages that
    don't appear in the Second Brain context)."""
    if not budget_allows(db, user_id):
        return _deterministic_deep(topic_title, book_text, sb_text), False
    from app.services.ai_client import ai_available, generate_json

    if not ai_available():
        return _deterministic_deep(topic_title, book_text, sb_text), False
    prompt = _DEEP_PROMPT.format(
        topic=topic_title,
        book_text=book_text[:MAX_TOPIC_PAGES_FOR_LLM],
        sb_text=sb_text[:MAX_SB_CHARS_FOR_LLM] or "(no notes found — everything is a gap)",
    )
    try:
        result = generate_json(prompt, max_tokens=1600, temperature=0.2)
        parsed = _parse_deep_result(result)
        if parsed is None:
            return _deterministic_deep(topic_title, book_text, sb_text), False
        record_generation(db, user_id, "book")
        parsed["ai_used"] = True
        return parsed, True
    except Exception as exc:  # noqa: BLE001 — LLM failure never breaks deep analysis
        logger.warning("Deep book topic analysis failed for %r: %s", topic_title, exc)
        return _deterministic_deep(topic_title, book_text, sb_text), False


def _deterministic_deep(
    topic_title: str, book_text: str, sb_text: str
) -> dict[str, Any]:
    """Deterministic fallback: numbered sub-headings in the book's topic pages
    not present in the Second Brain context become flagged gaps."""
    sb_lower = sb_text.lower()
    seen: set[str] = set()
    missing: list[dict] = []
    for line in book_text.splitlines():
        line = line.strip()
        m = _SECTION_RE.match(line)
        if not m or len(line) <= len(m.group(1)) + 2:
            continue
        title = line[len(m.group(1)):].strip(" .:-–—")
        if not title or _normalize(title) in _NOISE or title.lower() in seen:
            continue
        seen.add(title.lower())
        if title.lower() in sb_lower or any(
            t in sb_lower for t in _tokens(title)
        ):
            continue
        missing.append(
            {
                "concept": title[:200],
                "why": "Numbered section in the book's coverage of this topic "
                "that your Second Brain does not mention — review the pages "
                "to decide whether to capture it.",
            }
        )
    return {
        "summary": (
            f"Compared the book's “{topic_title}” pages against your Second Brain. "
            + (f"{len(missing)} sub-section(s) look missing from your notes." if missing
               else "No obvious gaps found from headings alone — open the pages to verify.")
        ),
        "covered": [],
        "missing": missing[:12],
        "ai_used": False,
        "deterministic": True,
    }


def analyze_topic_deep(
    db: Session, user_id: int, book_id: int, topic_id: int
) -> dict[str, Any]:
    """Stage 2 — deep analysis of ONE topic (explicit user action).

    Extracts ONLY the topic's page range from the PDF, retrieves the matching
    Second Brain documents, and runs a budget-gated LLM comparison. The result
    is persisted on the topic row (``deep_status=ANALYZED``) and missing
    sub-concepts are written as ``BookGapItem`` rows (with page evidence) so
    they feed the reading queue / mark-learned machinery. Re-running replaces
    the previous deep result for this topic (explicit Re-analyze only)."""
    topic = _topic_or_404(db, user_id, book_id, topic_id)
    book = (
        db.query(Book).filter(Book.id == book_id, Book.user_id == user_id).first()
    )
    if book is None:
        raise ValueError("Book not found")

    topic.deep_status = ANALYZING
    db.commit()

    try:
        path = _book_file_path(book)
        pages = extract_pdf_pages(str(path))
        start = max(1, topic.page_start or 1)
        end = min(len(pages), topic.page_end or start)
        topic_text = "\n\n".join(pages[start - 1:end])[:MAX_TOPIC_PAGES_FOR_LLM]

        vault_concepts = db.query(KbConcept).filter(KbConcept.user_id == user_id).all()
        vault_index = _build_vault_index(vault_concepts)
        sb_text = _sb_context_for_topic(db, user_id, topic, vault_index)

        result, ai_used = _llm_deep_compare(
            db, user_id, topic.title, topic_text, sb_text
        )
        result["ai_used"] = ai_used

        # Missing sub-concepts → BookGapItem rows with page evidence.
        db.query(BookGapItem).filter(
            BookGapItem.deep_topic_id == topic.id
        ).delete()
        for miss in result.get("missing", []):
            concept = miss["concept"]
            page = _find_page_for_concept(pages, concept, start, end) or start
            db.add(
                BookGapItem(
                    user_id=user_id,
                    book_id=book.id,
                    deep_topic_id=topic.id,
                    concept=concepts_service.canonicalize(concept) or concept,
                    display_name=concept,
                    chapter=topic.parent_title or topic.title,
                    section=topic.title,
                    page_start=page,
                    page_end=page,
                    snippet=None,
                    why=miss.get("why"),
                    status=UNKNOWN,
                    my_status=UNKNOWN,
                    knowledge_level=0,
                    difficulty="Beginner",
                    est_minutes=max(5, round((end - start + 1) * EST_MINUTES_PER_PAGE)),
                    is_historical=False,
                )
            )

        topic.deep_status = ANALYZED
        topic.deep_result_json = json.dumps(result, default=str)
        topic.analyzed_at = datetime.now(timezone.utc)
        db.commit()

        # Bump the analysis rollup's deep_analyzed count.
        analysis = (
            db.query(BookGapAnalysis)
            .filter(BookGapAnalysis.user_id == user_id, BookGapAnalysis.book_id == book.id)
            .first()
        )
        if analysis is not None:
            analysis.deep_analyzed = (
                db.query(BookGapTopic)
                .filter(
                    BookGapTopic.book_id == book.id,
                    BookGapTopic.user_id == user_id,
                    BookGapTopic.deep_status == ANALYZED,
                )
                .count()
            )
            db.commit()
        return _topic_payload(topic)
    except Exception as exc:  # noqa: BLE001 — surface as FAILED, never crash the request
        db.rollback()
        logger.exception("Deep book topic analysis failed for topic %s", topic_id)
        topic = _topic_or_404(db, user_id, book_id, topic_id)
        topic.deep_status = FAILED
        topic.deep_result_json = json.dumps({"error": str(exc)[:500]})
        db.commit()
        return _topic_payload(topic)


def _find_page_for_concept(
    pages: list[str], concept: str, start: int, end: int
) -> int | None:
    """First page in the range where the concept appears (page evidence)."""
    terms = [t for t in _tokens(concept) if len(t) >= 3]
    for i in range(start - 1, min(end, len(pages))):
        lower = pages[i].lower()
        if not terms:
            if concept.lower() in lower:
                return i + 1
            continue
        if all(t in lower for t in terms):
            return i + 1
    return None


def add_topic_to_brain(
    db: Session, user_id: int, book_id: int, topic_id: int
) -> dict[str, Any]:
    """Add an UNKNOWN/NEEDS_REVIEW topic to the Second Brain as a study note.

    Reuses the gap engine's ``create_gap_note`` (idempotent draft capture
    note) so the topic gets a real KbDocument draft the user can fill in."""
    topic = _topic_or_404(db, user_id, book_id, topic_id)
    book = (
        db.query(Book).filter(Book.id == book_id, Book.user_id == user_id).first()
    )
    if book is None:
        raise ValueError("Book not found")
    from app.services.kb.gap_engine import create_gap_note

    doc, created = create_gap_note(
        db,
        user_id,
        topic.title,
        subject=book.title,
        why=f"Added from the book “{book.title}” — this topic is not currently "
        "represented in your Second Brain. Fill in what you learn from the pages.",
        learn=[
            f"Capture what the book teaches about {topic.title} (pages {topic.page_start}–{topic.page_end}).",
            "Define the key techniques/mechanisms in your own words.",
        ],
        practice=["Summarize it in one paragraph from memory."],
    )
    return {
        "document": {"id": doc.id, "title": doc.title, "status": doc.status},
        "created": created,
        "topic_id": topic.id,
    }


def analyze_book(db: Session, user_id: int, book_id: int) -> dict[str, Any]:
    """Resolve the book, extract PDF pages, run Stage-1 TOC analysis.

    Stage 1 is deterministic (structure + Second Brain matching) — it never
    calls the LLM. Deep per-topic analysis is the separate explicit action
    ``analyze_topic_deep``."""
    book = (
        db.query(Book).filter(Book.id == book_id, Book.user_id == user_id).first()
    )
    if book is None:
        raise ValueError("Book not found")
    path = _book_file_path(book)
    if not path.exists():
        raise NoExtractableTextError("Book PDF file is missing on disk")
    pages = extract_pdf_pages(str(path))
    return analyze_toc(db, user_id, book, pages)


def _analysis_payload(analysis: BookGapAnalysis) -> dict[str, Any]:
    return {
        "book_id": analysis.book_id,
        "status": analysis.status,
        "total_pages": analysis.total_pages,
        "chapters": analysis.chapters,
        "total_concepts": analysis.total_concepts,
        "known": analysis.known,
        "partial": analysis.partial,
        "unknown": analysis.unknown,
        "needs_review": analysis.needs_review or 0,
        "deep_analyzed": analysis.deep_analyzed or 0,
        "historical": analysis.historical,
        "recommended_pages": analysis.recommended_pages,
        "recommended_pct": analysis.recommended_pct,
        "analyzed_at": analysis.analyzed_at.isoformat() if analysis.analyzed_at else None,
        "errors": json.loads(analysis.errors_json) if analysis.errors_json else [],
    }


def get_analysis(db: Session, user_id: int, book_id: int) -> dict[str, Any] | None:
    analysis = (
        db.query(BookGapAnalysis)
        .filter(BookGapAnalysis.user_id == user_id, BookGapAnalysis.book_id == book_id)
        .first()
    )
    return _analysis_payload(analysis) if analysis else None


def dashboard(db: Session, user_id: int, book_id: int) -> dict[str, Any]:
    """Book dashboard: analysis rollup + chapter-level counts + topics."""
    analysis = get_analysis(db, user_id, book_id)
    if analysis is None:
        return {"analysis": None, "chapters": [], "topics": []}

    topics = (
        db.query(BookGapTopic)
        .filter(BookGapTopic.book_id == book_id, BookGapTopic.user_id == user_id)
        .order_by(BookGapTopic.page_start.asc(), BookGapTopic.level.asc())
        .all()
    )
    items = (
        db.query(BookGapItem)
        .filter(BookGapItem.user_id == user_id, BookGapItem.book_id == book_id)
        .all()
    )

    # Chapter rollup from topics when present (TOC-first flow); falls back to
    # the legacy items-based rollup for books analyzed before this workflow.
    by_chapter: dict[str, dict[str, int]] = defaultdict(
        lambda: {"known": 0, "partial": 0, "unknown": 0, "historical": 0}
    )
    status_key = {KNOWN: "known", PARTIAL: "partial", UNKNOWN: "unknown"}
    if topics:
        for t in topics:
            name = t.parent_title or t.title
            c = by_chapter[name]
            c[status_key.get(t.status, "unknown")] += 1
    else:
        for it in items:
            c = by_chapter[it.chapter or "Untitled"]
            c[status_key.get(it.status, "unknown")] += 1
            if it.is_historical:
                c["historical"] += 1
    chapters = [
        {"chapter": name, **counts}
        for name, counts in sorted(by_chapter.items(), key=lambda kv: (kv[0] or "").lower())
    ]
    return {
        "analysis": analysis,
        "chapters": chapters,
        "topics": [_topic_payload(t) for t in topics],
    }


def list_items(
    db: Session, user_id: int, book_id: int, *, status: str | None = None, chapter: str | None = None
) -> list[dict[str, Any]]:
    q = db.query(BookGapItem).filter(
        BookGapItem.user_id == user_id, BookGapItem.book_id == book_id
    )
    if status:
        q = q.filter(BookGapItem.status == status)
    if chapter:
        q = q.filter(BookGapItem.chapter == chapter)
    items = q.order_by(BookGapItem.status, BookGapItem.est_minutes.desc()).all()
    return [_item_payload(it) for it in items]


def _item_payload(it: BookGapItem) -> dict[str, Any]:
    return {
        "id": it.id,
        "book_id": it.book_id,
        "deep_topic_id": it.deep_topic_id,
        "concept": it.concept,
        "display_name": it.display_name,
        "chapter": it.chapter,
        "section": it.section,
        "page_start": it.page_start,
        "page_end": it.page_end,
        "snippet": it.snippet,
        "why": it.why,
        "status": it.status,
        "my_status": it.my_status,
        "knowledge_level": it.knowledge_level,
        "difficulty": it.difficulty,
        "est_minutes": it.est_minutes,
        "is_historical": it.is_historical,
        "historical_note": it.historical_note,
    }


def reading_queue(db: Session, user_id: int, book_id: int) -> list[dict[str, Any]]:
    """Prioritized reading queue: UNKNOWN first, then PARTIALLY_KNOWN; within
    a tier by knowledge gap × difficulty × page span. Learned items excluded."""
    items = (
        db.query(BookGapItem)
        .filter(
            BookGapItem.user_id == user_id,
            BookGapItem.book_id == book_id,
            BookGapItem.status.in_((UNKNOWN, PARTIAL)),
            BookGapItem.my_status.notin_((LEARNED, MASTERED)),
        )
        .all()
    )
    rank = {UNKNOWN: 0, PARTIAL: 1}
    span = lambda it: max(1, (it.page_end or it.page_start or 0) - (it.page_start or 0) + 1)  # noqa: E731
    items.sort(
        key=lambda it: (
            rank.get(it.status, 9),
            -(3 - it.knowledge_level),
            -span(it),
            it.display_name.lower(),
        )
    )
    return [_item_payload(it) for it in items]


def mark_item_status(
    db: Session, user_id: int, book_id: int, item_id: int, status: str
) -> dict[str, Any]:
    """Set the user's learning progress on an item and mirror it to the
    cumulative cross-book store. ``status`` ∈ learning | learned | mastered."""
    if status not in (LEARNING, LEARNED, MASTERED):
        raise ValueError("Invalid status")
    item = (
        db.query(BookGapItem)
        .filter(
            BookGapItem.id == item_id,
            BookGapItem.book_id == book_id,
            BookGapItem.user_id == user_id,
        )
        .first()
    )
    if item is None:
        raise ValueError("Gap item not found")
    item.my_status = status
    if status in (LEARNED, MASTERED):
        item.learned_from_book_id = book_id
    state = _state_status(db, user_id, item.concept)
    if state is None:
        state = BookConceptState(user_id=user_id, concept=item.concept)
        db.add(state)
    state.my_status = status
    state.learned_from_book_id = book_id if status in (LEARNED, MASTERED) else None
    state.page_ref = item.page_start
    db.commit()
    return _item_payload(item)


def overview(db: Session, user_id: int) -> dict[str, Any]:
    """Cumulative dashboard across every uploaded book (analyzed or not)."""
    books = (
        db.query(Book)
        .filter(Book.user_id == user_id)
        .order_by(Book.created_at.desc())
        .all()
    )
    analyses = {
        a.book_id: a
        for a in db.query(BookGapAnalysis).filter(BookGapAnalysis.user_id == user_id).all()
    }
    book_rows = []
    total_known = total_partial = total_unknown = total_concepts = 0
    recommended_minutes = 0
    for book in books:
        analysis = analyses.get(book.id)
        if analysis is None:
            book_rows.append(
                {
                    "book_id": book.id,
                    "title": book.title,
                    "author": book.author,
                    "file_url": book.file_url,
                    "analyzed": False,
                    "total_concepts": 0,
                    "known": 0,
                    "partial": 0,
                    "unknown": 0,
                    "recommended_pct": 0.0,
                }
            )
            continue
        unknown = analysis.unknown
        partial = analysis.partial
        known = analysis.known
        total_concepts += analysis.total_concepts
        total_known += known
        total_partial += partial
        total_unknown += unknown
        recommended_minutes += round(partial * EST_MINUTES_PER_PAGE)
        book_rows.append(
            {
                "book_id": book.id,
                "title": book.title,
                "author": book.author,
                "file_url": book.file_url,
                "analyzed": True,
                "total_concepts": analysis.total_concepts,
                "known": known,
                "partial": partial,
                "unknown": unknown,
                "needs_review": analysis.needs_review or 0,
                "deep_analyzed": analysis.deep_analyzed or 0,
                "recommended_pct": analysis.recommended_pct,
            }
        )
    learned = (
        db.query(BookConceptState)
        .filter(
            BookConceptState.user_id == user_id,
            BookConceptState.my_status.in_((LEARNED, MASTERED)),
        )
        .count()
    )
    return {
        "books": book_rows,
        "total_concepts": total_concepts,
        "total_known": total_known,
        "total_partial": total_partial,
        "total_unknown": total_unknown,
        "learned_concepts": learned,
        "recommended_minutes": recommended_minutes,
    }
