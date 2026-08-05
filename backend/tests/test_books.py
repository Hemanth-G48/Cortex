"""Tests for the books reading tracker endpoints."""
from __future__ import annotations

import pytest
from fastapi import status
from sqlalchemy.orm import Session

from app.models.book import Book
from app.services.security import create_bearer_token


def _get_token(client):
    resp = client.post("/api/auth/login", json={})
    assert resp.status_code == 200
    return resp.json()["token"]


def _signup(client, username: str, email: str, password: str = "pass123"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": username, "username": username, "email": email, "password": password},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


class TestBookCRUD:
    def test_create_and_list(self, client, db_session: Session):
        token = _get_token(client)
        resp = client.post(
            "/api/books",
            json={"title": "Dune", "author": "Frank Herbert", "category": "reading"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        book = resp.json()
        assert book["title"] == "Dune"
        assert book["author"] == "Frank Herbert"
        assert book["category"] == "reading"

        resp2 = client.get(
            "/api/books",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Dune"

    def test_update(self, client, db_session: Session):
        token = _get_token(client)
        resp = client.post(
            "/api/books",
            json={"title": "Dune", "author": "Frank Herbert", "category": "want"},
            headers={"Authorization": f"Bearer {token}"},
        )
        book_id = resp.json()["id"]

        resp2 = client.put(
            f"/api/books/{book_id}",
            json={"category": "finished"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["category"] == "finished"

    def test_delete(self, client, db_session: Session):
        token = _get_token(client)
        resp = client.post(
            "/api/books",
            json={"title": "Dune", "author": "Frank Herbert", "category": "want"},
            headers={"Authorization": f"Bearer {token}"},
        )
        book_id = resp.json()["id"]

        resp2 = client.delete(
            f"/api/books/{book_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["ok"] is True

        resp3 = client.get(
            "/api/books",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp3.json()["total"] == 0


class TestOwnership:
    def test_second_user_cannot_read_first_users_book(self, client, db_session: Session):
        token1 = _get_token(client)
        resp = client.post(
            "/api/books",
            json={"title": "Dune", "author": "Frank Herbert", "category": "reading"},
            headers={"Authorization": f"Bearer {token1}"},
        )
        book_id = resp.json()["id"]

        token2 = _signup(client, "otheruser", "other@example.com")
        resp2 = client.get(
            "/api/books",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["total"] == 0
        assert book_id not in [b["id"] for b in data["items"]]

    def test_second_user_cannot_update_first_users_book(self, client, db_session: Session):
        token1 = _get_token(client)
        resp = client.post(
            "/api/books",
            json={"title": "Dune", "author": "Frank Herbert", "category": "reading"},
            headers={"Authorization": f"Bearer {token1}"},
        )
        book_id = resp.json()["id"]

        token2 = _signup(client, "otheruser2", "other2@example.com")
        resp2 = client.put(
            f"/api/books/{book_id}",
            json={"category": "finished"},
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert resp2.status_code == 404

    def test_second_user_cannot_delete_first_users_book(self, client, db_session: Session):
        token1 = _get_token(client)
        resp = client.post(
            "/api/books",
            json={"title": "Dune", "author": "Frank Herbert", "category": "reading"},
            headers={"Authorization": f"Bearer {token1}"},
        )
        book_id = resp.json()["id"]

        token2 = _signup(client, "otheruser3", "other3@example.com")
        resp2 = client.delete(
            f"/api/books/{book_id}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert resp2.status_code == 404


class TestCategoryFilterAndPagination:
    def test_category_filter(self, client, db_session: Session):
        token = _get_token(client)
        client.post(
            "/api/books",
            json={"title": "Book A", "category": "finished"},
            headers={"Authorization": f"Bearer {token}"},
        )
        client.post(
            "/api/books",
            json={"title": "Book B", "category": "reading"},
            headers={"Authorization": f"Bearer {token}"},
        )
        client.post(
            "/api/books",
            json={"title": "Book C", "category": "finished"},
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = client.get(
            "/api/books?category=finished",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert all(b["category"] == "finished" for b in data["items"])

    def test_pagination_page_size_one(self, client, db_session: Session):
        token = _get_token(client)
        client.post(
            "/api/books",
            json={"title": "Book A", "category": "want"},
            headers={"Authorization": f"Bearer {token}"},
        )
        client.post(
            "/api/books",
            json={"title": "Book B", "category": "want"},
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = client.get(
            "/api/books?page_size=1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 1
        assert data["page"] == 1
        assert data["page_size"] == 1


class TestInsights:
    def test_insights_math(self, client, db_session: Session):
        token = _get_token(client)
        client.post(
            "/api/books",
            json={"title": "Finished Book 1", "author": "Author A", "category": "finished"},
            headers={"Authorization": f"Bearer {token}"},
        )
        client.post(
            "/api/books",
            json={"title": "Finished Book 2", "author": "Author A", "category": "finished"},
            headers={"Authorization": f"Bearer {token}"},
        )
        client.post(
            "/api/books",
            json={"title": "Reading Book", "author": "Author B", "category": "reading"},
            headers={"Authorization": f"Bearer {token}"},
        )
        client.post(
            "/api/books",
            json={"title": "Want Book", "author": "Author B", "category": "want"},
            headers={"Authorization": f"Bearer {token}"},
        )

        resp = client.get(
            "/api/books/insights",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 4
        assert data["finished"] == 2
        assert data["reading"] == 1
        assert data["want"] == 1
        assert data["completion_pct"] == 50.0
        assert data["per_author"] == {"Author A": 2, "Author B": 2}


class TestUpload:
    def test_upload_pdf_success(self, client, db_session: Session):
        token = _get_token(client)
        resp = client.post(
            "/api/books/upload",
            files={"file": ("a.pdf", b"%PDF-1.4 test", "application/pdf")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "url" in data
        assert data["filename"] == "a.pdf"

    def test_upload_rejects_non_pdf(self, client, db_session: Session):
        token = _get_token(client)
        resp = client.post(
            "/api/books/upload",
            files={"file": ("a.exe", b"MZ executable", "application/x-msdownload")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
