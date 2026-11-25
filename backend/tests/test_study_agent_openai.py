import json

import pytest

from app import create_app
from app.study_agent_contract import TOOL_NAME
from app.study_agent_openai import (
    EXPERT_CONTEXT_BASELINE,
    EXPERT_CONTEXT_CANDIDATE,
    OpenAIConfig,
    OpenAIProviderError,
    OpenAIResponsesClient,
)


def request_payload():
    return {
        "startDate": "2026-09-17",
        "examDate": "2026-09-24",
        "hours": 2,
        "sessionHours": 1,
        "allowedPeriods": ["evening"],
        "courseName": "資料結構",
        "weeklyClasses": [],
        "personalEvents": [],
    }


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def post(self, url, **kwargs):
        self.requests.append({"url": url, **kwargs})
        return FakeResponse(self.responses.pop(0))


def test_openai_two_turn_tool_loop_uses_server_key_and_strict_schemas():
    data = request_payload()
    session = FakeSession(
        [
            {
                "output": [
                    {
                        "type": "function_call",
                        "call_id": "call-study-plan",
                        "name": TOOL_NAME,
                        "arguments": json.dumps(data),
                    }
                ],
                "usage": {"input_tokens": 20, "output_tokens": 5},
            },
            {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(
                                    {
                                        "assessment": "insufficient",
                                        "summary": "仍有 120 分鐘未排入。",
                                        "recommendations": ["增加可安排時段。"],
                                        "citations": [
                                            "planner-rule",
                                            "study-load-review",
                                        ],
                                    },
                                    ensure_ascii=False,
                                ),
                            }
                        ],
                    }
                ],
                "usage": {"input_tokens": 12, "output_tokens": 8},
            },
            {
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(
                                    {
                                        "summary": "已完成安全排程。",
                                        "warnings": [],
                                        "citations": ["planner-rule"],
                                        "refused": False,
                                    },
                                    ensure_ascii=False,
                                ),
                            }
                        ],
                    }
                ],
                "usage": {"input_tokens": 25, "output_tokens": 10},
            },
        ]
    )
    client = OpenAIResponsesClient(
        config=OpenAIConfig(model="gpt-test"),
        api_key="test-server-only-key",
        session=session,
    )

    function_call, history, selection_meta = client.choose_tool(data)
    expert_review, expert_meta = client.review_plan(
        {
            "task": {
                "courseName": "資料結構",
                "startDate": "2026-09-17",
                "examDate": "2026-09-24",
                "hours": 2,
                "sessionHours": 1,
                "allowedPeriods": ["evening"],
            },
            "plan": {
                "sessions": [],
                "scheduledMinutes": 0,
                "remainingMinutes": 120,
            },
            "deterministicChecks": {"issueCount": 0, "source": "planner-rule"},
        }
    )
    explanation, summary_meta = client.summarize(
        history,
        {"sessions": [], "scheduledMinutes": 0, "remainingMinutes": 120},
        expert_review,
    )

    assert function_call == {
        "name": TOOL_NAME,
        "args": data,
        "call_id": "call-study-plan",
    }
    assert explanation["summary"] == "已完成安全排程。"
    assert selection_meta["usage"]["input_tokens"] == 20
    assert expert_meta["usage"]["output_tokens"] == 8
    assert expert_meta["contextVersion"] == EXPERT_CONTEXT_CANDIDATE
    assert expert_review["assessment"] == "insufficient"
    assert summary_meta["usage"]["output_tokens"] == 10
    assert len(session.requests) == 3
    assert session.requests[0]["headers"]["Authorization"] == (
        "Bearer test-server-only-key"
    )
    assert session.requests[0]["json"]["tools"][0]["strict"] is True
    assert (
        session.requests[0]["json"]["tools"][0]["parameters"][
            "additionalProperties"
        ]
        is False
    )
    assert "tools" not in session.requests[1]["json"]
    assert (
        session.requests[1]["json"]["text"]["format"]["name"]
        == "study_load_expert_review"
    )
    assert "Week 09 few-shot" in session.requests[1]["json"]["instructions"]
    assert session.requests[2]["json"]["input"][-2]["type"] == (
        "function_call_output"
    )
    assert session.requests[2]["json"]["text"]["format"]["strict"] is True
    assert "test-server-only-key" not in repr(client.config)


def test_week09_baseline_and_candidate_use_different_context_with_same_packet():
    expert_output = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": json.dumps(
                            {
                                "assessment": "balanced",
                                "summary": "固定輸出。",
                                "recommendations": [],
                                "citations": ["planner-rule"],
                            },
                            ensure_ascii=False,
                        ),
                    }
                ],
            }
        ],
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }
    session = FakeSession([expert_output, expert_output])
    client = OpenAIResponsesClient(
        config=OpenAIConfig(model="gpt-test"),
        api_key="test-server-only-key",
        session=session,
    )
    packet = {
        "task": {
            "courseName": "資料結構",
            "startDate": "2026-09-17",
            "examDate": "2026-09-24",
            "hours": 6,
            "sessionHours": 2,
            "allowedPeriods": ["afternoon", "evening"],
        },
        "plan": {
            "sessions": [
                {"date": "2026-09-17", "start": "18:00", "end": "20:00"},
                {"date": "2026-09-18", "start": "13:00", "end": "15:00"},
                {"date": "2026-09-19", "start": "13:00", "end": "15:00"},
            ],
            "scheduledMinutes": 360,
            "remainingMinutes": 0,
        },
        "deterministicChecks": {"issueCount": 0, "source": "planner-rule"},
    }

    _, baseline_meta = client.review_plan(
        packet,
        context_variant=EXPERT_CONTEXT_BASELINE,
    )
    _, candidate_meta = client.review_plan(
        packet,
        context_variant=EXPERT_CONTEXT_CANDIDATE,
    )

    baseline_request, candidate_request = session.requests
    assert baseline_request["json"]["input"] == candidate_request["json"]["input"]
    assert "Week 09 few-shot" not in baseline_request["json"]["instructions"]
    assert "Week 09 few-shot" in candidate_request["json"]["instructions"]
    assert baseline_meta["contextVersion"] == EXPERT_CONTEXT_BASELINE
    assert candidate_meta["contextVersion"] == EXPERT_CONTEXT_CANDIDATE
    assert "tools" not in baseline_request["json"]
    assert "tools" not in candidate_request["json"]


def test_openai_requires_server_side_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(OpenAIProviderError) as error:
        OpenAIResponsesClient(session=FakeSession([]))
    assert error.value.code == "OPENAI_API_KEY_NOT_CONFIGURED"
    assert error.value.attempted is False


def test_openai_health_reports_presence_without_exposing_key(monkeypatch, tmp_path):
    monkeypatch.setenv("STUDY_AGENT_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "health-test-secret")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "openai-health.sqlite3"),
        }
    )

    response = app.test_client().get("/api/v1/study-agent/health")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["provider"] == "OpenAI Responses API"
    assert payload["authentication"] == "Server-side API key"
    assert payload["keyConfigured"] is True
    assert payload["model"] == "gpt-test"
    assert "health-test-secret" not in response.get_data(as_text=True)
    assert payload["liveChecked"] is False


def test_invalid_provider_is_rejected_without_model_call(monkeypatch, tmp_path):
    monkeypatch.setenv("STUDY_AGENT_PROVIDER", "unknown")
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "invalid-provider.sqlite3"),
        }
    )

    response = app.test_client().get("/api/v1/study-agent/health")

    assert response.status_code == 503
    assert response.get_json() == {
        "ok": False,
        "code": "INVALID_STUDY_AGENT_PROVIDER",
        "liveChecked": False,
    }
