"""Week 06: injected failures are explicitly distinct from Gemini live evidence."""

from copy import deepcopy
import sqlite3

import pytest

from app import create_app
from app.db import init_db
from app.graduation_explanation_core import (
    ProviderFailure, evaluate, evidence_context, explain, valid_draft,
)
from app.planner_graduation import make_check


@pytest.fixture
def result():
    return {"rule_set_id": "synthetic-v1", "overall_status": "not_met", "earned_credits": 3,
            "checks": [make_check("total_credits", "總學分", 133, 3),
                       make_check("lecture_general", "一般講座", 12, None),
                       make_check("lecture_professional", "專業講座", 10, 10)]}


def fixture_provider(context, previous, feedback):
    return valid_draft(context), {"provider": "fixture", "usage": {}, "latency_ms": 0}


def test_valid_first_draft(result):
    output = explain(result, fixture_provider)
    assert output["status"] == "verified" and output["model_calls"] == 1
    assert output["stop_reason"] == "RUBRIC_PASS"
    assert "未知" in output["explanation"][1]["text"]
    assert output["attempts"][0]["metrics"]["provider"] == "fixture"


@pytest.mark.parametrize("defect", ["credits", "source", "unknown", "scope", "action", "duplicate", "prose", "boolean"])
def test_same_rubric_rejects_wrong_claims(result, defect):
    context = evidence_context(result)
    draft = valid_draft(context)
    if defect == "credits": draft["earned_credits"] = 99
    if defect == "source": draft["items"][0]["source_ids"] = ["fabricated"]
    if defect == "unknown": draft["items"][1]["actual_value"] = 0
    if defect == "scope": draft["scope"] = "official_graduation_approval"
    if defect == "action": draft["items"][1]["action"] = "keep_record"
    if defect == "duplicate": draft["items"][1] = deepcopy(draft["items"][0])
    if defect == "prose": draft["summary"] = "下學期保證開課"
    if defect == "boolean": draft["items"][0]["actual_value"] = True
    assert evaluate(draft, context)


def test_boundary_revision_gets_feedback_and_same_context(result, evidence):
    seen = []
    def provider(context, previous, feedback):
        seen.append(deepcopy((context, previous, feedback)))
        draft, metrics = fixture_provider(context, previous, feedback)
        if not previous:
            draft["items"][0]["source_ids"] = []
            draft["earned_credits"] = 130
        return draft, metrics
    before = deepcopy(result)
    output = explain(result, provider)
    assert result == before and seen[0][0] == seen[1][0]
    assert seen[1][1] == output["attempts"][0]["draft"]
    assert seen[1][2] == output["attempts"][0]["errors"]
    assert [a["passed"] for a in output["attempts"]] == [False, True]
    assert output["model_calls"] == 2 and output["status"] == "verified"
    evidence.append({"kind": "injected_boundary", "expected": "A rejected, B passes same rubric", "actual": output})


def test_boundary_revision_limit(result, evidence):
    def provider(context, previous, feedback):
        draft, metrics = fixture_provider(context, previous, feedback)
        draft["earned_credits"] = 999
        return draft, metrics
    output = explain(result, provider)
    assert output["model_calls"] == 2
    assert output["stop_reason"] == "REVISION_LIMIT" and output["status"] == "fallback"
    assert all(not a["passed"] for a in output["attempts"])
    assert "999" not in str(output["explanation"])
    evidence.append({"kind": "injected_boundary", "expected": "stop after B, show authoritative facts", "actual": output})


def test_provider_failure_is_bounded(result, evidence):
    def provider(*args):
        raise ProviderFailure("PROVIDER_UNAVAILABLE", attempted=True)
    output = explain(result, provider)
    assert output["model_calls"] == 1 and not output["attempts"]
    assert output["stop_reason"] == "PROVIDER_UNAVAILABLE"
    assert output["explanation"]
    evidence.append({"kind": "injected_provider_failure", "expected": "one call, fallback", "actual": output})


def test_missing_rule_skips_provider(result):
    result.update(rule_set_id=None, checks=[], earned_credits=None)
    def forbidden(*args):
        pytest.fail("provider called without rules")
    output = explain(result, forbidden)
    assert output["stop_reason"] == "RULE_UNAVAILABLE" and output["model_calls"] == 0


def test_provider_cannot_modify_authoritative_context(result):
    def provider(context, previous, feedback):
        context["earned_credits"] = 999
        return fixture_provider(context, previous, feedback)
    output = explain(result, provider)
    assert output["stop_reason"] == "REVISION_LIMIT"
    assert output["evidence"]["earned_credits"] == 3


@pytest.fixture
def explanation_app(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "graduation.sqlite3"),
                      "GRADUATION_ENGINE": "langgraph",
                      "GRADUATION_EXPLANATION_PROVIDER": fixture_provider})
    with app.app_context():
        init_db()
    client = app.test_client()
    assert client.patch("/api/v1/me", json={"department_id": "dept-nutn-csie", "admission_year": 115,
                                          "current_semester_id": "semester-115-1"}).status_code == 200
    return app


def db_digest(app):
    with sqlite3.connect(app.config["DATABASE"]) as db:
        return "\n".join(db.iterdump())


def test_http_read_only_and_same_progress(explanation_app, evidence):
    client = explanation_app.test_client()
    before = db_digest(explanation_app)
    original = client.get("/api/v1/graduation-progress").json["data"]
    response = client.post("/api/v1/graduation-explanation")
    assert response.status_code == 200
    data = response.json["data"]
    assert data["workflow"]["status"] == "verified"
    assert {k: v for k, v in original.items() if k != "evaluated_at"} == {
        k: v for k, v in data["progress"].items() if k != "evaluated_at"}
    assert db_digest(explanation_app) == before
    assert client.post("/api/v1/graduation-explanation").json["data"]["workflow"]["run_id"] != data["workflow"]["run_id"]
    evidence.append({"kind": "fixture_http_normal", "expected": "200, original facts, no writes", "actual": data})


@pytest.mark.parametrize("suffix,kwargs", [("?user_id=other", {}), ("", {"json": {"earned_credits": 999}}),
                                           ("", {"data": "{}", "content_type": "application/json"})])
def test_invalid_input_zero_downstream(explanation_app, evidence, suffix, kwargs):
    def forbidden(*args):
        pytest.fail("invalid input called model")
    explanation_app.config["GRADUATION_EXPLANATION_PROVIDER"] = forbidden
    before = db_digest(explanation_app)
    response = explanation_app.test_client().post("/api/v1/graduation-explanation" + suffix, **kwargs)
    assert response.status_code == 422
    assert db_digest(explanation_app) == before
    evidence.append({"kind": "invalid_input", "expected": "422, provider zero calls, no writes", "actual": response.json})


def test_database_error_zero_downstream(explanation_app):
    def forbidden(*args): pytest.fail("database failure called model")
    explanation_app.config["GRADUATION_EXPLANATION_PROVIDER"] = forbidden
    with sqlite3.connect(explanation_app.config["DATABASE"]) as db:
        db.execute("UPDATE graduation_rule_documents SET digest='corrupt'")
    response = explanation_app.test_client().post("/api/v1/graduation-explanation")
    assert response.status_code == 500


def test_source_projection_excludes_identity(result):
    result.update(user_id="private", raw_grades=[100], student_name="private")
    assert "private" not in str(evidence_context(result))


def test_provider_missing_config_zero_requests(result, monkeypatch):
    from app import graduation_gemini
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(graduation_gemini, "urlopen", lambda *a, **k: pytest.fail("missing config made request"))
    output = explain(result, graduation_gemini.generate)
    assert output["stop_reason"] == "PROVIDER_NOT_CONFIGURED" and output["model_calls"] == 0


def test_provider_request_and_thought_filter(result, monkeypatch):
    import json
    from app import graduation_gemini
    context = evidence_context(result)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, limit):
            return json.dumps({"candidates": [{"finishReason": "STOP", "content": {"parts": [
                {"thought": True, "text": "not output"}, {"text": json.dumps(valid_draft(context))}]}}],
                "usageMetadata": {"promptTokenCount": 17}}).encode()
    def fake_open(req, timeout):
        assert timeout == 25 and req.full_url.endswith("test-model:generateContent")
        assert "test-key-not-real" not in req.full_url
        payload = json.loads(req.data)
        assert payload["generationConfig"]["responseMimeType"] == "application/json"
        assert "user_id" not in str(payload)
        return Response()
    monkeypatch.setattr(graduation_gemini, "urlopen", fake_open)
    output = explain(result, graduation_gemini.generate)
    assert output["status"] == "verified"
    assert output["attempts"][0]["metrics"]["usage"]["promptTokenCount"] == 17
    assert "not output" not in str(output)


def test_provider_timeout_is_sanitized(result, monkeypatch):
    from app import graduation_gemini
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    def fail(*a, **k): raise TimeoutError("must not leak test-key-not-real")
    monkeypatch.setattr(graduation_gemini, "urlopen", fail)
    output = explain(result, graduation_gemini.generate)
    assert output["stop_reason"] == "PROVIDER_UNAVAILABLE"
    assert output["model_calls"] == 1 and "test-key-not-real" not in str(output)


def test_http_provider_failure_keeps_progress(explanation_app):
    def fail(*args): raise ProviderFailure("PROVIDER_HTTP_503", attempted=True)
    explanation_app.config["GRADUATION_EXPLANATION_PROVIDER"] = fail
    before = db_digest(explanation_app)
    response = explanation_app.test_client().post("/api/v1/graduation-explanation")
    assert response.status_code == 200
    data = response.json["data"]
    assert data["progress"]["checks"] and data["workflow"]["status"] == "fallback"
    assert data["workflow"]["stop_reason"] == "PROVIDER_HTTP_503"
    assert db_digest(explanation_app) == before


def test_cross_site_cannot_trigger_model(explanation_app):
    def forbidden(*args): pytest.fail("cross-site called model")
    explanation_app.config["GRADUATION_EXPLANATION_PROVIDER"] = forbidden
    response = explanation_app.test_client().post("/api/v1/graduation-explanation", headers={"Origin": "https://other.invalid"})
    assert response.status_code == 403


def test_explicit_dev_proxy_origin(explanation_app, monkeypatch):
    monkeypatch.setenv("GRADUATION_ALLOWED_ORIGINS", "http://127.0.0.1:5173")
    response = explanation_app.test_client().post("/api/v1/graduation-explanation", headers={
        "Origin": "http://127.0.0.1:5173", "Sec-Fetch-Site": "same-origin"})
    assert response.status_code == 200 and response.json["data"]["workflow"]["status"] == "verified"
