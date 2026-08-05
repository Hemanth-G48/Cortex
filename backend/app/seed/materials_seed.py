"""Seed demo materials for SyllabusAI."""

from __future__ import annotations

import os

from sqlalchemy.orm import Session

from app.config import settings
from app.models import CurriculumUnit, Material


def parts_demo_materials(db: Session) -> None:
    """Idempotently seed demo materials for each curriculum unit."""
    # Only seed if no materials exist yet.
    if db.query(Material).first() is not None:
        return

    units = db.query(CurriculumUnit).all()
    if not units:
        return

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    for n, unit in enumerate(units, start=1):
        text = f"This is the demo material for {unit.name} (unit {unit.unit_number}).\n\nIt provides an overview of the key topics covered in this curriculum unit."
        filename = f"demotext_{n}.txt"
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)

        material = Material(
            unit_id=unit.id,
            title=f"Demo: {unit.name}",
            file_type="txt",
            file_url=f"/uploads/{filename}",
            file_size=len(text),
            original_file_name="demo_material.txt",
            extracted_text=text,
        )
        db.add(material)

    db.commit()
