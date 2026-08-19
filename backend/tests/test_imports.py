"""Tests that all new routers/models/schemas/services import cleanly."""
from __future__ import annotations


def test_import_auth_router():
    # The auth router is a pytest-only shim now (single-user app).
    from app.routers import auth_test
    assert auth_test.router is not None


def test_import_user_schemas():
    from app.schemas.user import UserResponse, UserSignup, UserLogin, EnrollmentUpdate
    assert UserResponse is not None
    assert EnrollmentUpdate is not None


def test_import_user_model():
    from app.models import User
    assert User is not None


def test_import_institution_model():
    from app.models import Institution
    assert Institution is not None


def test_import_curriculum_course_model():
    from app.models import CurriculumCourse
    assert CurriculumCourse is not None


def test_import_materials_seed():
    from app.seed.materials_seed import parts_demo_materials
    assert callable(parts_demo_materials)


def test_import_ai_client():
    from app.services.ai_client import generate, generate_json, extract_json, ai_available
    assert callable(generate)
    assert callable(generate_json)
    assert callable(extract_json)
    assert callable(ai_available)


def test_import_ingestion():
    from app.services.ingestion import text_for_material, extract_text_for_units
    assert callable(text_for_material)
    assert callable(extract_text_for_units)


def test_import_summaries_service():
    from app.services.summaries import generate_summary, list_summaries, delete_summary
    assert callable(generate_summary)
    assert callable(list_summaries)
    assert callable(delete_summary)


def test_import_quizzes_service():
    from app.services.quizzes import generate_quiz, score_attempt
    assert callable(generate_quiz)
    assert callable(score_attempt)


def test_import_quiz_stats_service():
    from app.services.quiz_stats import reviewer_summary
    assert callable(reviewer_summary)