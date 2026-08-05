"""Reading tracker service: book insights computation."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.book import Book
from app.schemas.book import BookInsights


def compute_book_insights(db: Session, user_id: int) -> BookInsights:
    """Compute reading insights for a user from the books table."""
    books = db.query(Book).filter(Book.user_id == user_id).all()
    total = len(books)
    finished = sum(1 for b in books if b.category == "finished")
    reading = sum(1 for b in books if b.category == "reading")
    want = sum(1 for b in books if b.category == "want")
    completion_pct = round(finished / total * 100, 1) if total > 0 else 0.0

    per_author: dict[str, int] = {}
    for b in books:
        author = b.author or "Unknown"
        per_author[author] = per_author.get(author, 0) + 1

    # Trend: books added in the current calendar month.
    now = datetime.now()
    added_this_month = sum(
        1
        for b in books
        if b.created_at is not None
        and b.created_at.year == now.year
        and b.created_at.month == now.month
    )

    return BookInsights(
        total=total,
        finished=finished,
        reading=reading,
        want=want,
        completion_pct=completion_pct,
        per_author=per_author,
        added_this_month=added_this_month,
    )
