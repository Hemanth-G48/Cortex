"""Sleep analytics + bedtime/wake recommendations.

Zenith-Study-Planner G3 (Phases 17–19). Pure functions over SleepLog rows so
the logic is trivially unit-testable. All times are "HH:MM" 24h strings;
duration math crosses midnight correctly (bedtime 23:00 → wake 07:00 = 8h).
"""

from __future__ import annotations

from statistics import mean, pstdev
from typing import Iterable

from app.config import settings


# ── Helpers ─────────────────────────────────────────────────────────────── #

def _to_minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def hours_between(bedtime: str, wake_time: str) -> float:
    """Nightly sleep hours, crossing midnight when wake < bedtime."""
    bed = _to_minutes(bedtime)
    wake = _to_minutes(wake_time)
    if wake <= bed:
        wake += 24 * 60
    return round((wake - bed) / 60.0, 2)


def _subtract_minutes(hhmm: str, minutes: int) -> str:
    total = (_to_minutes(hhmm) - minutes) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


# ── Analytics (Phase 17) ────────────────────────────────────────────────── #

def analytics(logs: Iterable, target_hours: float | None = None) -> dict:
    """Aggregate sleep logs into avg hours, consistency, deviation, and count
    of nights under the target."""
    target = target_hours if target_hours is not None else settings.sleep_target_hours
    rows = list(logs)
    if not rows:
        return {
            "nights_logged": 0,
            "avg_hours": None,
            "consistency_hours": None,
            "deviation_hours": None,
            "nights_under_target": 0,
            "target_hours": round(target, 2),
        }

    hours = [hours_between(r.bedtime, r.wake_time) for r in rows]
    avg = round(mean(hours), 2)
    consistency = round(pstdev(hours), 2) if len(hours) > 1 else 0.0
    return {
        "nights_logged": len(rows),
        "avg_hours": avg,
        "consistency_hours": consistency,
        "deviation_hours": round(avg - target, 2),
        "nights_under_target": sum(1 for h in hours if h < target),
        "target_hours": round(target, 2),
    }


# ── Bedtime / wake recommendation (Phase 18) ────────────────────────────── #

def recommend_bedtime(
    wake_time: str,
    target_hours: float | None = None,
    history: Iterable | None = None,
) -> dict:
    """Recommend a bedtime for a given wake time, alerting on sleep deficit."""
    target = target_hours if target_hours is not None else settings.sleep_target_hours
    recommended = _subtract_minutes(wake_time, int(round(target * 60)))

    result = {
        "target_hours": round(target, 2),
        "wake_time": wake_time,
        "recommended_bedtime": recommended,
        "alert": None,
        "tips": [],
        "schedule_hints": [],
    }

    rows = list(history or [])
    if rows:
        avg = mean(hours_between(r.bedtime, r.wake_time) for r in rows)
        if avg < min(target, 6.0):
            result["alert"] = (
                f"Your recent average is {avg:.1f}h — below a healthy baseline. "
                "Consider protecting more rest this week."
            )
            result["schedule_hints"].append(
                "Block 30 extra minutes of wind-down time before the recommended bedtime."
            )

    result["tips"] = [
        f"Wind down by {_subtract_minutes(recommended, 30)} — screens off, lights low.",
        "Keep your wake-up time consistent even on weekends.",
        "Avoid caffeine after mid-afternoon for deeper sleep.",
    ]
    return result


# ── Sleep-aware schedule adjustment (Phase 19) ──────────────────────────── #

def schedule_hints(logs: Iterable, target_hours: float | None = None) -> list[str]:
    """Suggest protected-rest / reduced-evening-study hints from sleep deficit."""
    target = target_hours if target_hours is not None else settings.sleep_target_hours
    rows = list(logs)
    if not rows:
        return []

    avg = mean(hours_between(r.bedtime, r.wake_time) for r in rows)
    hints: list[str] = []
    if avg < target:
        deficit = round(target - avg, 1)
        hints.append(f"You're averaging {deficit}h less than your {target:g}h target.")
        if deficit >= 1.0:
            hints.append("Move heavy study blocks earlier in the day for the next few days.")
            hints.append("Protect the last hour before bed as rest — no screens, no deadlines.")
        else:
            hints.append("Shift evening study 30 minutes earlier to protect wind-down time.")
    return hints
