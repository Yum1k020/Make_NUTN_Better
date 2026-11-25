from types import SimpleNamespace

import pytest

from app import create_app
from app.study_agent_api import (
    StudyAgentService,
    get_validated_study_plan,
    normalize_request,
)
from app.study_agent_contract import TOOL_NAME
from app.study_agent_openai import (
    EXPERT_CONTEXT_BASELINE,
    EXPERT_CONTEXT_CANDIDATE,
)


def request_payload(**overrides):
    payload = {
        "startDate": "2026-09-17",
        "examDate": "2026-09-24",
        "hours": 6,
        "sessionHours": 2,
        "allowedPeriods": ["afternoon", "evening"],
        "courseName": "資料結構",
        "weeklyClasses": [
            {
                "id": "class-programming-thursday",
                "title": "程式設計（一）",
                "weekday": 4,
                "start": "14:00",
                "end": "15:50",
                "location": "文薈樓 J201",
            }
        ],
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
        self.expert_context_versions = []

    def choose_tool(self, data):
        args = self.mutate(dict(data)) if self.mutate else data
        return (
            {"name": TOOL_NAME, "args": args},
            [{"role": "user", "content": [{"type": "input_text", "text": "synthetic"}]}],
            {"usage": {"input_tokens": 10}},
        )

    def review_plan(self, packet, *, context_variant=EXPERT_CONTEXT_CANDIDATE):
        self.expert_packets.append(packet)
        self.expert_context_versions.append(context_variant)
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
            {
                "usage": {"input_tokens": 8, "output_tokens": 6},
                "contextVersion": context_variant,
            },
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
                    "weekly-classes-backend-sqlite",
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
    result_without_classes = get_validated_study_plan(
        request_payload(weeklyClasses=[])
    )
    assert result["scheduledMinutes"] == 360
    assert result["remainingMinutes"] == 0
    assert len(result["sessions"]) == 3
    assert result["sessions"][0]["id"] == "study-2026-09-17-18:00"
    assert result_without_classes["sessions"][0]["id"] == "study-2026-09-17-13:00"


def test_main_flow_records_function_call_validation_and_response():
    service = StudyAgentService(provider_factory=FakeProvider)
    result = service.run(request_payload())
    assert result["workflow"]["status"] == "completed"
    assert result["workflow"]["runId"].startswith("week09-")
    assert result["workflow"]["version"] == EXPERT_CONTEXT_CANDIDATE
    assert result["optimization"]["method"] == "few-shot prompting"
    assert result["optimization"]["expectedAssessment"] == "balanced"
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
    assert result["multiAgent"]["expertReview"]["assessment"] == "balanced"


def test_week10_data_package_integrates_backend_inputs_and_redacts_private_text():
    service = StudyAgentService(provider_factory=FakeProvider)
    result = service.run(request_payload())

    package = result["dataPackage"]
    assert package["schemaVersion"] == "week10-agent-data-v1"
    assert package["packageId"].startswith("week10-data-week09-")
    assert package["environment"]["weeklyClasses"]["source"] == (
        "flask-sqlite:academic-timetable"
    )
    assert package["environment"]["weeklyClasses"]["count"] == 1
    assert package["environment"]["personalEvents"]["source"] == (
        "flask-sqlite:personal-events"
    )
    assert package["environment"]["personalEvents"]["count"] == 2
    serialized_events = repr(package["environment"]["personalEvents"]["records"])
    assert "社團會議" not in serialized_events
    assert "活動中心 3 樓" not in serialized_events
    assert package["trajectory"]["stepCount"] == len(result["workflow"]["stages"])
    assert package["verifier"]["planIssueCount"] == 0
    assert package["verifier"]["expectedAssessment"] == "balanced"
    assert package["verifier"]["actualAssessment"] == "balanced"
    assert package["verifier"]["passed"] is True
    assert package["provenance"]["integratesClassmateData"] is True
    assert package["provenance"]["credentialsIncluded"] is False
    assert package["provenance"]["personalEventTextIncluded"] is False


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
        def review_plan(self, packet, *, context_variant=EXPERT_CONTEXT_CANDIDATE):
            self.expert_packets.append(packet)
            self.expert_context_versions.append(context_variant)
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


def test_week09_same_case_comparison_scores_baseline_and_candidate():
    class ComparisonProvider(FakeProvider):
        def review_plan(self, packet, *, context_variant=EXPERT_CONTEXT_CANDIDATE):
            self.expert_packets.append(packet)
            self.expert_context_versions.append(context_variant)
            assessment = (
                "concentrated"
                if context_variant == EXPERT_CONTEXT_BASELINE
                else "balanced"
            )
            return (
                {
                    "assessment": assessment,
                    "summary": f"{context_variant} 測試輸出。",
                    "recommendations": [],
                    "citations": ["planner-rule", "study-load-review"],
                },
                {
                    "usage": {"input_tokens": 8, "output_tokens": 6},
                    "contextVersion": context_variant,
                },
            )

    provider = ComparisonProvider()
    service = StudyAgentService(provider_factory=lambda: provider)

    result = service.compare_context(request_payload())

    assert result["sameCase"] is True
    assert result["expectedAssessment"] == "balanced"
    assert provider.expert_context_versions == [
        EXPERT_CONTEXT_BASELINE,
        EXPERT_CONTEXT_CANDIDATE,
    ]
    assert provider.expert_packets[0] == provider.expert_packets[1]
    assert result["versions"]["baseline"]["evaluation"]["pass"] is False
    assert result["versions"]["candidate"]["evaluation"]["pass"] is True
    assert "由未通過變為通過" in result["observation"]


def test_week09_context_comparison_http_endpoint(tmp_path):
    class ComparisonProvider(FakeProvider):
        def review_plan(self, packet, *, context_variant=EXPERT_CONTEXT_CANDIDATE):
            self.expert_packets.append(packet)
            self.expert_context_versions.append(context_variant)
            return (
                {
                    "assessment": "balanced",
                    "summary": "固定案例輸出。",
                    "recommendations": [],
                    "citations": ["planner-rule"],
                },
                {"usage": {}, "contextVersion": context_variant},
            )

    provider = ComparisonProvider()
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "week09.sqlite3"),
            "STUDY_AGENT_SERVICE_FACTORY": service_factory(provider),
        }
    )
    response = app.test_client().post(
        "/api/v1/study-agent/context-comparison",
        json=request_payload(),
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["sameCase"] is True
    assert body["versions"]["baseline"]["contextVersion"] == EXPERT_CONTEXT_BASELINE
    assert body["versions"]["candidate"]["contextVersion"] == EXPERT_CONTEXT_CANDIDATE
    assert body["sharedContext"]["sameDeterministicPlan"] is True


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


def test_request_schema_rejects_invalid_weekly_class():
    invalid = [
        {
            "id": "bad-class",
            "title": "錯誤課程",
            "weekday": 7,
            "start": "09:00",
            "end": "10:00",
            "location": "測試教室",
        }
    ]
    with pytest.raises(ValueError, match="weekday"):
        normalize_request(request_payload(weeklyClasses=invalid))


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
    assert body["workflow"]["runId"].startswith("week09-")
    assert body["optimization"]["candidateContextVersion"] == EXPERT_CONTEXT_CANDIDATE
    assert body["dataPackage"]["schemaVersion"] == "week10-agent-data-v1"
    assert body["dataPackage"]["verifier"]["passed"] is True

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
