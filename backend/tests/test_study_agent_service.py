from types import SimpleNamespace

import pytest

from app import create_app
from app.study_agent_api import (
    StudyAgentService,
    get_validated_study_plan,
    normalize_request,
)
from app.study_agent_contract import TOOL_NAME


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
    provider_name = "OpenAI Responses API"
    authentication = "Server-side API key"
    framework = "OpenAI Responses API"

    def __init__(self, *, mutate=None, expert_error=None):
        self.config = SimpleNamespace(model="openai-test")
        self.mutate = mutate
        self.expert_error = expert_error
        self.expert_packets = []

    def choose_tool(self, data):
        args = self.mutate(dict(data)) if self.mutate else data
        return (
            {"name": TOOL_NAME, "args": args},
            [{"role": "user", "content": [{"type": "input_text", "text": "synthetic"}]}],
            {"usage": {"input_tokens": 10}},
        )

    def review_plan(self, packet):
        self.expert_packets.append(packet)
        if self.expert_error is not None:
            raise self.expert_error
        assessment = (
            "insufficient"
            if packet["plan"]["remainingMinutes"] > 0
            else "balanced"
        )
        return (
            {
                "assessment": assessment,
                "summary": "時段已通過受限專家檢查。",
                "recommendations": [],
                "citations": ["planner-rule", "study-load-review"],
            },
            {"usage": {"input_tokens": 8, "output_tokens": 6}},
        )

    def summarize(self, history, plan, expert_review=None):
        assert history
        assert expert_review is not None
        return (
            {
                "summary": "已依規則安排三個複習時段，並整合專家檢查。",
                "warnings": [],
                "citations": [
                    "planner-rule",
                    "weekly-classes-fixture",
                    "planner-backend-sqlite",
                ],
                "refused": False,
            },
            {"usage": {"output_tokens": 20}},
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
    assert result["workflow"]["runId"].startswith("week08-")
    assert [stage["id"] for stage in result["workflow"]["stages"]] == [
        "validate-request",
        "model-tool-call",
        "validate-tool-args",
        "execute-tool",
        "delegate-study-load-expert",
        "integrate-expert-review",
        "return-tool-result",
    ]
    assert result["agent"]["framework"] == "OpenAI Responses API"
    assert result["agent"]["tool"] == TOOL_NAME
    assert result["comparison"]["agentCount"] == 2
    assert result["multiAgent"]["pattern"] == "bounded-specialist"
    assert result["multiAgent"]["roles"][1]["tools"] == []


def test_expert_receives_minimum_context_without_private_event_details():
    provider = FakeProvider()
    service = StudyAgentService(provider_factory=lambda: provider)

    result = service.run(request_payload())

    packet = provider.expert_packets[0]
    serialized = repr(packet)
    assert "personalEvents" not in packet
    assert "社團會議" not in serialized
    assert "活動中心 3 樓" not in serialized
    assert packet["task"]["courseName"] == "資料結構"
    assert packet["plan"]["scheduledMinutes"] == 360
    assert result["multiAgent"]["sharedContext"]["personalEventDetailsShared"] is False


def test_invalid_expert_output_stops_before_final_coordinator_summary():
    class InvalidExpertProvider(FakeProvider):
        def review_plan(self, packet):
            self.expert_packets.append(packet)
            return (
                {
                    "assessment": "insufficient",
                    "summary": "錯誤地把已排滿計畫判成不足。",
                    "recommendations": [],
                    "citations": ["planner-rule"],
                },
                {"usage": {}},
            )

        def summarize(self, history, plan, expert_review=None):
            raise AssertionError("Coordinator summary must not run after invalid expert output")

    service = StudyAgentService(provider_factory=InvalidExpertProvider)
    with pytest.raises(Exception) as error:
        service.run(request_payload())

    assert getattr(error.value, "code", None) == "EXPERT_OUTPUT_INVALID"
    assert error.value.workflow["stopReason"] == "EXPERT_OUTPUT_INVALID"


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
    body = response.get_json()
    assert body["agent"]["model"] == "openai-test"
    assert body["multiAgent"]["pattern"] == "bounded-specialist"
    assert body["workflow"]["runId"].startswith("week08-")

    invalid = client.post(
        "/api/v1/study-agent/run",
        json=request_payload(examDate="2026-09-17"),
    )
    assert invalid.status_code == 422
    assert invalid.get_json()["code"] == "INVALID_REQUEST"


def test_health_does_not_claim_live_provider(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "health-test-secret")
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "health.sqlite3"),
        }
    )
    response = app.test_client().get("/api/v1/study-agent/health")
    assert response.status_code == 200
    assert response.get_json()["authentication"] == "Server-side API key"
    assert response.get_json()["liveChecked"] is False
    assert "health-test-secret" not in response.get_data(as_text=True)
