"""Acceptance cases from the semester/course/offering contract, plus boundary regressions."""

import hashlib
import json
from pathlib import Path
import select
import sqlite3
import subprocess
import sys
import os
from urllib.request import urlopen

import pytest

from app import create_app
from app.db import init_db

BASE = "/api/v1/"
RULE = "rules-csie-115-v1"
COURSE = "course-demo-001"
SEMESTER = "semester-115-1"
URLS = ["semesters", "courses", "courses/" + COURSE, "course-offerings?semester_id=" + SEMESTER]


@pytest.fixture
def catalog_app(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "catalog.sqlite3")})
    with app.app_context():
        init_db()
    return app


@pytest.fixture
def mutate(catalog_app, evidence):
    def run(sql, args=(), foreign_keys=True):
        with sqlite3.connect(catalog_app.config["DATABASE"]) as db:
            db.execute(f"PRAGMA foreign_keys = {'ON' if foreign_keys else 'OFF'}")
            db.execute(sql, args)
        evidence.append({"setup_sql": sql, "parameters": args, "foreign_keys": foreign_keys})
    return run


@pytest.fixture
def api(catalog_app, evidence):
    def get(path, query=None, status=200, stop="L4"):
        db_path = Path(catalog_app.config["DATABASE"])
        before = hashlib.sha256(db_path.read_bytes()).hexdigest()
        trace = []
        from app.db import get_db
        with catalog_app.app_context():
            get_db().set_trace_callback(trace.append)
            response = catalog_app.test_client().get(BASE + path, query_string=query)
        after = hashlib.sha256(db_path.read_bytes()).hexdigest()
        evidence.append({"transport": "Flask test client", "method": "GET", "path": BASE + path,
                         "query": query, "expected_status": status, "expected_stop": stop,
                         "actual_status": response.status_code, "actual_body": response.json,
                         "database_sha256_before": before, "database_sha256_after": after,
                         "sql_trace": trace})
        assert before == after, "Read endpoint modified the database"
        assert response.status_code == status
        assert not any(s.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "REPLACE")) for s in trace)
        if stop == "L1":
            assert trace == []
        if status != 200:
            assert set(response.json) == {"error"}
            assert set(response.json["error"]) == {"code", "message", "fields"}
            if status in (404, 500):
                assert response.json["error"]["fields"] == []
        elif isinstance(response.json["data"], list):
            assert response.json["meta"]["count"] == len(response.json["data"])
        return response.json
    return get


def test_S01_all_semesters_sorted(api):
    rows = api("semesters")["data"]
    assert [r["semester_id"] for r in rows] == ["semester-115-1", "semester-115-2", "semester-114-2"]
    assert rows[0] == {"semester_id": SEMESTER, "academic_year": 115, "term": "1",
                       "starts_on": "2026-09-01", "ends_on": "2027-01-31", "timezone": "Asia/Taipei"}


def test_S02_filter_year(api):
    rows = api("semesters", {"academic_year": "115"})["data"]
    assert len(rows) == 2 and all(r["academic_year"] == 115 for r in rows)


@pytest.mark.parametrize("year", ["abc", "0", "-1", "115.0", "true", "", " 115", "+115"])
def test_S03_invalid_year(api, year):
    body = api("semesters", {"academic_year": year}, 422, "L1")
    assert body["error"]["fields"][0]["field"] == "academic_year"


@pytest.mark.parametrize("year", ["999", "9" * 100])
def test_S04_year_without_data(api, year):
    assert api("semesters", {"academic_year": year}) == {"data": [], "meta": {"count": 0}}


@pytest.mark.parametrize("value", ["2020-01-01", "2027-02-30", "2027-1-31"])
def test_S05_invalid_stored_dates(api, mutate, value):
    mutate("UPDATE semesters SET ends_on=? WHERE id=?", (value, SEMESTER))
    api("semesters", status=500)


def test_C01_all_courses_without_implicit_rule(api, catalog_app):
    client = catalog_app.test_client()
    assert client.patch(BASE + "me", json={"department_id": "dept-csie", "admission_year": 115,
                                          "current_semester_id": SEMESTER}).status_code == 200
    rows = api("courses")["data"]
    assert len(rows) == 6 and all(r["classification"] is None for r in rows)
    assert [r["course_id"] for r in rows] == sorted(r["course_id"] for r in rows)
    assert rows[0]["course_code"] is None
    assert rows[2]["credits"] == 2.5 and rows[4]["credits"] == 0
    assert rows[5]["offering_department_id"] is None


@pytest.mark.parametrize("q,ids", [("資料", [COURSE, "course-demo-004"]),
                                   (" demo-prog ", ["course-demo-002"])])
def test_C02_search_name_or_code(api, q, ids):
    assert [r["course_id"] for r in api("courses", {"q": q})["data"]] == ids


@pytest.mark.parametrize("q", ["不存在", "%", "_", "' OR 1=1 --"])
def test_C03_no_matches_literal_search(api, q):
    assert api("courses", {"q": q}) == {"data": [], "meta": {"count": 0}}


@pytest.mark.parametrize("q", ["", "  ", "字" * 101])
def test_C04_invalid_search(api, q):
    api("courses", {"q": q}, 422, "L1")


def test_C05_invalid_department(api):
    body = api("courses", {"department_id": "unknown"}, 422, "L2")
    assert body["error"]["fields"] == [{"field": "department_id", "reason": "系所不存在"}]


@pytest.mark.parametrize("path", ["courses", "courses/" + COURSE])
def test_C06_invalid_rule(api, path):
    body = api(path, {"rule_set_id": "unknown"}, 422, "L2")
    assert body["error"]["fields"] == [{"field": "rule_set_id", "reason": "規則不存在"}]


def test_C07_unclassified_retained(api):
    rows = api("courses", {"rule_set_id": RULE})["data"]
    assert len(rows) == 6
    assert rows[2]["classification"] == {"rule_set_id": RULE, "credit_category": None, "status": "unclassified"}


def test_C08_detail(api):
    row = api("courses/" + COURSE, {"rule_set_id": RULE})["data"]
    assert row == {"course_id": COURSE, "course_code": None, "name": "資料結構", "credits": 3,
                   "offering_department_id": "dept-csie", "classification": {"rule_set_id": RULE,
                   "credit_category": "department_required", "status": "classified"},
                   "prerequisites": {"status": "unknown", "mode": None, "course_ids": None, "source": None}}


def test_C09_missing_course(api):
    assert api("courses/unknown", status=404, stop="L3")["error"]["code"] == "COURSE_NOT_FOUND"


def test_C10_unknown_prerequisites(api):
    assert api("courses/" + COURSE)["data"]["prerequisites"] == {
        "status": "unknown", "mode": None, "course_ids": None, "source": None}


def test_C11_confirmed_no_prerequisites(api):
    p = api("courses/course-demo-002")["data"]["prerequisites"]
    assert p["status"] == "none" and p["course_ids"] == [] and p["mode"] is None
    assert "測試" in p["source"]


@pytest.mark.parametrize("course,mode", [("course-demo-004", "all"), ("course-demo-005", "any")])
def test_C12_known_prerequisites(api, course, mode):
    p = api("courses/" + course)["data"]["prerequisites"]
    assert p["status"] == "known" and p["mode"] == mode and "測試" in p["source"]
    assert p["course_ids"] == ["course-demo-002", "course-demo-003"]
    for course_id in p["course_ids"]:
        api("courses/" + course_id)


@pytest.mark.parametrize("rule", [None, RULE, "rules-demo-114-v1"])
def test_C13_list_detail_consistency(api, rule):
    query = {"rule_set_id": rule} if rule else None
    for row in api("courses", query)["data"]:
        detail = api("courses/" + row["course_id"], query)["data"]
        assert {k: v for k, v in detail.items() if k != "prerequisites"} == row


def test_C14_rule_specific_classification(api):
    for rule, category in [(RULE, "department_required"), ("rules-demo-114-v1", "free_elective")]:
        assert api("courses/" + COURSE, {"rule_set_id": rule})["data"]["classification"] == {
            "rule_set_id": rule, "credit_category": category, "status": "classified"}


def test_O01_offerings_for_semester(api):
    rows = api("course-offerings", {"semester_id": SEMESTER})["data"]
    assert len(rows) == 4 and all(r["semester_id"] == SEMESTER for r in rows)
    assert [(r["course_id"], r["offering_id"]) for r in rows] == sorted((r["course_id"], r["offering_id"]) for r in rows)
    for row in rows:
        assert row["course_name"] == api("courses/" + row["course_id"])["data"]["name"]
        meetings = row["class_meetings"]
        assert [(m["weekday"], m["start_time"]) for m in meetings] == sorted((m["weekday"], m["start_time"]) for m in meetings)


def test_O02_missing_semester(api):
    assert api("course-offerings", status=422, stop="L1")["error"]["fields"] == [
        {"field": "semester_id", "reason": "此欄位為必填"}]


def test_O03_invalid_semester(api):
    api("course-offerings", {"semester_id": "unknown"}, 422, "L2")


def test_O04_semester_without_offerings(api):
    assert api("course-offerings", {"semester_id": "semester-115-2"}) == {"data": [], "meta": {"count": 0}}


def test_O05_invalid_course(api):
    api("course-offerings", {"semester_id": SEMESTER, "course_id": "unknown"}, 422, "L2")


def test_O06_multiple_sections(api):
    rows = api("course-offerings", {"semester_id": SEMESTER, "course_id": COURSE})["data"]
    assert [r["section_name"] for r in rows] == ["A班", "B班"]
    assert len(set(r["offering_id"] for r in rows)) == 2


def test_O07_multiple_meetings_count_offerings(api):
    body = api("course-offerings", {"semester_id": SEMESTER, "course_id": "course-demo-004"})
    assert body["meta"]["count"] == 1 and len(body["data"][0]["class_meetings"]) == 2
    assert [m["start_time"] for m in body["data"][0]["class_meetings"]] == ["09:00", "13:00"]


def test_O08_unknown_location(api):
    row = api("course-offerings", {"semester_id": SEMESTER, "course_id": COURSE})["data"][1]
    assert row["schedule_status"] == "scheduled"
    assert row["class_meetings"][0] == {"meeting_id": "meeting-demo-003", "weekday": 2,
                                       "start_time": "13:00", "end_time": "15:00", "campus_id": None, "location": None}


def test_O09_unknown_schedule(api):
    row = api("course-offerings", {"semester_id": SEMESTER, "course_id": "course-demo-002"})["data"][0]
    assert row["schedule_status"] == "unknown" and row["class_meetings"] == [] and row["section_name"] is None


@pytest.mark.parametrize("column,value", [("weekday", 8), ("weekday", 1.5), ("end_time", "08:00"),
                                          ("end_time", "09:00"), ("start_time", "25:00")])
def test_O10_invalid_stored_meeting(api, mutate, column, value):
    mutate(f"UPDATE class_meetings SET {column}=? WHERE meeting_id='meeting-demo-001'", (value,))
    api("course-offerings", {"semester_id": SEMESTER}, 500)


@pytest.mark.parametrize("path", URLS)
def test_X01_unknown_query(api, path):
    query = {"typo": "value"}
    if path.startswith("course-offerings"):
        query["semester_id"] = SEMESTER
    body = api(path.split("?")[0], query, 422, "L1")
    assert body["error"]["fields"][0]["field"] == "typo"


@pytest.mark.parametrize("path", URLS + ["courses?department_id=dept-csie"])
def test_X02_database_read_failure(api, monkeypatch, evidence, path):
    from app import catalog
    original = catalog.get_db
    def fail_reads():
        db = original()
        db.set_authorizer(lambda action, *_: sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_READ else sqlite3.SQLITE_OK)
        return db
    monkeypatch.setattr(catalog, "get_db", fail_reads)
    evidence.append({"fault_injection": "SQLite authorizer denies SQLITE_READ; connection and transaction setup still succeed"})
    body = api(path, status=500, stop="L2" if "semester_id" in path or "department_id" in path else "L3")
    assert body == {"error": {"code": "INTERNAL_ERROR", "message": "無法讀取查詢資料", "fields": []}}


def test_E01_combined_filters(api):
    rows = api("courses", {"q": "資料", "department_id": "dept-csie", "rule_set_id": RULE})["data"]
    assert [r["course_id"] for r in rows] == [COURSE, "course-demo-004"]
    assert api("courses", {"q": "資料", "department_id": "dept-demo"})["data"] == []
    assert api("course-offerings", {"semester_id": SEMESTER, "course_id": "course-demo-006"})["data"] == []


@pytest.mark.parametrize("path,key", [("semesters", "academic_year"), ("courses", "q"),
                                      ("courses/" + COURSE, "rule_set_id"), ("course-offerings", "semester_id")])
def test_E02_repeated_query_rejected(api, path, key):
    api(path, [(key, "115"), (key, "115")], 422, "L1")


@pytest.mark.parametrize("sql,path", [
    ("UPDATE courses SET credits=-1", "courses"),
    ("UPDATE courses SET name=''", "courses"),
    ("UPDATE courses SET offering_department_id='missing'", "courses"),
    ("UPDATE courses SET prerequisite_source=NULL WHERE course_id='course-demo-002'", "courses/course-demo-002"),
    ("DELETE FROM course_prerequisites WHERE course_id='course-demo-004'", "courses/course-demo-004"),
    ("UPDATE course_prerequisites SET prerequisite_id='missing' WHERE prerequisite_id='course-demo-002'", "courses/course-demo-004"),
    ("UPDATE course_classifications SET credit_category='invalid'", "courses?rule_set_id=" + RULE),
    ("UPDATE course_offerings SET schedule_status='unknown' WHERE offering_id='offering-demo-001'", URLS[3]),
    ("UPDATE course_offerings SET schedule_status='scheduled' WHERE offering_id='offering-demo-003'", URLS[3]),
    ("UPDATE class_meetings SET campus_id='missing'", URLS[3]),
    ("UPDATE course_offerings SET course_id='missing'", URLS[3]),
])
def test_E03_invalid_stored_contract(api, mutate, sql, path):
    mutate(sql, foreign_keys=False)
    api(path, status=500)


def test_E04_init_idempotent_preserves_changes(catalog_app, mutate, api, evidence):
    mutate("UPDATE courses SET name='保留自訂名稱' WHERE course_id=?", (COURSE,))
    client = catalog_app.test_client()
    before = client.patch(BASE + "me", json={"current_semester_id": SEMESTER}).json
    result = catalog_app.test_cli_runner().invoke(args=["init-db"])
    evidence.append({"command": "flask --app app:create_app init-db", "exit_code": result.exit_code, "output": result.output})
    assert result.exit_code == 0
    assert client.get(BASE + "me").json == before
    assert api("courses/" + COURSE)["data"]["name"] == "保留自訂名稱"


def test_E05_upgrade_original_profile_database(tmp_path, evidence):
    path = tmp_path / "legacy.sqlite3"
    # Snapshot of the /me schema at 88c2beb, independent of clone depth/Git availability.
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE departments (id TEXT PRIMARY KEY);
            CREATE TABLE admission_years (year INTEGER PRIMARY KEY);
            CREATE TABLE semesters (id TEXT PRIMARY KEY);
            CREATE TABLE rule_sets (
                id TEXT PRIMARY KEY,
                department_id TEXT NOT NULL REFERENCES departments(id),
                admission_year INTEGER NOT NULL REFERENCES admission_years(year),
                UNIQUE (department_id, admission_year));
            CREATE TABLE user_profiles (
                user_id TEXT PRIMARY KEY,
                department_id TEXT REFERENCES departments(id),
                admission_year INTEGER REFERENCES admission_years(year),
                rule_set_id TEXT REFERENCES rule_sets(id),
                current_semester_id TEXT REFERENCES semesters(id));
            INSERT INTO departments VALUES ('dept-csie'), ('dept-demo');
            INSERT INTO admission_years VALUES (114), (115);
            INSERT INTO semesters VALUES ('semester-115-1'), ('semester-115-2');
            INSERT INTO rule_sets VALUES ('rules-csie-115-v1', 'dept-csie', 115);
            INSERT INTO user_profiles(user_id) VALUES ('user-demo-001');
        """)
    app = create_app({"TESTING": True, "DATABASE": str(path)})
    client = app.test_client()
    before = client.patch(BASE + "me", json={"department_id": "dept-csie", "admission_year": 115,
                                          "current_semester_id": SEMESTER}).json
    result = app.test_cli_runner().invoke(args=["init-db"])
    assert result.exit_code == 0
    after = client.get(BASE + "me").json
    evidence.append({"legacy_schema_commit": "88c2beb", "init_output": result.output,
                     "profile_before": before, "profile_after": after})
    assert before == after
    assert client.get(BASE + "semesters").status_code == 200
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_E06_openapi(catalog_app, evidence):
    spec = catalog_app.test_client().get("/openapi.json").json
    paths = [BASE + "semesters", BASE + "courses", BASE + "courses/{course_id}", BASE + "course-offerings"]
    for path in paths:
        operation = spec["paths"][path]["get"]
        assert {"200", "422", "500"} <= operation["responses"].keys()
    assert "404" in spec["paths"][paths[2]]["get"]["responses"]
    required = spec["paths"][paths[3]]["get"]["parameters"]
    assert any(p["name"] == "semester_id" and p["required"] for p in required)
    evidence.append({"openapi_paths_checked": paths, "offering_query_parameters": required})


def test_E07_real_http(catalog_app, evidence):
    code = ("from app import create_app; from werkzeug.serving import make_server; "
            "s=make_server('127.0.0.1',0,create_app()); print(s.server_port,flush=True); s.serve_forever()")
    process = subprocess.Popen([sys.executable, "-u", "-c", code], cwd=Path(__file__).resolve().parents[1],
                               env=dict(os.environ, ME_DATABASE=catalog_app.config["DATABASE"]),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert select.select([process.stdout], [], [], 10)[0]
        line = process.stdout.readline().strip()
        if not line:
            _, stderr = process.communicate(timeout=5)
            pytest.fail(stderr)
        for path in URLS:
            url = f"http://127.0.0.1:{int(line)}{BASE}{path}"
            with urlopen(url, timeout=5) as response:
                body = json.load(response)
                evidence.append({"transport": "real HTTP", "url": url, "actual_status": response.status, "actual_body": body})
                assert response.status == 200 and "data" in body
                assert body == catalog_app.test_client().get(BASE + path).json
    finally:
        process.terminate()
        process.communicate(timeout=10)
