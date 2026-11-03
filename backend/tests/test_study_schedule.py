import pytest

from app import create_app
from app.db import init_db


@pytest.fixture
def schedule_app(tmp_path):
    path = tmp_path / "schedule.sqlite3"
    app = create_app({"TESTING": True, "DATABASE": str(path)})
    with app.app_context():
        init_db()
    return app, path


def schedule_payload(start="14:00", end="15:00"):
    return {
        "plan": {
            "course_id": "course-demo-001",
            "exam_task_id": None,
            "start_date": "2026-09-17",
            "exam_date": "2026-09-24",
            "target_minutes": 60,
            "session_minutes": 60,
            "allowed_windows": [
                {"weekday": 4, "start_time": "13:00", "end_time": "18:00"}
            ],
        },
        "sessions": [
            {
                "title": "資料結構複習",
                "starts_at": f"2026-09-17T{start}:00+08:00",
                "ends_at": f"2026-09-17T{end}:00+08:00",
            }
        ],
    }


def test_study_schedule_replaces_and_persists_as_one_transaction(schedule_app):
    app, path = schedule_app
    client = app.test_client()
    assert client.get("/api/v1/study-schedule").json == {"data": None}

    saved = client.put("/api/v1/study-schedule", json=schedule_payload())
    assert saved.status_code == 200
    assert saved.json["data"]["plan_version"] == 2
    assert len(saved.json["data"]["sessions"]) == 1

    restarted = create_app({"TESTING": True, "DATABASE": str(path)}).test_client()
    recalled = restarted.get("/api/v1/study-schedule")
    assert recalled.status_code == 200
    assert recalled.json["data"]["sessions"][0]["title"] == "資料結構複習"


def test_failed_schedule_replacement_rolls_back_previous_plan(schedule_app):
    client = schedule_app[0].test_client()
    first = client.put("/api/v1/study-schedule", json=schedule_payload())
    first_plan_id = first.json["data"]["plan_id"]
    event = client.post(
        "/api/v1/personal-events",
        json={
            "title": "後端行程",
            "starts_at": "2026-09-17T15:00:00+08:00",
            "ends_at": "2026-09-17T17:00:00+08:00",
            "location": None,
        },
    )
    assert event.status_code == 201

    failed = client.put(
        "/api/v1/study-schedule", json=schedule_payload("15:30", "16:30")
    )
    assert failed.status_code == 409
    assert failed.json["error"]["code"] == "SCHEDULE_CONFLICT"

    recalled = client.get("/api/v1/study-schedule")
    assert recalled.json["data"]["plan_id"] == first_plan_id
    assert recalled.json["data"]["sessions"][0]["starts_at"].endswith(
        "14:00:00+08:00"
    )


def test_113_frontend_catalog_is_seeded_for_planned_courses(schedule_app):
    response = schedule_app[0].test_client().post(
        "/api/v1/planned-courses",
        json={
            "target_semester_id": "semester-113-2",
            "course_id": "elective-NN1194",
            "offering_id": None,
        },
    )
    assert response.status_code == 201
    assert response.json["data"]["course_id"] == "elective-NN1194"
