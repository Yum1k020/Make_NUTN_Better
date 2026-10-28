import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import backend.week02_api as api_module
from backend.scheduler import build_study_plan

FIXTURE = Path(__file__).parent / "fixtures" / "week02_success.json"
client = TestClient(api_module.app)


def load_case():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_week02_200_success():
    response = client.post("/api/study-plan", json=load_case())
    assert response.status_code == 200
    data = response.json()
    assert data["scheduled_minutes"] == 180
    assert data["remaining_minutes"] == 0
    assert all(
        session["starts_at"] != "2026-10-08T10:00:00"
        for session in data["suggested_sessions"]
    )


def test_week02_422_missing_required_field():
    payload = load_case()
    payload.pop("target_minutes")
    assert client.post("/api/study-plan", json=payload).status_code == 422


def test_week02_502_upstream_boundary(monkeypatch):
    def broken_scheduler(**kwargs):
        raise RuntimeError("simulated upstream generation failure")

    monkeypatch.setattr(api_module, "build_study_plan", broken_scheduler)
    response = client.post("/api/study-plan", json=load_case())
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "UPSTREAM_GENERATION_UNAVAILABLE"


@pytest.mark.xfail(
    strict=True,
    reason="v1 known failure: a tail shorter than session_minutes is not used",
)
def test_week02_known_failure_partial_tail():
    result = build_study_plan(
        plan_id="known-failure",
        start_date="2026-10-08",
        exam_date="2026-10-09",
        target_minutes=120,
        session_minutes=60,
        allowed_windows=[
            {"date": "2026-10-08", "start_time": "09:00", "end_time": "10:30"}
        ],
        busy_intervals=[],
    )
    assert result["scheduled_minutes"] == 90
    assert result["remaining_minutes"] == 30
