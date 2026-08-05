"""Ingestion helpers for SyllabusAI materials."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.models.material import Material
from app.services.text_extractor import NoExtractableTextError, extract

MAX_EXTRACTED_CHARS = 60_000


def text_for_material(db: Session, material: Material) -> str:
    """Return cached ``extracted_text`` or extract from disk and cache it."""
    if material.extracted_text:
        return material.extracted_text

    try:
        text = extract(material.file_path_on_disk(), material.file_type)
    except NoExtractableTextError:
        text = ""

    if len(text) > MAX_EXTRACTED_CHARS:
        text = text[:MAX_EXTRACTED_CHARS]

    material.extracted_text = text or None
    db.add(material)
    db.commit()
    return material.extracted_text or ""


def extract_text_for_units(db: Session, unit_ids: list[int]) -> str:
    """Gather extracted text for all active materials in the given units."""
    materials = (
        db.query(Material)
        .filter(Material.unit_id.in_(unit_ids), Material.is_active == True)  # noqa: E712
        .all()
    )
    parts: list[str] = []
    for material in materials:
        text = text_for_material(db, material)
        if not text:
            continue
        parts.append(f"--- {material.title} ---\n{text}")
    return "\n\n".join(parts)
