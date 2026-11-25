from datetime import date, timedelta

from app import create_app
from app.db import init_db


FIRST = date(2090, 6, 1)
EVENTS = "/api/v1/personal-events"
ADJUSTMENT = EVENTS + "/study-adjustment"
SCHEDULE = "/api/v1/study-schedule"


def interval(start, end, title):
    return {
        "title": title,
        "starts_at": f"{FIRST}T{start}:00+08:00",
        "ends_at": f"{FIRST}T{end}:00+08:00",
    }


def setup_schedule(tmp_path, window_end="18:00"):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "schedule.sqlite3")})
    with app.app_context():
        init_db()
    client = app.test_client()
    response = client.put(SCHEDULE, json={
        "plan": {
            "course_id": "course-demo-001",
            "start_date": FIRST.isoformat(),
            "exam_date": (FIRST + timedelta(days=2)).isoformat(),
            "target_minutes": 120,
            "session_minutes": 60,
            "allowed_windows": [
                {"weekday": FIRST.isoweekday(), "start_time": "13:00", "end_time": window_end}
            ],
        },
        "sessions": [
            interval("13:00", "14:00", "受影響的複習"),
            interval("14:00", "15:00", "另一段複習"),
        ],
    })
    assert response.status_code == 200, response.json
    return client, response.json["data"]


def test_preview_is_read_only_and_confirmation_moves_only_conflicting_sessions(tmp_path):
    client, original = setup_schedule(tmp_path)
    event = interval("13:00", "14:00", "私人行程")
    assert client.post(EVENTS, json=event).status_code == 409
    preview = client.post(ADJUSTMENT + "/preview", json={"event": event})
    assert preview.status_code == 200, preview.json
    proposal = preview.json["data"]
    assert [move["session_id"] for move in proposal["moves"]] == [original["sessions"][0]["session_id"]]
    assert proposal["moves"][0]["to_start"].endswith("T15:00:00+08:00")
    assert client.get(EVENTS).json["data"] == []
    assert client.get(SCHEDULE).json["data"] == original

    payload = {"event": event, "preview_token": proposal["preview_token"]}
    confirmed = client.post(ADJUSTMENT + "/commit", json=payload)
    assert confirmed.status_code == 200, confirmed.json
    schedule = confirmed.json["data"]["study_schedule"]
    assert schedule["sessions"][0] == original["sessions"][1]
    assert schedule["sessions"][1]["session_id"] == original["sessions"][0]["session_id"]
    assert schedule["scheduled_minutes"] == original["scheduled_minutes"]
    assert schedule["plan_version"] == original["plan_version"] + 1
    assert client.get(SCHEDULE).json["data"] == schedule
    assert client.post(ADJUSTMENT + "/commit", json=payload).status_code == 409
    assert len(client.get(EVENTS).json["data"]) == 1


def test_a_new_event_invalidates_the_preview_without_partial_writes(tmp_path):
    client, original = setup_schedule(tmp_path)
    event = interval("13:00", "14:00", "準備新增的行程")
    preview = client.post(ADJUSTMENT + "/preview", json={"event": event}).json["data"]
    assert client.post(EVENTS, json=interval("15:00", "16:00", "後來加入的行程")).status_code == 201
    response = client.post(
        ADJUSTMENT + "/commit",
        json={"event": event, "preview_token": preview["preview_token"]},
    )
    assert response.status_code == 409
    assert response.json["error"]["code"] == "STUDY_ADJUSTMENT_STALE"
    assert client.get(SCHEDULE).json["data"] == original
    assert len(client.get(EVENTS).json["data"]) == 1


def test_no_slot_leaves_plan_and_personal_events_unchanged(tmp_path):
    client, original = setup_schedule(tmp_path, window_end="15:00")
    response = client.post(ADJUSTMENT + "/preview", json={
        "event": interval("13:30", "14:00", "私人行程"),
    })
    assert response.status_code == 409
    assert response.json["error"]["code"] == "STUDY_ADJUSTMENT_NO_SLOT"
    assert client.get(EVENTS).json["data"] == []
    assert client.get(SCHEDULE).json["data"] == original


def test_edit_keeps_event_id_and_checks_other_personal_events(tmp_path):
    client, _ = setup_schedule(tmp_path)
    event = client.post(EVENTS, json=interval("12:00", "13:00", "改期的行程")).json["data"]
    client.post(EVENTS, json=interval("11:00", "12:00", "其他行程"))
    event_id = event["event_id"]
    request = {"event_id": event_id, "event": interval("11:30", "14:00", event["title"])}
    blocked = client.post(ADJUSTMENT + "/preview", json=request)
    assert blocked.status_code == 409
    assert blocked.json["error"]["code"] == "SCHEDULE_CONFLICT"

    request["event"] = interval("12:30", "14:00", event["title"])
    preview = client.post(ADJUSTMENT + "/preview", json=request)
    assert preview.status_code == 200, preview.json
    response = client.post(ADJUSTMENT + "/commit", json={
        **request,
        "preview_token": preview.json["data"]["preview_token"],
    })
    assert response.status_code == 200, response.json
    assert response.json["data"]["event"]["event_id"] == event_id
    assert len(client.get(EVENTS).json["data"]) == 2
