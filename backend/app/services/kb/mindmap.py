"""Mind-map generation (Phase 4, Idea 38).

Builds a tree from the Phase 1 ``outline_json`` headings (root = document
title), attaches MENTIONS concept chips to the heading under which they appear
(phrase 72), falls back to chunk ``heading_path`` values for non-markdown
documents (phrase 75), and exports Markdown / OPML (phrase 74).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

from sqlalchemy.orm import Session

from app.models import KbChunk, KbConcept, KbDocument, KbEdge
from app.services.kb import KbService


def _concepts_for_range(
    db: Session, user_id: int, doc: KbDocument, start: int, end: int
) -> list[str]:
    """Concept canonical names whose aliases appear within a text range."""
    if doc.doc_type != "md" or not doc.extracted_text:
        return []
    window = doc.extracted_text[start:end].lower()
    rows = (
        db.query(KbConcept)
        .join(KbEdge, KbEdge.target_concept_id == KbConcept.id)
        .filter(
            KbEdge.user_id == user_id,
            KbEdge.source_document_id == doc.id,
            KbEdge.relation == "MENTIONS",
            KbEdge.target_type == "concept",
            KbConcept.user_id == user_id,
        )
        .all()
    )
    names: list[str] = []
    for c in rows:
        terms = [c.canonical_name] + list(KbService.json_loads(c.aliases) or [])
        if any(t and t.lower() in window for t in terms):
            names.append(c.canonical_name)
    return names


def _node(node_id: str, label: str) -> dict:
    return {"id": node_id, "label": label, "children": [], "concepts": [], "chunk_ids": []}


def build_tree(db: Session, user_id: int, doc: KbDocument) -> dict:
    """Return the mind-map tree ``{id, label, children[], concepts[], chunk_ids[]}``."""
    root = _node(f"doc:{doc.id}", doc.title or doc.path_rel or f"doc {doc.id}")

    outline = KbService.json_loads(doc.outline_json) or []
    items: list[dict[str, Any]] = []
    if outline:
        items = [
            {
                "level": int(o["level"]),
                "text": str(o["text"]),
                "char_start": int(o.get("char_start", 0)),
            }
            for o in outline
        ]
    else:
        # Non-markdown fallback: derive headings from chunk heading_path (phrase 75).
        chunks = (
            db.query(KbChunk)
            .filter(KbChunk.document_id == doc.id, KbChunk.user_id == user_id)
            .order_by(KbChunk.seq.asc())
            .all()
        )
        for c in chunks:
            if c.heading_path:
                level = 2 if c.heading_path else 1
                items.append(
                    {
                        "level": level,
                        "text": c.heading_path,
                        "char_start": c.char_start,
                    }
                )
        # Dedupe repeated heading paths.
        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for it in items:
            if it["text"] in seen:
                continue
            seen.add(it["text"])
            deduped.append(it)
        items = deduped

    # Attach chunk_ids per node: all chunks whose heading matches the node text
    # or whose range falls inside the node's section span.
    chunk_ranges: list[dict[str, Any]] = []
    if not outline:
        chunks = (
            db.query(KbChunk)
            .filter(KbChunk.document_id == doc.id, KbChunk.user_id == user_id)
            .order_by(KbChunk.seq.asc())
            .all()
        )
        chunk_ranges = [
            {"id": c.id, "start": c.char_start, "end": c.char_end, "heading": c.heading_path}
            for c in chunks
        ]

    stack: list[dict] = []
    seq = 0
    for it in items:
        node = _node(f"n{seq}", it["text"])
        seq += 1
        # concepts mentioned in this heading's text span
        node["concepts"] = _concepts_for_range(
            db, user_id, doc, it["char_start"], it["char_start"] + 1500
        )
        # chunks whose section falls under this heading
        for cr in chunk_ranges:
            if cr["heading"] == it["text"]:
                node["chunk_ids"].append(cr["id"])

        level = max(1, min(it["level"], 6))
        while stack and stack[-1]["_level"] >= level:
            stack.pop()
        if stack:
            stack[-1]["children"].append(node)
        else:
            root["children"].append(node)
        node["_level"] = level
        stack.append(node)

    # Strip internal markers.
    def clean(n: dict) -> dict:
        n.pop("_level", None)
        for child in n["children"]:
            clean(child)
        return n

    return clean(root)


def export_markdown(tree: dict, base_level: int = 1) -> str:
    """Nested ``#`` outline with concept chips as bullets (phrase 74)."""
    lines: list[str] = []

    def walk(node: dict, level: int) -> None:
        heading = "#" * min(6, level) + " " + node["label"]
        lines.append(heading)
        for concept in node.get("concepts", []):
            lines.append(f"- concept: {concept}")
        for child in node.get("children", []):
            walk(child, level + 1)

    walk(tree, base_level)
    return "\n".join(lines) + "\n"


def export_opml(tree: dict) -> str:
    """OPML outline XML for external mind-map tools (phrase 74)."""
    root = ET.Element("opml", {"version": "2.0"})
    head = ET.SubElement(root, "head")
    ET.SubElement(head, "title").text = tree["label"]

    body = ET.SubElement(root, "body")
    outline_root = ET.SubElement(body, "outline", {"text": tree["label"]})

    def walk(node: dict, parent: ET.Element) -> None:
        for child in node.get("children", []):
            attrs = {"text": child["label"]}
            if child.get("concepts"):
                attrs["_note"] = ", ".join(child["concepts"])
            el = ET.SubElement(parent, "outline", attrs)
            walk(child, el)

    walk(tree, outline_root)
    return ET.tostring(root, encoding="unicode", xml_declaration=True)
