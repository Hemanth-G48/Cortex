"""Grade calculation math — exact port of Shiori-v1.

Sourced from ``Shiori-v1/client/src/stores/index.js`` (``LETTER_GRADE``,
``pctToGPA``, ``calculateCourseGrade``) and ``pages/Grades.jsx``
(``neededOnFinal`` predictor + credit-weighted cumulative GPA).
"""
from __future__ import annotations

from typing import Iterable


def letter_grade(pct: float) -> str:
    """Percentage → letter grade (Shiori's LETTER_GRADE table)."""
    if pct >= 93:
        return "A"
    if pct >= 90:
        return "A-"
    if pct >= 87:
        return "B+"
    if pct >= 83:
        return "B"
    if pct >= 80:
        return "B-"
    if pct >= 77:
        return "C+"
    if pct >= 73:
        return "C"
    if pct >= 70:
        return "C-"
    if pct >= 67:
        return "D+"
    if pct >= 63:
        return "D"
    if pct >= 60:
        return "D-"
    return "F"


def pct_to_gpa(pct: float) -> float:
    """Percentage → 4.0-scale GPA (Shiori's pctToGPA table)."""
    if pct >= 93:
        return 4.0
    if pct >= 90:
        return 3.7
    if pct >= 87:
        return 3.3
    if pct >= 83:
        return 3.0
    if pct >= 80:
        return 2.7
    if pct >= 77:
        return 2.3
    if pct >= 73:
        return 2.0
    if pct >= 70:
        return 1.7
    if pct >= 67:
        return 1.3
    if pct >= 63:
        return 1.0
    if pct >= 60:
        return 0.7
    return 0.0


def calculate_course_grade(
    grades: Iterable[dict],
    weights: Iterable[dict] | None = None,
) -> dict | None:
    """Compute a course grade from grade entries + optional weighted categories.

    ``grades``: ``[{"points_earned": float, "points_possible": float,
    "category_id": int|None}]``
    ``weights``: ``[{"id": int, "weight": float}]`` (optional).

    Returns ``None`` when there are no grades / everything is zero, else
    ``{"percentage": float, "letter_grade": str, "is_weighted": bool,
    "total_earned": float|None, "total_possible": float|None}``.
    Mirrors Shiori's ``calculateCourseGrade`` exactly (weighted path with
    uncategorized remainder, unweighted path as plain totals).
    """
    entries = list(grades)
    if not entries:
        return None

    weight_list = list(weights or [])
    if weight_list:
        total_weight = sum(w.get("weight", 0) for w in weight_list)
        if total_weight == 0:
            return None

        weighted_sum = 0.0
        weighted_total = 0.0

        for cat in weight_list:
            cat_grades = [g for g in entries if g.get("category_id") == cat.get("id")]
            if not cat_grades:
                continue
            earned = sum(g.get("points_earned", 0) or 0 for g in cat_grades)
            possible = sum(g.get("points_possible", 0) or 0 for g in cat_grades)
            if possible == 0:
                continue
            cat_pct = (earned / possible) * 100
            frac = cat.get("weight", 0) / total_weight
            weighted_sum += cat_pct * frac
            weighted_total += frac

        weight_ids = {w.get("id") for w in weight_list}
        uncategorized = [g for g in entries if not g.get("category_id") or g.get("category_id") not in weight_ids]
        if uncategorized:
            earned = sum(g.get("points_earned", 0) or 0 for g in uncategorized)
            possible = sum(g.get("points_possible", 0) or 0 for g in uncategorized)
            if possible > 0:
                weighted_sum += (earned / possible) * 100 * (1 - weighted_total)
                weighted_total = 1.0

        if weighted_total == 0:
            return None
        percentage = weighted_sum / weighted_total
        return {
            "percentage": round(percentage, 1),
            "letter_grade": letter_grade(percentage),
            "is_weighted": True,
            "total_earned": None,
            "total_possible": None,
        }

    total_earned = sum(g.get("points_earned", 0) or 0 for g in entries)
    total_possible = sum(g.get("points_possible", 0) or 0 for g in entries)
    if total_possible == 0:
        return None
    percentage = (total_earned / total_possible) * 100
    return {
        "percentage": round(percentage, 1),
        "letter_grade": letter_grade(percentage),
        "is_weighted": False,
        "total_earned": round(total_earned, 1),
        "total_possible": round(total_possible, 1),
    }


def needed_on_final(current_pct: float, final_weight_pct: float, desired_pct: float) -> float:
    """What % you need on the final exam (Shiori's Grades.jsx predictor).

    ``needed = (desired - current * (1 - w)) / w`` where ``w = final_weight/100``.
    """
    w = final_weight_pct / 100.0
    if w <= 0:
        return float("inf")
    needed = (desired_pct - current_pct * (1 - w)) / w
    return round(needed, 1)


def cumulative_gpa(course_pcts: Iterable[tuple[float, int]]) -> float | None:
    """Credit-weighted cumulative GPA from ``(course_percentage, credits)`` pairs."""
    pairs = [(pct, credits) for pct, credits in course_pcts if pct is not None and credits]
    if not pairs:
        return None
    total_credits = sum(c for _, c in pairs)
    if total_credits == 0:
        return None
    gpa = sum(pct_to_gpa(pct) * credits for pct, credits in pairs) / total_credits
    return round(gpa, 2)
