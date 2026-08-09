"""OCR for scanned/image-only documents (Idea 6).

Fully import-guarded — when ``KB_OCR_ENABLED=false`` or pytesseract/pdf2image/
Pillow or the system tesseract binary are missing, everything degrades to a
warning and never crashes a scan.
"""

from __future__ import annotations

import logging

from app.config import settings

logger = logging.getLogger(__name__)

# A page that yields less than this many chars is treated as image-only.
LOW_TEXT_CHARS = 50


class OcrUnavailableError(RuntimeError):
    """Raised when OCR cannot run (disabled, missing deps, missing binary)."""


def _imports_ok() -> bool:
    try:
        import pdf2image  # noqa: F401
        import PIL  # noqa: F401
        import pytesseract  # noqa: F401

        return True
    except Exception:  # noqa: BLE001 — any import failure means no OCR
        return False


def _tesseract_ok() -> bool:
    try:
        import pytesseract

        if settings.kb_tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = settings.kb_tesseract_cmd
        pytesseract.get_tesseract_version()
        return True
    except Exception:  # noqa: BLE001 — missing/invalid binary
        return False


def ocr_available() -> bool:
    """True only when OCR is enabled AND every dependency is present."""
    if not settings.KB_OCR_ENABLED:
        return False
    return _imports_ok() and _tesseract_ok()


def needs_ocr(page_texts: list[str]) -> bool:
    """Flag a PDF when any page yields < ~50 chars (phrase 53)."""
    if not page_texts:
        return False
    return any(len((t or "").strip()) < LOW_TEXT_CHARS for t in page_texts)


def ocr_pdf(path: str) -> str:
    """Render PDF pages to images and run tesseract. Returns merged text.

    Raises :class:`OcrUnavailableError` when dependencies or the binary are
    missing — callers catch it and degrade gracefully.
    """
    if not ocr_available():
        raise OcrUnavailableError("OCR is not available")

    try:
        import pytesseract
        from pdf2image import convert_from_path

        images = convert_from_path(path)
        parts: list[str] = []
        for img in images:
            text = pytesseract.image_to_string(img)
            if text and text.strip():
                parts.append(text.strip())
        return "\n\n".join(parts)
    except OcrUnavailableError:
        raise
    except Exception as exc:  # noqa: BLE001 — poppler/render failures vary
        logger.warning("OCR failed for %s: %s", path, exc)
        raise OcrUnavailableError("OCR failed") from exc
