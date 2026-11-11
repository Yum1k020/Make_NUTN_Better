"""HTTP evidence, isolation, bounded live protocol and transactional commit checks."""

from copy import deepcopy
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from app import create_app
from app.db import init_db
from app import agent_provider, agent_engine
from app.agent_engine import Runner
from app.planner_core import Problem

BASE = "/api/v1/agent"


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "agents.sqlite3")})
    with app.app_context():
        init_db()
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def request_data(client, name="normal"):
    return next(e["request"] for e in client.get(BASE + "/examples").json["data"] if e["id"] == name)


def run(client, payload=None):
    response = client.post(BASE + "/runs", json=payload or request_data(client))
    assert response.status_code == 201, response.json
    return response.json["data"]


def resources(app):
    with sqlite3.connect(app.config["DATABASE"]) as db:
        return list(db.execute("SELECT * FROM planner_resources ORDER BY id"))


def test_complete_trace_and_read_only(app, client, evidence):
    before = resources(app)
    payload = request_data(client)
    r = run(client, payload)
    assert r["status"] == "completed"
    assert r["result"]["scheduled_minutes"] == 360
    assert r["verification"]["passed"] is True
    assert r["metrics"]["model_calls"] == 0
    assert r["metrics"]["simulated_turns"] == 5
    assert r["final_role"] == "assistant"
    assert {t["owner"] for t in r["ledger"]} == {"assistant", "scheduler"}
    assert all(t["status"] == "completed" for t in r["ledger"])
    assert r["messages"][0]["from"] == "scheduler"
    assert resources(app) == before
    assert client.get(BASE + "/runs/" + r["run_id"]).json["data"] == r
    assert client.get(BASE + "/runs").json["data"][0]["run_id"] == r["run_id"]
    evidence.append({"request": payload, "response": r, "planner_unchanged": True})


def test_partial_and_baseline(client, evidence):
    p = request_data(client, "shortage")
    multi = run(client, p)
    p["architecture"] = "single"
    single = run(client, p)
    for r in (multi, single):
        assert r["status"] == "partial"
        assert r["result"]["remaining_minutes"] == 240
        assert r["verification"]["passed"]
    assert single["metrics"]["simulated_turns"] == 3
    assert multi["snapshot_version"] == single["snapshot_version"]
    assert multi["result"]["candidates"] == single["result"]["candidates"]
    evidence.append({"multi": multi, "single": single, "note": "Offline only; not a model performance result"})


def test_zero_slots_cannot_commit(client):
    p = request_data(client)
    p["plan"]["allowed_windows"] = [{"weekday": 7, "start_time": "19:00", "end_time": "21:00"}]
    r = run(client, p)
    assert r["status"] == "partial" and r["result"]["scheduled_minutes"] == 0
    response = client.post(BASE + f'/runs/{r["run_id"]}/commit', json={"confirmed": True})
    assert response.status_code == 409 and response.json["error"]["code"] == "EMPTY_SCHEDULE"


def test_avoids_events(client):
    response = client.post("/api/v1/personal-events", json={"title": "社團", "starts_at": "2026-11-16T19:00:00+08:00", "ends_at": "2026-11-16T20:00:00+08:00"})
    assert response.status_code == 201
    r = run(client)
    assert r["result"]["candidates"][0]["starts_at"] == "2026-11-16T20:00:00+08:00"
    assert r["verification"]["passed"]


def test_unknown_schedule_fails_without_write(app, client, evidence):
    response = client.post("/api/v1/enrollments", json={"course_id": "course-demo-001", "semester_id": "semester-115-1", "enrollment_status": "in_progress"})
    assert response.status_code == 201
    before = resources(app)
    r = run(client)
    assert r["status"] == "failed" and r["error"]["code"] == "SCHEDULE_INCOMPLETE"
    assert not r["verification"]["passed"] and r["result"] is None
    assert resources(app) == before
    evidence.append(r)


@pytest.mark.parametrize("field,value", [("target_minutes", True), ("target_minutes", 14401), ("session_minutes", 14),
    ("session_minutes", 241), ("allowed_windows", []), ("exam_date", "2026-11-16"),
    ("exam_date", "2027-11-16"), ("course_id", "not-a-course")])
def test_invalid_plan_does_not_write(app, client, field, value):
    p = request_data(client)
    p["plan"][field] = value
    before = resources(app)
    response = client.post(BASE + "/runs", json=p)
    assert response.status_code == 422, response.json
    assert resources(app) == before
    assert client.get(BASE + "/runs").json["data"] == []


def test_boundary_contract(client):
    assert client.post(BASE + "/runs", data="{}").status_code == 415
    assert client.post(BASE + "/runs", data="{", content_type="application/json").status_code == 400
    p = request_data(client)
    p["user_id"] = "someone-else"
    assert client.post(BASE + "/runs", json=p).status_code == 422
    assert client.get(BASE + "/config?unexpected=1").status_code == 422
    assert client.get(BASE + "/runs/no-such-run").status_code == 404
    p.pop("user_id")
    p["provider"] = "openai"
    assert client.post(BASE + "/runs", json=p).status_code == 503


def test_commit_idempotent_and_reverification(app, client, evidence):
    r = run(client)
    url = BASE + f'/runs/{r["run_id"]}/commit'
    assert client.post(url, json={"confirmed": False}).status_code == 422
    response = client.post(url, json={"confirmed": True})
    assert response.status_code == 201, response.json
    first = response.json["data"]
    after = resources(app)
    replay = client.post(url, json={"confirmed": True})
    assert replay.status_code == 200 and replay.json["data"] == first
    assert resources(app) == after
    verification = client.post(BASE + f'/runs/{r["run_id"]}/verify').json["data"]
    assert verification["passed"]
    assert len([x for x in after if x[0] == "study-plans"]) == 1
    evidence.append({"commit": first, "replay": replay.json, "verification": verification})


def test_concurrent_commit_creates_one_plan(app, client):
    r = run(client)
    def commit():
        return app.test_client().post(BASE + f'/runs/{r["run_id"]}/commit', json={"confirmed": True})
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: commit(), range(2)))
    assert sorted(r.status_code for r in responses) == [200, 201]
    assert len([x for x in resources(app) if x[0] == "study-plans"]) == 1


def test_stale_schedule_blocks_commit(app, client, evidence):
    r = run(client)
    response = client.post("/api/v1/personal-events", json={"title": "新增行程", "starts_at": "2026-11-16T19:00:00+08:00", "ends_at": "2026-11-16T20:00:00+08:00"})
    assert response.status_code == 201
    before = resources(app)
    v = client.post(BASE + f'/runs/{r["run_id"]}/verify').json["data"]
    assert not v["passed"]
    response = client.post(BASE + f'/runs/{r["run_id"]}/commit', json={"confirmed": True})
    assert response.status_code == 409
    assert resources(app) == before
    evidence.append({"verification": v, "commit_error": response.json})


def test_edited_commit_fails_verification(client):
    r = run(client)
    saved = client.post(BASE + f'/runs/{r["run_id"]}/commit', json={"confirmed": True}).json["data"]
    assert client.patch("/api/v1/study-plans/" + saved["plan_id"], json={"target_minutes": 420}).status_code == 200
    v = client.post(BASE + f'/runs/{r["run_id"]}/verify').json["data"]
    assert not v["passed"]
    assert next(c for c in v["checks"] if c["id"] == "committed_version")["passed"] is False


def live_config(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key-do-not-export")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")


def tool(name, args=None):
    return {"output": [{"type": "function_call", "name": name, "call_id": "test-call", "arguments": json.dumps(args or {})}],
            "usage": {"input_tokens": 10, "output_tokens": 5}, "id": "test-response"}


def successful_provider(instructions, messages, tools, timeout):
    names = [t["name"] for t in tools]
    outputs = [json.loads(m["output"]) for m in messages if m.get("type") == "function_call_output"]
    if not outputs:
        return tool("delegate_scheduler" if "delegate_scheduler" in names else "get_availability")
    last = outputs[-1]
    if "scheduled_minutes" not in last:
        return tool("generate_schedule")
    return tool("finish", {"scheduled_minutes": last["scheduled_minutes"], "remaining_minutes": last["remaining_minutes"],
                           "source_ids": last["source_ids"], "explanation": "測試用模型回應：依工具事實交付，未儲存。"})


def test_openai_protocol_with_stub(client, monkeypatch, evidence):
    live_config(monkeypatch)
    monkeypatch.setattr(agent_provider, "respond", successful_provider)
    p = request_data(client)
    p["provider"] = "openai"
    r = run(client, p)
    assert r["status"] == "completed"
    assert r["metrics"]["model_calls"] == 5 and r["metrics"]["simulated_turns"] == 0
    assert r["metrics"]["input_tokens"] == 50
    assert "fake-test-key" not in json.dumps(r)
    evidence.append({"mock_provider": True, "live_network_calls": 0, "result": r})


@pytest.mark.parametrize("case,expected", [("unauthorized", "ROLE_TOOL_DENIED"), ("override", "INVALID_TOOL_ARGUMENTS"),
    ("premature", "MISSING_TOOL_EVIDENCE"), ("timeout", "PROVIDER_TIMEOUT"), ("repeat", "REPEATED_TOOL_CALL"),
    ("wrong_total", "UNGROUNDED_RESULT"), ("wrong_source", "UNGROUNDED_RESULT"), ("batch", "INVALID_TOOL_BATCH")])
def test_provider_failures_are_auditable(app, client, monkeypatch, case, expected):
    live_config(monkeypatch)
    def responder(instructions, messages, tools, timeout):
        if case == "unauthorized": return tool("delete_calendar")
        if case == "override": return tool("delegate_scheduler", {"target_minutes": 0})
        if case == "premature": return tool("finish")
        if case == "timeout": raise Problem(504, "PROVIDER_TIMEOUT", "模型逾時")
        if case == "repeat": return tool("delegate_scheduler" if any(t["name"] == "delegate_scheduler" for t in tools) else "get_availability")
        if case == "batch": return {"output": [tool("finish")["output"][0]] * 2}
        response = successful_provider(instructions, messages, tools, timeout)
        call = response["output"][0]
        if call["name"] == "finish":
            args = json.loads(call["arguments"])
            args["scheduled_minutes" if case == "wrong_total" else "source_ids"] = 999 if case == "wrong_total" else ["invented"]
            call["arguments"] = json.dumps(args)
        return response
    monkeypatch.setattr(agent_provider, "respond", responder)
    p = request_data(client)
    p["provider"] = "openai"
    before = resources(app)
    r = run(client, p)
    assert r["status"] == "failed" and r["error"]["code"] == expected
    assert resources(app) == before
    assert not r["verification"]["passed"]
    assert client.get(BASE + "/runs/" + r["run_id"]).status_code == 200


def test_budget_limit(client, monkeypatch):
    monkeypatch.setattr(agent_engine, "MAX_CALLS", 1)
    r = run(client)
    assert r["status"] == "failed" and r["error"]["code"] == "AGENT_BUDGET_EXCEEDED"


def test_commit_rolls_back_after_partial_write(app, client, monkeypatch):
    from app import agent_api
    r = run(client)
    before = resources(app)
    def fail(*args):
        raise Problem(409, "TEST_ROLLBACK", "測試回滾")
    monkeypatch.setattr(agent_api, "replace_sessions", fail)
    response = client.post(BASE + f'/runs/{r["run_id"]}/commit', json={"confirmed": True})
    assert response.status_code == 409
    assert resources(app) == before
    assert client.get(BASE + "/runs/" + r["run_id"]).json["data"]["commit"] is None


def test_api_docs_and_separate_interface(client):
    assert client.get("/agent-lab").status_code == 200
    assert client.get("/agent-lab/assets/app.js").status_code == 200
    assert client.get("/").location == "/docs"
    paths = client.get("/openapi.json").json["paths"]
    assert "post" in paths[BASE + "/runs"] and "get" in paths[BASE + "/runs"]
    assert BASE + "/runs/{run_id}/commit" in paths
    assert "/api/v1/study-plans" in paths


def test_transport_payload_and_no_secret_in_error(monkeypatch):
    from urllib.error import HTTPError
    live_config(monkeypatch)
    captured = {}
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size):
            return json.dumps({"status": "completed", "output": []}).encode()
    def send(request, timeout):
        captured.update(url=request.full_url, payload=json.loads(request.data), timeout=timeout)
        assert request.get_header("Authorization") == "Bearer fake-test-key-do-not-export"
        return Response()
    monkeypatch.setattr(agent_provider, "urlopen", send)
    agent_provider.respond("instructions", [{"role": "user", "content": "test"}], [], 10)
    assert captured["url"] == "https://api.openai.com/v1/responses"
    assert captured["payload"]["store"] is False
    assert captured["payload"]["parallel_tool_calls"] is False
    assert captured["payload"]["include"] == ["reasoning.encrypted_content"]
    assert captured["timeout"] == 10
    def error(*args, **kwargs):
        raise HTTPError("https://api.openai.com/v1/responses", 429, "secret provider text", {}, None)
    monkeypatch.setattr(agent_provider, "urlopen", error)
    with pytest.raises(Problem) as raised:
        agent_provider.respond("", [], [], 10)
    assert raised.value.code == "PROVIDER_RATE_LIMIT"
    assert "secret" not in raised.value.message


def test_missing_usage_and_late_result(client, monkeypatch):
    live_config(monkeypatch)
    def no_usage(*args):
        response = successful_provider(*args)
        response["usage"] = None
        return response
    monkeypatch.setattr(agent_provider, "respond", no_usage)
    p = request_data(client)
    p["provider"] = "openai"
    r = run(client, p)
    assert r["status"] == "completed" and not r["metrics"]["usage_complete"]
    ticks = iter([0, 0, 121, 121])
    monkeypatch.setattr(agent_engine.time, "monotonic", lambda: next(ticks, 121))
    r = run(client, p)
    assert r["status"] == "failed" and r["error"]["code"] == "AGENT_BUDGET_EXCEEDED"
