"""Text extraction from uploaded study documents (SyllabusAI materials).

Supports TXT, PDF (pypdf), and DOCX (python-docx). Unknown formats
raise ``NoExtractableTextError`` so callers can return a clear 400.
"""

from __future__ import annotations

from pathlib import Path

EXTRACTABLE_TYPES = {"pdf", "docx", "txt", "md"}


class NoExtractableTextError(Exception):
    """Raised when a file has no extractable text or an unsupported type."""


def extract(file_path: str, file_type: str) -> str:
    """Return the plain text of the file at ``file_path``.

    Parameters
    ----------
    file_path: path on disk to the file.
    file_type: extension without leading dot (e.g. "pdf", "txt").

    Raises
    ------
    NoExtractableTextError: on unsupported type or empty/whitespace-only result.
    """
    ext = file_type.lower()
    if ext not in EXTRACTABLE_TYPES:
        raise NoExtractableTextError(f"Unsupported file type: {ext}")

    path = Path(file_path)

    if ext == "pdf":
        from pypdf import PdfReader  # noqa: PLC0415

        try:
            reader = PdfReader(path)
            parts = []
            for page in reader.pages:
                text = page.extract_text() or ""
                if text.strip():
                    parts.append(text)
            result = "\n".join(parts)
        except Exception:  # noqa: BLE001 — corrupt/garbage PDFs raise various pypdf errors
            raise NoExtractableTextError("Could not extract text from PDF")  # noqa: B904

    elif ext == "docx":
        from docx import Document  # noqa: PLC0415

        document = Document(path)
        result = "\n".join(p.text for p in document.paragraphs)

    else:  # txt or md
        result = path.read_text(encoding="utf-8", errors="replace")

    result = result.strip()
    if not result:
        raise NoExtractableTextError("No extractable text")

    return result


def extract_pdf_pages(file_path: str) -> list[str]:
    """Return per-page text of a PDF (page boundaries for OCR, Idea 5/6).

    ``extract()`` is intentionally unchanged so existing callers keep working.
    """
    from pypdf import PdfReader  # noqa: PLC0415

    reader = PdfReader(Path(file_path))
    return [page.extract_text() or "" for page in reader.pages]


def extract_multiple(files: list[tuple[str, str]]) -> str:
    """Extract text from multiple files, joining with headers.

    Each element is ``(file_path, file_type)``. Files that raise
    ``NoExtractableTextError`` or have an unsupported type are skipped.
    """
    chunks: list[str] = []
    for file_path, file_type in files:
        try:
            text = extract(file_path, file_type)
        except NoExtractableTextError:
            continue
        if not text:
            continue
        name = Path(file_path).name
        chunks.append(f"--- {name} ---\n{text}")
    return "\n\n".join(chunks)
