import json
import os
import select
import sqlite3
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from app import create_app
from app.db import get_db, init_db

URL = "/api/v1/me"
FULL = {"department_id": "dept-csie", "admission_year": 115,
        "current_semester_id": "semester-115-1"}
EXPECTED = {"user_id": "user-demo-001", **FULL, "rule_set_id": "rules-csie-115-v1",
            "profile_complete": True, "rule_status": "matched"}


@pytest.fixture
def app(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "profile.sqlite3")})
    with app.app_context():
        init_db()
    return app


def snapshot(app):
    with sqlite3.connect(app.config["DATABASE"]) as db:
        db.row_factory = sqlite3.Row
        return [dict(row) for row in db.execute("SELECT * FROM user_profiles ORDER BY user_id")]


@pytest.fixture
def api(app, evidence):
    def call(method="GET", payload=None, raw=None, content_type="application/json", status=200):
        before = snapshot(app)
        trace = []
        with app.app_context():
            get_db().set_trace_callback(trace.append)
            kwargs = {"content_type": content_type}
            if raw is not None:
                kwargs["data"] = raw
            elif payload is not None:
                kwargs["data"] = json.dumps(payload)
            response = app.test_client().open(URL, method=method, **kwargs)
        after = snapshot(app)
        evidence.append({"transport": "Flask test client", "method": method, "path": URL,
                         "content_type": content_type, "input": raw if raw is not None else payload,
                         "expected_status": status, "actual_status": response.status_code,
                         "actual_body": response.json, "before": before, "after": after,
                         "sql_trace": trace})
        assert response.status_code == status
        if status != 200:
            assert after == before
            assert set(response.json) == {"error"}
            assert set(response.json["error"]) == {"code", "message", "fields"}
            if status in (400, 415, 422):
                assert not any(sql.startswith("UPDATE") for sql in trace)
        return response.json
    return call


def test_G01_complete_profile(api):
    assert api("PATCH", FULL) == {"data": EXPECTED}
    assert api() == {"data": EXPECTED}


def test_G02_missing_values(api):
    assert api() == {"data": {"user_id": "user-demo-001", "department_id": None,
                              "admission_year": None, "rule_set_id": None,
                              "current_semester_id": None, "profile_complete": False,
                              "rule_status": "profile_incomplete"}}


@pytest.mark.skip(reason="未執行：baseline 未實作登入驗證，G03 401 留待正式版")
def test_G03_unauthenticated():
    pass


def test_P01_full_patch_and_get(api):
    assert api("PATCH", FULL) == {"data": EXPECTED}
    assert api() == {"data": EXPECTED}


def test_P02_partial_patch(api):
    api("PATCH", FULL)
    expected = {"data": dict(EXPECTED, current_semester_id="semester-115-2")}
    assert api("PATCH", {"current_semester_id": "semester-115-2"}) == expected
    assert api() == expected


@pytest.mark.parametrize("value", ["abc", "115", 115.0, True, [], {}])
def test_P03_strict_integer(api, value):
    api("PATCH", FULL)
    body = api("PATCH", {"admission_year": value}, status=422)
    assert body["error"]["fields"][0]["field"] == "admission_year"
    assert api() == {"data": EXPECTED}


def test_P04_unknown_department(api):
    body = api("PATCH", {"department_id": "unknown"}, status=422)
    assert body["error"]["fields"] == [{"field": "department_id", "reason": "系所不存在"}]


def test_P05_unknown_semester(api):
    body = api("PATCH", {"current_semester_id": "unknown"}, status=422)
    assert body["error"]["fields"] == [{"field": "current_semester_id", "reason": "學期不存在"}]


@pytest.mark.parametrize("payload", [{}, {"department_id": None}, {"admission_year": None},
                                     {"current_semester_id": None}])
def test_P06_empty_or_null(api, payload):
    api("PATCH", payload, status=422)


@pytest.mark.parametrize("field", ["user_id", "rule_set_id", "unexpected"])
def test_P07_readonly_or_unknown_field(api, field):
    body = api("PATCH", {field: "other", "current_semester_id": "semester-115-2"}, status=422)
    assert body["error"]["fields"] == [{"field": field, "reason": "不允許修改此欄位"}]


def test_P08_atomic_validation(api):
    api("PATCH", FULL)
    api("PATCH", {"department_id": "unknown", "current_semester_id": "semester-115-2"}, status=422)
    assert api() == {"data": EXPECTED}


@pytest.mark.parametrize("change", [{"department_id": "dept-demo"}, {"admission_year": 114}])
def test_P09_missing_rule_and_rematch(api, change):
    api("PATCH", FULL)
    expected = {"data": dict(EXPECTED, **change, rule_set_id=None, rule_status="not_found")}
    assert api("PATCH", change) == expected
    assert api() == expected
    assert api("PATCH", FULL) == {"data": EXPECTED}


def test_P10_database_failure_rolls_back(app, api, evidence):
    api("PATCH", FULL)
    with app.app_context():
        get_db().execute("""CREATE TRIGGER simulate_storage_failure AFTER UPDATE ON user_profiles
                         BEGIN SELECT RAISE(FAIL, 'simulated write failure after update'); END""")
        get_db().commit()
    evidence.append({"fault_injection": "SQLite AFTER UPDATE trigger RAISE(FAIL); update runs before failure"})
    body = api("PATCH", {"current_semester_id": "semester-115-2"}, status=500)
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert "ROLLBACK" in evidence[-1]["sql_trace"]
    assert api() == {"data": EXPECTED}


def test_P11_malformed_json(api, evidence):
    body = api("PATCH", raw='{"admission_year":115', status=400)
    assert body["error"]["code"] == "INVALID_JSON"
    assert evidence[-1]["sql_trace"] == []


@pytest.mark.parametrize("payload", [{"admission_year": 116}, {"department_id": ""},
                                     {"current_semester_id": ""}])
def test_X01_unsupported_reference(api, payload):
    api("PATCH", payload, status=422)


@pytest.mark.parametrize("raw", ["null", "[]", '"text"', "115"])
def test_X02_nonobject_json(api, raw):
    api("PATCH", raw=raw, status=422)


def test_X03_media_type(api):
    body = api("PATCH", raw="{}", content_type="text/plain", status=415)
    assert body["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_X04_incomplete_with_matching_rule(api):
    body = api("PATCH", {"department_id": "dept-csie", "admission_year": 115})["data"]
    assert body["rule_set_id"] == "rules-csie-115-v1"
    assert body["current_semester_id"] is None
    assert body["profile_complete"] is False
    assert body["rule_status"] == "profile_incomplete"


def test_X05_related_records_and_other_profile_preserved(app, api, evidence):
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO user_profiles(user_id) VALUES ('user-other')")
        for table in ("fixture_courses", "fixture_todos", "fixture_events"):
            db.execute(f"CREATE TABLE {table} (id TEXT, user_id TEXT REFERENCES user_profiles(user_id) ON DELETE CASCADE)")
            db.execute(f"INSERT INTO {table} VALUES ('keep', 'user-demo-001')")
        db.commit()
    api("PATCH", FULL)
    with app.app_context():
        related = {table: [tuple(row) for row in get_db().execute(f"SELECT * FROM {table}")]
                   for table in ("fixture_courses", "fixture_todos", "fixture_events")}
    evidence.append({"synthetic_related_records_after": related})
    assert all(rows == [("keep", "user-demo-001")] for rows in related.values())
    assert snapshot(app)[1] == {"user_id": "user-other", "department_id": None,
                                "admission_year": None, "rule_set_id": None, "current_semester_id": None}


def test_X06_init_idempotent(app, api):
    api("PATCH", FULL)
    before = snapshot(app)
    result = app.test_cli_runner().invoke(args=["init-db"])
    assert result.exit_code == 0
    assert snapshot(app) == before
    assert api() == {"data": EXPECTED}


def test_X07_invalid_response_rolls_back(app, api, monkeypatch, evidence):
    from app import profile
    api("PATCH", FULL)
    original = profile.make_response_data
    def invalid_response(*args):
        from marshmallow import ValidationError
        raise ValidationError("simulated invalid response")
    monkeypatch.setattr(profile, "make_response_data", invalid_response)
    evidence.append({"fault_injection": "Response validation raises ValidationError after UPDATE, before COMMIT"})
    api("PATCH", {"current_semester_id": "semester-115-2"}, status=500)
    assert "ROLLBACK" in evidence[-1]["sql_trace"]
    monkeypatch.setattr(profile, "make_response_data", original)
    assert api() == {"data": EXPECTED}


def test_X08_openapi(app):
    spec = app.test_client().get("/openapi.json").json
    operations = spec["paths"][URL]
    assert {"get", "patch"} <= operations.keys()
    assert {"200", "400", "415", "422", "500"} <= operations["patch"]["responses"].keys()
    schema = operations["patch"]["requestBody"]["content"]["application/json"]["schema"]
    assert schema["minProperties"] == 1 and schema["additionalProperties"] is False


def test_X09_real_http_process_restart(app, evidence):
    backend = Path(__file__).resolve().parents[1]
    code = ("from app import create_app; from werkzeug.serving import make_server; "
            "server = make_server('127.0.0.1', 0, create_app()); "
            "print(server.server_port, flush=True); server.serve_forever()")
    env = dict(os.environ, ME_DATABASE=app.config["DATABASE"], PYTHONDONTWRITEBYTECODE="1")
    def exchange(port, method="GET", payload=None, raw=None):
        data = raw.encode() if raw is not None else json.dumps(payload).encode() if payload else None
        req = Request(f"http://127.0.0.1:{port}{URL}", data=data, method=method,
                      headers={"Content-Type": "application/json"})
        try:
            response = urlopen(req, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            status, body = response.status, json.load(response)
        evidence.append({"transport": "real HTTP / subprocess", "method": method,
                         "url": req.full_url, "input": raw if raw is not None else payload,
                         "actual_status": status, "actual_body": body})
        return status, body
    for phase in ("before restart", "after restart"):
        process = subprocess.Popen([sys.executable, "-u", "-c", code], cwd=backend, env=env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            assert select.select([process.stdout], [], [], 10)[0], "Server did not start"
            port_line = process.stdout.readline().strip()
            if not port_line:
                _, stderr = process.communicate(timeout=5)
                evidence.append({"phase": phase, "server_start_error": stderr})
                pytest.fail(f"HTTP server failed to start: {stderr}")
            port = int(port_line)
            evidence.append({"phase": phase, "process_id": process.pid, "port": port})
            if phase == "before restart":
                assert exchange(port, "PATCH", FULL) == (200, {"data": EXPECTED})
                assert exchange(port, "PATCH", {"current_semester_id": "semester-115-2"}) == (
                    200, {"data": dict(EXPECTED, current_semester_id="semester-115-2")})
                assert exchange(port, "PATCH", {"admission_year": "abc"})[0] == 422
                assert exchange(port, "PATCH", raw='{"admission_year":')[0] == 400
            assert exchange(port) == (200, {"data": dict(EXPECTED, current_semester_id="semester-115-2")})
        finally:
            process.terminate()
            process.communicate(timeout=10)


@pytest.mark.skip(reason="未執行：固定身分 baseline 無法提供兩位登入使用者隔離；合成資料保留測試不代表登入隔離")
def test_X10_authenticated_user_isolation():
    pass


def test_X11_missing_database_returns_json_500(tmp_path, evidence):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "missing" / "db.sqlite3")})
    for method in ("GET", "PATCH"):
        response = app.test_client().open(URL, method=method, json=FULL if method == "PATCH" else None)
        evidence.append({"precondition": "Database parent directory does not exist; init-db not run",
                         "method": method, "input": FULL if method == "PATCH" else None,
                         "actual_status": response.status_code, "actual_body": response.json})
        assert response.status_code == 500
        assert response.json["error"]["code"] == "INTERNAL_ERROR"


def test_X12_inconsistent_stored_rule_returns_500(app, api, evidence):
    api("PATCH", FULL)
    with app.app_context():
        get_db().execute("UPDATE user_profiles SET rule_set_id = NULL")
        get_db().commit()
    evidence.append({"fault_injection": "Remove stored rule_set_id despite matching department/year"})
    api(status=500)
