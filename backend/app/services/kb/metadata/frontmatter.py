"""Frontmatter parsing helpers — extracted from ``course_derivation.py`` (F4).

These are pure functions with no domain-specific logic. They normalize Obsidian-
style YAML frontmatter values (status, color, description) into the app's
canonical forms. Used by course derivation and course content modules.
"""

from __future__ import annotations

import re
from typing import Any

# Folder-level metadata: a folder may carry an ``index.md`` (or ``_index.md``)
# whose YAML frontmatter drives the *derived subject's* description, status and
# color. Anything not recognised falls back to the folder-derivation defaults
# (status ``In progress``, no description/color).
_STATUS_MAP = {
    "not started": "Not started",
    "todo": "Not started",
    "planned": "Not started",
    "planning": "Not started",
    "backlog": "Not started",
    "in progress": "In progress",
    "active": "In progress",
    "ongoing": "In progress",
    "wip": "In progress",
    "doing": "In progress",
    "completed": "Completed",
    "complete": "Completed",
    "done": "Completed",
    "finished": "Completed",
    "archive": "Completed",
    "archived": "Completed",
}

# Named colors the frontend can consume directly as CSS color values (the
# Tailwind-ish palette used across the app's badges/chips).
_NAMED_COLORS = {
    "red", "orange", "amber", "yellow", "lime", "green", "emerald", "teal",
    "cyan", "sky", "blue", "indigo", "violet", "purple", "fuchsia", "pink",
    "rose", "slate", "gray", "grey", "zinc", "neutral", "stone",
}

# Optional keys tried (in order) when looking up a metadata field, so common
# Obsidian frontmatter naming variants all work.
_DESCRIPTION_KEYS = ("description", "summary", "subtitle", "about")
_STATUS_KEYS = ("status", "state")
_COLOR_KEYS = ("color", "colour", "accent")


def _normalize_status(value: Any) -> str:
    """Map arbitrary frontmatter status text onto the app's three statuses.

    Unknown values (and missing frontmatter) fall back to the folder
    derivation default (``In progress``).
    """
    if isinstance(value, str):
        key = value.strip().lower()
        if key in _STATUS_MAP:
            return _STATUS_MAP[key]
    return "In progress"


def _normalize_color(value: Any) -> str | None:
    """Accept a hex color (``#abc`` / ``#aabbcc`` / ``#aabbccdd``) or a named
    CSS color; anything else is ignored so junk frontmatter can't leak into the
    UI as an invalid inline style."""
    if not isinstance(value, str):
        return None
    color = value.strip()
    if not color:
        return None
    if color.lower() in _NAMED_COLORS:
        return color.lower()
    if re.fullmatch(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?(?:[0-9a-fA-F]{2})?", color):
        return color.lower()
    return None


def _meta_description(meta: dict[str, Any]) -> str | None:
    """First non-empty string among the description-ish frontmatter keys."""
    for key in _DESCRIPTION_KEYS:
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:2000]
    return None
