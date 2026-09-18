"""KB document metadata package.

Extracted from ``services/kb/metadata.py`` as part of the ``services/kb/``
sub-package reorganization (F2).
"""

from app.services.kb.metadata.frontmatter import (
    _DESCRIPTION_KEYS,
    _STATUS_KEYS,
    _COLOR_KEYS,
    _NAMED_COLORS,
    _normalize_status,
    _normalize_color,
    _meta_description,
)

from app.services.kb.metadata.core import (
    apply_metadata_update,
    propose_metadata,
    detect_language,
    estimate_reading_time,
    enrich_metadata,
    extract_frontmatter,
    generate_json,
    metadata_filters,
)

__all__ = [
    "apply_metadata_update",
    "propose_metadata",
    "detect_language",
    "estimate_reading_time",
    "filter_documents_by_metadata",
    "build_metadata_filter",
    "frontmatter",
]

import app.services.kb.metadata.frontmatter  # noqa: F401
import app.services.kb.metadata.core  # noqa: F401
