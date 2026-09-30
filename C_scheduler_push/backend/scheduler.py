from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Iterable

DEFAULT_TIMEZONE = "Asia/Taipei"


def _parse_date(value: str | date) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value))


def _parse_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _parse_time(value: str | time) -> time:
    if isinstance(value, time):
        return value
    return time.fromisoformat(str(value))


def _overlaps(
    start: datetime,
    end: datetime,
    busy_start: datetime,
    busy_end: datetime,
) -> bool:
    """
    Half-open interval overlap check: [start, end).

    10:00 end and 10:00 start do NOT conflict.
    """
    return start < busy_end and end > busy_start


def _window_applies(window: dict[str, Any], current_date: date) -> bool:
    """
    Support either:
    - explicit date: {"date": "2026-10-01", ...}
    - weekday: {"weekday": 3, ...}  # Monday=1 ... Sunday=7
    """
    if window.get("date") is not None:
        return _parse_date(window["date"]) == current_date

    if window.get("weekday") is not None:
        return int(window["weekday"]) == current_date.isoweekday()

    return True


def _build_daily_windows(
    current_date: date,
    allowed_windows: Iterable[dict[str, Any]],
) -> list[tuple[datetime, datetime]]:
    result: list[tuple[datetime, datetime]] = []

    for window in allowed_windows:
        if not _window_applies(window, current_date):
            continue

        start_t = _parse_time(window["start_time"])
        end_t = _parse_time(window["end_time"])

        start_dt = datetime.combine(current_date, start_t)
        end_dt = datetime.combine(current_date, end_t)

        if end_dt <= start_dt:
            raise ValueError("allowed window end_time must be later than start_time")

        result.append((start_dt, end_dt))

    result.sort(key=lambda x: x[0])
    return result


def build_study_plan(
    *,
    plan_id: str,
    start_date: str | date,
    exam_date: str | date,
    target_minutes: int,
    session_minutes: int,
    allowed_windows: list[dict[str, Any]],
    busy_intervals: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Build a deterministic study schedule.

    Contract:
      input:
        plan_id
        start_date
        exam_date
        target_minutes
        session_minutes
        allowed_windows
        busy_intervals

      output:
        suggested_sessions
        scheduled_minutes
        remaining_minutes
        reason

    Rule:
      exam_date is treated as a date-only deadline, so sessions are scheduled
      from start_date through the day BEFORE exam_date.
    """
    if target_minutes <= 0:
        raise ValueError("target_minutes must be greater than 0")

    if session_minutes <= 0:
        raise ValueError("session_minutes must be greater than 0")

    start = _parse_date(start_date)
    exam = _parse_date(exam_date)

    if start >= exam:
        raise ValueError("start_date must be earlier than exam_date")

    parsed_busy: list[tuple[datetime, datetime, dict[str, Any]]] = []

    for busy in busy_intervals:
        busy_start = _parse_datetime(busy["starts_at"])
        busy_end = _parse_datetime(busy["ends_at"])

        if busy_end <= busy_start:
            raise ValueError("busy interval ends_at must be later than starts_at")

        parsed_busy.append((busy_start, busy_end, busy))

    remaining = int(target_minutes)
    sessions: list[dict[str, Any]] = []

    current_date = start
    last_schedulable_date = exam - timedelta(days=1)

    while current_date <= last_schedulable_date and remaining > 0:
        daily_windows = _build_daily_windows(current_date, allowed_windows)

        for window_start, window_end in daily_windows:
            cursor = window_start

            while cursor < window_end and remaining > 0:
                duration = min(session_minutes, remaining)
                candidate_end = cursor + timedelta(minutes=duration)

                if candidate_end > window_end:
                    break

                conflicts = [
                    busy
                    for busy_start, busy_end, busy in parsed_busy
                    if _overlaps(cursor, candidate_end, busy_start, busy_end)
                ]

                if not conflicts:
                    sessions.append(
                        {
                            "plan_id": plan_id,
                            "starts_at": cursor.isoformat(),
                            "ends_at": candidate_end.isoformat(),
                            "minutes": duration,
                        }
                    )
                    remaining -= duration

                # Move by one configured session block.
                cursor += timedelta(minutes=session_minutes)

        current_date += timedelta(days=1)

    scheduled = target_minutes - remaining

    if remaining == 0:
        reason = "scheduled_in_available_windows"
    elif scheduled == 0:
        reason = "no_available_time_before_exam"
    else:
        reason = "insufficient_available_time_before_exam"

    return {
        "plan_id": plan_id,
        "suggested_sessions": sessions,
        "scheduled_minutes": scheduled,
        "remaining_minutes": remaining,
        "reason": reason,
    }
