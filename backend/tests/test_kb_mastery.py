"""Audit defects #40/#71/#76/#82/#96 — ``GET /api/kb/mastery``.

The mastery read model must report scores derived from real ``LearningEvent``
practice logs (not configured numbers), scoped either to one curriculum subject
or to the whole vault, together with a daily trend for sparklines.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models import CurriculumSubject, LearningEvent, Topic, User

AUTH = "Authorization"


def _signup(client, uname="mastery-user", email="mastery@test.com"):
    resp = client.post(
        "/api/auth/signup",
        json={"name": "Mastery", "username": uname, "email": email,
              "password": "pass123", "role": "student"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


def _uid(db, email="mastery@test.com"):
    user = db.query(User).filter(User.email == email).first()
    assert user is not None
    return user.id


def _subject(db, name="Operating Systems"):
    subject = CurriculumSubject(
        program_id=db.query(CurriculumSubject).first().program_id,
        name=name,
        code=name[:4].upper(),
        semester=1,
    )
    db.add(subject)
    db.commit()
    return subject


def _topic(db, uid, subject_id, name="Paging"):
    topic = Topic(
        user_id=uid,
        subject_id=subject_id,
        name=name,
        normalized_name=name.lower(),
        status="confirmed",
    )
    db.add(topic)
    db.commit()
    return topic


def _event(db, uid, topic_id, kind, value, days_ago=1):
    db.add(LearningEvent(
        user_id=uid,
        topic_id=topic_id,
        event_type=kind,
        value=value,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_ago),
    ))
    db.commit()


class TestMasteryEndpoint:
    def test_empty_vault_returns_zeroed_payload(self, client, db_session):
        token = _signup(client)
        resp = client.get("/api/kb/mastery", headers={AUTH: f"Bearer {token}"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["topics_total"] == 0
        assert body["score_pct"] == 0.0
        assert body["classification"] == "unknown"
        assert body["trend"] == []

    def test_scores_come_from_practice_events(self, client, db_session):
        token = _signup(client)
        uid = _uid(db_session)
        subject = _subject(db_session)
        topic = _topic(db_session, uid, subject.id)
        # Two strong quiz results → a real, non-zero mastery score.
        _event(db_session, uid, topic.id, "quiz", 0.95)
        _event(db_session, uid, topic.id, "quiz", 1.0, days_ago=0)

        body = client.get("/api/kb/mastery", headers={AUTH: f"Bearer {token}"}).json()
        assert body["topics_total"] == 1
        assert body["evidence_events"] == 2
        assert body["events"] == {"quiz": 2}
        assert body["score_pct"] > 50
        assert body["topics"][0]["score_pct"] > 50

    def test_subject_filter_scopes_the_aggregate(self, client, db_session):
        token = _signup(client)
        uid = _uid(db_session)
        os_subject = _subject(db_session, "Operating Systems")
        db_subject = _subject(db_session, "Databases")
        os_topic = _topic(db_session, uid, os_subject.id, "Paging")
        db_topic = _topic(db_session, uid, db_subject.id, "Indexes")
        _event(db_session, uid, os_topic.id, "quiz", 1.0)
        _event(db_session, uid, db_topic.id, "quiz", 0.1)

        scoped = client.get(
            "/api/kb/mastery", params={"subject": os_subject.id},
            headers={AUTH: f"Bearer {token}"},
        ).json()
        assert scoped["topics_total"] == 1
        assert scoped["subject_id"] == os_subject.id
        assert scoped["subject_name"] == "Operating Systems"

        whole = client.get("/api/kb/mastery", headers={AUTH: f"Bearer {token}"}).json()
        assert whole["topics_total"] == 2

    def test_subject_name_resolves_unknown_names_to_empty(self, client, db_session):
        token = _signup(client)
        body = client.get(
            "/api/kb/mastery", params={"subject_name": "Nonexistent Subject"},
            headers={AUTH: f"Bearer {token}"},
        ).json()
        assert body["subject_id"] is None
        assert body["topics_total"] == 0
        assert body["classification"] == "unknown"

    def test_trend_has_one_point_per_active_day(self, client, db_session):
        token = _signup(client)
        uid = _uid(db_session)
        subject = _subject(db_session)
        topic = _topic(db_session, uid, subject.id)
        _event(db_session, uid, topic.id, "quiz", 0.2, days_ago=3)
        _event(db_session, uid, topic.id, "quiz", 0.9, days_ago=0)

        body = client.get(
            "/api/kb/mastery", params={"days": 30}, headers={AUTH: f"Bearer {token}"},
        ).json()
        trend = body["trend"]
        assert len(trend) == 2
        # Oldest → newest, and the later score must be the higher one.
        assert trend[0]["date"] < trend[1]["date"]
        assert trend[0]["score_pct"] < trend[1]["score_pct"]

    def test_rejected_topics_are_excluded(self, client, db_session):
        token = _signup(client)
        uid = _uid(db_session)
        subject = _subject(db_session)
        kept = _topic(db_session, uid, subject.id, "Kept")
        rejected = Topic(
            user_id=uid, subject_id=subject.id, name="Rejected",
            normalized_name="rejected", status="rejected",
        )
        db_session.add(rejected)
        db_session.commit()
        _event(db_session, uid, kept.id, "quiz", 1.0)
        _event(db_session, uid, rejected.id, "quiz", 0.0)

        body = client.get(
            "/api/kb/mastery", params={"subject": subject.id},
            headers={AUTH: f"Bearer {token}"},
        ).json()
        assert body["topics_total"] == 1
        assert body["topics"][0]["name"] == "Kept"
