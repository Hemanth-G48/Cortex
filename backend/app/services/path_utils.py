"""Path sanitization utilities — single source of truth for turning a KbDocument
source path or user-provided filename into a safe filesystem path.

Every place that reconstructs a filesystem path from a user-controlled string
must use these helpers so traversal defenses are consistent and auditable.
"""

from __future__ import annotations

from pathlib import Path


def safe_path(rel: str, *, base: Path | None = None) -> Path:
    """Normalise a user-controlled relative path into a safe filesystem path.

    Strips directory components (so ``../../etc/passwd`` → ``passwd``),
    removes ``..`` segments, and optionally anchors the result under a base
    directory. Never raises on malformed input — returns a safe Path or, if
    the result is empty after sanitization, Path("unnamed").

    Usage::

        # For upload filenames (just strip to basename):
        safe = safe_path(filename).name

        # For KbDocument.source → filesystem path:
        target = safe_path(doc.path_rel, base=settings.UPLOAD_DIR)
    """
    # Strip to the final path component first — kills any ../ traversal.
    name = Path(rel).name if rel else ""
    if not name or name in (".", ".."):
        name = "unnamed"
    # Remove any remaining .. segments (defense in depth).
    parts = [p for p in Path(name).parts if p not in ("..", ".")
             and not p.startswith(".")]
    if not parts:
        parts = ["unnamed"]
    result = Path(*parts)
    if base is not None:
        result = base / result
    return result
