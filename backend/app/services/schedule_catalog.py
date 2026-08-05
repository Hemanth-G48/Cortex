"""Catalog constants and validation helpers for the daily schedule."""

from typing import Optional

from app.models.daily_schedule_item import DailyScheduleItem

CATEGORIES: list[tuple[str, str]] = [
    ("School", "school"),
    ("Study Time", "study"),
    ("Break", "break"),
]

ENERGIES: list[tuple[str, str]] = [
    ("High", "high"),
    ("Medium", "medium"),
    ("Low", "low"),
]

CATEGORY_CLASS: dict[str, str] = {name: f"cat-{slug}" for name, slug in CATEGORIES}
ENERGY_CLASS: dict[str, str] = {name: f"energy-{slug}" for name, slug in ENERGIES}


def parse_time_range(time_range: str) -> Optional[tuple[int, int]]:
    """Parse a time_range string like '08:00-09:30' into (start_min, end_min).

    Returns None for malformed strings or when end <= start.
    """
    try:
        start_str, end_str = time_range.split("-")
        start_h, start_m = start_str.split(":")
        end_h, end_m = end_str.split(":")
        start_min = int(start_h) * 60 + int(start_m)
        end_min = int(end_h) * 60 + int(end_m)
    except Exception:
        return None
    if end_min <= start_min:
        return None
    return (start_min, end_min)


def blocks_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """Return True if two half-open intervals [a_start, a_end) and [b_start, b_end) overlap."""
    return a_start < b_end and b_start < a_end


def validate_blocks(
    existing: list[DailyScheduleItem], new_start: int, new_end: int
) -> bool:
    """Return True if the new block overlaps ANY existing block on the same date."""
    for item in existing:
        parsed = parse_time_range(item.time_range)
        if parsed is None:
            continue
        existing_start, existing_end = parsed
        if blocks_overlap(new_start, new_end, existing_start, existing_end):
            return True
    return False
