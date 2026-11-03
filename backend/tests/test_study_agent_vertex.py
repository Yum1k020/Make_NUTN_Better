from types import SimpleNamespace

import pytest

from app import create_app
from app.study_agent_api import (
    StudyAgentService,
    get_validated_study_plan,
    normalize_request,
)
from app.study_agent_vertex import TOOL_NAME


def request_payload(**overrides):
    payload = {
        "startDate": "2026-09-17",
        "examDate": "2026-09-24",
        "hours": 6,
        "sessionHours": 2,
        "allowedPeriods": ["afternoon", "evening"],
        "courseName": "資料結構",
        "personalEvents": [
            {
                "id": "event-club",
                "title": "社團會議",
                "date": "2026-09-17",
                "start": "17:00",
                "end": "18:00",
                "location": "活動中心 3 樓",
            },
            {
                "id": "event-council",
                "title": "系學會會議",
                "date": "2026-09-16",
                "start": "14:00",
                "end": "16:00",
                "location": "活動中心 3 樓",
            },
        ],
    }
    payload.update(overrides)
    return payload


class FakeProvider:
    def __init__(self, *, mutate=None):
        self.config = SimpleNamespace(model="gemini-test")
        self.mutate = mutate

    def choose_tool(self, data):
        args = self.mutate(dict(data)) if self.mutate else data
        return (
            {"name": TOOL_NAME, "args": args},
            [{"role": "user", "parts": [{"text": "synthetic"}]}],
            {"usage": {"promptTokenCount": 10}},
        )

    def summarize(self, history, plan):
        assert history
        return (
            {
                "summary": "已依規則安排三個複習時段。",
                "warnings": [],
                "citations": [
                    "planner-rule",
                    "weekly-classes-fixture",
                    "planner-backend-sqlite",
                ],
                "refused": False,
            },
            {"usage": {"candidatesTokenCount": 20}},
        )


def service_factory(provider):
    return lambda: StudyAgentService(provider_factory=lambda: provider)


def test_deterministic_tool_matches_frontend_fixture():
    result = get_validated_study_plan(request_payload())
    assert result["scheduledMinutes"] == 360
    assert result["remainingMinutes"] == 0
    assert len(result["sessions"]) == 3
    assert result["sessions"][0]["id"] == "study-2026-09-17-18:00"


def test_main_flow_records_function_call_validation_and_response():
    service = StudyAgentService(provider_factory=FakeProvider)
    result = service.run(request_payload())
    assert result["workflow"]["status"] == "completed"
    assert [stage["id"] for stage in result["workflow"]["stages"]] == [
        "validate-request",
        "model-tool-call",
        "validate-tool-args",
        "execute-tool",
        "return-tool-result",
    ]
    assert result["agent"]["framework"] == "Google Cloud Vertex AI / ADC"
    assert result["agent"]["tool"] == TOOL_NAME


def test_changed_model_arguments_stop_before_tool_execution():
    calls = []
    provider = FakeProvider(mutate=lambda data: {**data, "hours": 7})
    service = StudyAgentService(
        provider_factory=lambda: provider,
        tool=lambda data: calls.append(data),
    )
    with pytest.raises(Exception) as error:
        service.run(request_payload())
    assert getattr(error.value, "code", None) == "TOOL_ARGUMENT_MISMATCH"
    assert calls == []


def test_request_schema_rejects_unknown_fields():
    with pytest.raises(ValueError, match="未允許欄位"):
        normalize_request(request_payload(secret="no"))


def test_http_main_flow_and_invalid_boundary(tmp_path):
    provider = FakeProvider()
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "study-agent.sqlite3"),
            "STUDY_AGENT_SERVICE_FACTORY": service_factory(provider),
        }
    )
    client = app.test_client()
    response = client.post("/api/v1/study-agent/run", json=request_payload())
    assert response.status_code == 200
    assert response.get_json()["agent"]["model"] == "gemini-test"

    invalid = client.post(
        "/api/v1/study-agent/run",
        json=request_payload(examDate="2026-09-17"),
    )
    assert invalid.status_code == 422
    assert invalid.get_json()["code"] == "INVALID_REQUEST"


def test_health_does_not_claim_live_provider(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "health.sqlite3"),
        }
    )
    response = app.test_client().get("/api/v1/study-agent/health")
    assert response.status_code == 200
    assert response.get_json()["authentication"] == "Application Default Credentials"
    assert response.get_json()["liveChecked"] is False
