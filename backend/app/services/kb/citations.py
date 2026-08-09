"""Citation resolution (Phase 3, Idea 25, phrases 41–50).

Turns a search hit into an actionable citation: the source path (relative vault
path for scanned docs, ``/uploads/...`` for PDFs), an optional heading
breadcrumb, a PDF page number derived from the chunk's char offset, and an
open-in-vault target (plain file path, or an Obsidian URI for vault sources).
"""

from __future__ import annotations

from typing import Any

from app.config import settings


def resolve_source_path(doc_type: str, path_rel: str | None) -> str | None:
    """Absolute-ish display path for a document.

    Scanned docs carry a relative vault path; PDF uploads live under
    ``settings.UPLOAD_DIR``.
    """
    if not path_rel:
        return None
    return path_rel


def resolve_page(
    doc_type: str,
    char_start: int,
    page_boundaries: list[tuple[int, int]] | None = None,
) -> int | None:
    """Return the PDF page number containing ``char_start`` (phrase 42).

    ``page_boundaries`` is a list of ``(char_start, char_end)`` per page from
    Phase 1 (Group 5). Falls back to an estimate (page = offset // 3000 chars)
    when boundaries are unavailable.
    """
    if doc_type != "pdf":
        return None
    if page_boundaries:
        for page_no, (start, end) in enumerate(page_boundaries, start=1):
            if start <= char_start <= end:
                return page_no
    return (char_start // 3000) + 1


def open_in_vault_target(source_path: str | None, source_type: str = "local_dir") -> str | None:
    """Build the open-in-vault target (phrase 46).

    Vault sources → an ``obsidian://open?vault=...`` URI; otherwise the file
    path. Returns None when no path is available.
    """
    if not source_path:
        return None
    if source_type == "vault_folder":
        return f"obsidian://open?vault=SecondBrain&file={source_path}"
    return source_path


def build_citation(item: dict[str, Any], source_type: str = "local_dir") -> dict[str, Any]:
    """Add citation fields to a unified search result dict (phrase 43)."""
    page = resolve_page(
        item.get("doc_type", ""),
        item.get("char_start", 0) or 0,
    )
    return {
        **item,
        "source_path": resolve_source_path(item.get("doc_type", ""), item.get("source_path")),
        "page": page,
        "open_in_vault": open_in_vault_target(item.get("source_path"), source_type),
        "heading": item.get("heading_path"),
    }
