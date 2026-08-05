"""Material model for SyllabusAI curriculum materials."""

from __future__ import annotations

import os

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship

from app.database import Base
from app.config import settings


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("curriculum_units.id"), nullable=False)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(300))
    description = Column(Text, nullable=True)
    file_type = Column(String(20))
    file_url = Column(String(500))
    file_size = Column(Integer)
    original_file_name = Column(String(260))
    view_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    extracted_text = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    unit = relationship("CurriculumUnit")

    def file_path_on_disk(self) -> str:
        return os.path.join(settings.UPLOAD_DIR, os.path.basename(self.file_url))
