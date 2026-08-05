"""Book router for the reading tracker (STUDENT-PLANAR G4, phases 23-25 & 27)."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.book import Book
from app.schemas.book import BookCreate, BookUpdate, BookResponse, BookInsights
from app.services.reading import compute_book_insights
from app.services.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api", tags=["books"])


@router.get("/books", response_model=dict)
def list_books(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    category: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    """Return current user's books, newest first, with optional category filter and pagination."""
    query = db.query(Book).filter(Book.user_id == current_user.id)
    if category is not None:
        query = query.filter(Book.category == category)
    total = query.count()
    items = query.order_by(Book.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [BookResponse.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/books", response_model=BookResponse, status_code=201)
def create_book(
    body: BookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Book:
    """Create a new book owned by the current user."""
    book = Book(
        user_id=current_user.id,
        title=body.title,
        author=body.author,
        category=body.category,
        cover_url=body.cover_url,
        file_url=body.file_url,
    )
    db.add(book)
    db.flush()
    db.refresh(book)
    return book


@router.put("/books/{book_id}", response_model=BookResponse)
def update_book(
    book_id: int,
    body: BookUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Book:
    """Update a book; 404 if missing or not owned by the caller."""
    book = db.query(Book).filter(Book.id == book_id, Book.user_id == current_user.id).first()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(book, field, value)
    db.flush()
    db.refresh(book)
    return book


@router.delete("/books/{book_id}")
def delete_book(
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a book; 404 if missing or not owned by the caller."""
    book = db.query(Book).filter(Book.id == book_id, Book.user_id == current_user.id).first()
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    db.delete(book)
    db.flush()
    return {"ok": True}


@router.post("/books/upload", status_code=201)
def upload_book_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Upload a reading file (PDF only) for the current user."""
    original = Path(file.filename or "file.pdf").name
    suffix = Path(original).suffix.lower()
    if suffix not in {".pdf"}:
        raise HTTPException(400, detail={"error": "Only PDF files are allowed"})

    data = file.file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, detail={"error": "File too large"})

    directory = Path(settings.UPLOAD_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    target = directory / stored_name
    with target.open("wb") as out:
        out.write(data)

    return {"url": f"/uploads/{stored_name}", "filename": original}


@router.get("/books/insights", response_model=BookInsights)
def book_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BookInsights:
    """Return reading insights for the current user."""
    return compute_book_insights(db, current_user.id)
