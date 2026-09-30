import json
from pathlib import Path

from backend.scheduler import build_study_plan


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(filename: str) -> dict:
    with open(FIXTURE_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def test_scheduler_avoids_busy_intervals_and_fills_target():
    payload = load_fixture("scheduler_success.json")

    result = build_study_plan(**payload)

    assert result["scheduled_minutes"] == 180
    assert result["remaining_minutes"] == 0
    assert result["reason"] == "scheduled_in_available_windows"
    assert len(result["suggested_sessions"]) == 3

    # 10:00-11:00 is occupied, so it must not be scheduled.
    scheduled_starts = {
        session["starts_at"]
        for session in result["suggested_sessions"]
    }
    assert "2026-10-01T10:00:00" not in scheduled_starts


def test_scheduler_reports_remaining_minutes_when_time_is_insufficient():
    payload = load_fixture("scheduler_insufficient.json")

    result = build_study_plan(**payload)

    assert result["scheduled_minutes"] == 60
    assert result["remaining_minutes"] == 120
    assert result["reason"] == "insufficient_available_time_before_exam"


def test_adjacent_intervals_are_not_conflicts():
    payload = {
        "plan_id": "plan-003",
        "start_date": "2026-10-01",
        "exam_date": "2026-10-02",
        "target_minutes": 60,
        "session_minutes": 60,
        "allowed_windows": [
            {
                "date": "2026-10-01",
                "start_time": "10:00",
                "end_time": "11:00"
            }
        ],
        "busy_intervals": [
            {
                "source_type": "class",
                "source_id": "class-002",
                "title": "前一堂課",
                "starts_at": "2026-10-01T09:00:00",
                "ends_at": "2026-10-01T10:00:00"
            }
        ],
    }

    result = build_study_plan(**payload)

    assert result["scheduled_minutes"] == 60
    assert result["remaining_minutes"] == 0
    assert result["suggested_sessions"][0]["starts_at"] == "2026-10-01T10:00:00"


def test_scheduler_never_schedules_on_exam_date():
    payload = {
        "plan_id": "plan-004",
        "start_date": "2026-10-01",
        "exam_date": "2026-10-02",
        "target_minutes": 120,
        "session_minutes": 60,
        "allowed_windows": [
            {
                "date": "2026-10-01",
                "start_time": "09:00",
                "end_time": "10:00"
            },
            {
                "date": "2026-10-02",
                "start_time": "09:00",
                "end_time": "12:00"
            }
        ],
        "busy_intervals": [],
    }

    result = build_study_plan(**payload)

    assert result["scheduled_minutes"] == 60
    assert result["remaining_minutes"] == 60
    assert all(
        not session["starts_at"].startswith("2026-10-02")
        for session in result["suggested_sessions"]
    )
