"""Second Brain Knowledge Core services (Phase 1, Ideas 1–10).

Every query filters ``user_id`` — the per-user scoping rule (Idea 2, phrase 11).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models import KbDocument, KbEdge, KbSource

# Directories never indexed during a scan (Idea 3, phrase 24).
NOISE_DIRS = {".obsidian", ".git", ".trash", ".tmp", "node_modules", ".idea"}


def utcnow() -> datetime:
    """Naive UTC now — SQLite-friendly, avoids datetime.utcnow() deprecation."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class KbService:
    """User-scoped helper queries for the Knowledge Core."""

    @staticmethod
    def get_source(db: Session, user_id: int, source_id: int) -> KbSource | None:
        return (
            db.query(KbSource)
            .filter(KbSource.id == source_id, KbSource.user_id == user_id)
            .first()
        )

    @staticmethod
    def get_document(db: Session, user_id: int, document_id: int) -> KbDocument | None:
        return (
            db.query(KbDocument)
            .filter(KbDocument.id == document_id, KbDocument.user_id == user_id)
            .first()
        )

    @staticmethod
    def content_hash(data: bytes) -> str:
        """SHA-256 of raw file bytes — never decoded text (Idea 8, phrase 80)."""
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def get_duplicate_map(source: KbSource) -> dict[str, int]:
        """Load the source's persistent ``{path_rel: canonical_document_id}`` map."""
        data = KbService.json_loads(source.duplicate_map_json)
        return {str(k): int(v) for k, v in (data or {}).items()}

    @staticmethod
    def save_duplicate_map(source: KbSource, mapping: dict[str, int]) -> None:
        """Persist the path→canonical dedupe map back to the source row."""
        source.duplicate_map_json = KbService.json_dumps(mapping)

    @staticmethod
    def find_canonical(db: Session, user_id: int, content_hash: str) -> KbDocument | None:
        """Earliest row for (user, hash) — the dedupe canonical document."""
        return (
            db.query(KbDocument)
            .filter(
                KbDocument.user_id == user_id,
                KbDocument.content_hash == content_hash,
            )
            .order_by(KbDocument.id.asc())
            .first()
        )

    @staticmethod
    def record_duplicate(db: Session, user_id: int, canonical_id: int) -> KbEdge:
        """Upsert the DUPLICATE_OF self-loop edge on the canonical document.

        The edge's source == target == canonical row; ``weight`` counts how many
        duplicate files were seen (Idea 8, phrase 73).
        """
        edge = (
            db.query(KbEdge)
            .filter(
                KbEdge.user_id == user_id,
                KbEdge.source_document_id == canonical_id,
                KbEdge.target_document_id == canonical_id,
                KbEdge.relation == "DUPLICATE_OF",
            )
            .first()
        )
        if edge:
            edge.weight = (edge.weight or 1) + 1
            db.add(edge)
            return edge
        edge = KbEdge(
            user_id=user_id,
            source_document_id=canonical_id,
            target_document_id=canonical_id,
            relation="DUPLICATE_OF",
            weight=1.0,
        )
        db.add(edge)
        return edge

    @staticmethod
    def bool_setting(name: str, default: bool = False) -> bool:
        """Read a boolean config knob defensively (Phase 3 kill switches).

        Returns ``default`` when the setting is absent, so older configs
        degrade safely instead of raising on a missing attribute.
        """
        value = getattr(settings, name, default)
        if value is None:
            return default
        if isinstance(value, str):
            return value.strip().lower() in ("1", "true", "yes", "on")
        return bool(value)

    @staticmethod
    def json_dumps(value: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False, default=str)

    @staticmethod
    def json_loads(text: str | None) -> Any:
        if not text:
            return None
        try:
            return json.loads(text)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def token_estimate(text: str) -> int:
        """Rough token count (≈ chars/4) — Phase 2 embedding batch seam."""
        return max(1, len(text) // 4)
