"""Research-paper import from arXiv (Idea 5, phrases 45–48)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KbChunk, KbDocument, User
from app.schemas.kb import KbDocumentResponse, KbPaperImport, KbPaperImportResult
from app.services.kb import KbService, utcnow
from app.services.kb import arxiv
from app.services.kb.pipeline import _parse_markdown_meta, re_chunk
from app.services.security import get_current_user

router = APIRouter(prefix="/api/kb", tags=["kb-papers"])


@router.post("/papers/import", response_model=KbPaperImportResult, status_code=201)
def import_paper(
    body: KbPaperImport,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Paste an arXiv ID (or URL) → fetch metadata → create a document.

    Offline lookups degrade gracefully: the document is still created with the
    arXiv ID in metadata (phrase 48 — never 500).
    """
    arxiv_id = arxiv.extract_arxiv_id(body.arxiv_id)
    if arxiv_id is None:
        raise HTTPException(400, "Could not detect an arXiv ID")

    source = None
    if body.source_id is not None:
        source = KbService.get_source(db, current_user.id, body.source_id)
        if source is None:
            raise HTTPException(404, "Source not found")

    meta = arxiv.fetch_arxiv_metadata(arxiv_id)
    title = (meta or {}).get("title") or f"arXiv:{arxiv_id}"
    doc = KbDocument(
        user_id=current_user.id,
        source_id=source.id if source else None,
        path_rel=f"papers/{arxiv_id}.md" if source else None,
        title=title,
        doc_type="md",
        status="new",
        metadata_json=KbService.json_dumps(meta or {"arxiv_id": arxiv_id}),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    if meta:
        # Materialize title/authors/abstract as content so chunking works.
        authors = ", ".join(meta.get("authors") or [])
        abstract = (meta.get("abstract") or "").strip()
        text = f"# {title}\n\n**Authors:** {authors}\n\n{abstract}".strip()
        doc.extracted_text = text
        doc.char_count = len(text)
        _parse_markdown_meta(db, doc, text)
        re_chunk(db, doc)
        doc.status = "unchanged"
        doc.indexed_at = utcnow()
        db.add(doc)
        db.commit()

    db.refresh(doc)
    resp_doc = KbDocumentResponse.model_validate(doc)
    resp_doc.chunk_count = (
        db.query(func.count(KbChunk.id))
        .filter(KbChunk.document_id == doc.id, KbChunk.user_id == current_user.id)
        .scalar()
        or 0
    )
    return KbPaperImportResult(
        document=resp_doc,
        metadata_fetched=bool(meta),
    )
