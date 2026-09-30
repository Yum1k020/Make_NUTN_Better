"""Contract acceptance tests: each recorded exchange includes phase and atomicity evidence."""

from copy import deepcopy
import hashlib
import json
import logging
import os
from pathlib import Path
import select
import sqlite3
import subprocess
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from app import create_app
from app.db import get_db, init_db

PREFIX = "/api/v1/"
COURSE, SEM = "course-demo-001", "semester-115-1"
RULE = "nutn-csie-115-mvp-v1"


def dt(time, date="2026-10-05"):
    return f"{date}T{time}:00+08:00"


def meeting(start="09:00", end="10:00", weekday=1):
    return {"weekday": weekday, "start_time": start, "end_time": end}


DATA = {
    "enrollments": {"course_id": COURSE, "semester_id": SEM, "enrollment_status": "finished", "passed": True, "grade": 80},
    "timetable-entries": {"course_id": COURSE, "semester_id": SEM, "meetings": [meeting(), meeting(weekday=3)]},
    "tasks": {"title": "資料結構作業", "type": "assignment", "due_date": "2026-10-09"},
    "personal-events": {"title": "行程", "starts_at": dt("20:00"), "ends_at": dt("21:00")},
    "study-plans": {"course_id": COURSE, "start_date": "2026-10-05", "exam_date": "2026-10-06",
                    "target_minutes": 180, "session_minutes": 60, "allowed_windows": [meeting("09:00", "12:00")]},
    "planned-courses": {"course_id": COURSE, "target_semester_id": SEM},
}
KEYS = dict(zip(DATA, ["enrollment_id", "entry_id", "task_id", "event_id", "plan_id", "planned_course_id"]))
PATCHES = {"enrollments": {"grade": 81}, "timetable-entries": {"section_name": "新班"},
           "tasks": {"completed": True}, "personal-events": {"title": "更新行程"},
           "study-plans": {"target_minutes": 240}, "planned-courses": {"target_semester_id": "semester-115-2"}}


@pytest.fixture
def planner_app(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "planner.sqlite3")})
    with app.app_context():
        init_db()
    return app


def snapshot(app):
    with sqlite3.connect(app.config["DATABASE"]) as db:
        rows = list(db.execute("SELECT kind,id,user_id,body,created_at,updated_at FROM planner_resources ORDER BY id"))
        lectures = list(db.execute("SELECT * FROM lecture_progress ORDER BY user_id"))
        digest = hashlib.sha256("\n".join(db.iterdump()).encode()).hexdigest()
    return {"logical_sha256": digest, "resources": rows, "lectures": lectures}


@pytest.fixture
def api(planner_app, evidence):
    def call(method, path, payload=None, status=200, raw=None, phase=None):
        before, trace, phases = snapshot(planner_app), [], []
        class Capture(logging.Handler):
            def emit(self, record):
                if hasattr(record, "planner_stage"):
                    phases.append({"stage": record.planner_stage, "status": record.planner_status})
        handler = Capture()
        previous_level = planner_app.logger.level
        planner_app.logger.setLevel(logging.INFO)
        planner_app.logger.addHandler(handler)
        try:
            with planner_app.app_context():
                get_db().set_trace_callback(trace.append)
                response = planner_app.test_client().open(PREFIX + path, method=method,
                    **({"data": raw, "content_type": "application/json"} if raw is not None else {"json": payload} if payload is not None else {}))
        finally:
            planner_app.logger.removeHandler(handler)
            planner_app.logger.setLevel(previous_level)
        after = snapshot(planner_app)
        actual = response.get_json(silent=True)
        evidence.append({"method": method, "path": PREFIX + path, "input": payload if raw is None else raw,
                         "expected_status": status, "actual_status": response.status_code, "actual_body": actual,
                         "observed_phases": phases, "sql_trace": trace,
                         "before": before, "after": after})
        assert response.status_code == status, actual
        if phase:
            assert phases[-1]["stage"] == phase
        if status >= 400 or method == "GET" or path.startswith("schedule/") or path.endswith("/generate") or path == "planned-courses/check":
            assert after == before, "Failure or preview changed stored data"
        if status == 204:
            assert response.data == b""
        elif status >= 400:
            assert {"code", "message", "fields"} <= actual["error"].keys()
        elif isinstance(actual.get("data"), list):
            assert actual["meta"]["count"] == len(actual["data"])
        return actual["data"] if actual and "data" in actual else actual
    return call


@pytest.fixture
def mutate(planner_app, evidence):
    def run(sql, params=()):
        with sqlite3.connect(planner_app.config["DATABASE"]) as db:
            db.execute(sql, params)
        evidence.append({"setup_sql": sql, "params": params})
    return run


def create(api, kind, **changes):
    return api("POST", kind, {**deepcopy(DATA[kind]), **changes}, 201)


def plan(api, **changes):
    return create(api, "study-plans", **changes)


def confirm(api, p, start="09:00", end="10:00"):
    return api("PUT", f"study-plans/{p['plan_id']}/sessions", {"plan_version": p["plan_version"],
        "sessions": [{"title": "複習", "starts_at": dt(start), "ends_at": dt(end)}]})


def select_rule(api):
    api("PATCH", "me", {"department_id": "dept-nutn-csie", "admission_year": 115, "current_semester_id": SEM})


@pytest.mark.parametrize("kind", DATA)
def test_X01_X02_X04_crud_roundtrip(api, kind):
    row = create(api, kind)
    path = kind + "/" + row[KEYS[kind]]
    assert api("GET", path) == row
    assert row in api("GET", kind)
    changed = api("PATCH", path, PATCHES[kind])
    for key, value in row.items():
        if key not in {*PATCHES[kind], "updated_at", "plan_version", "remaining_minutes"}:
            assert changed[key] == value
    api("DELETE", path, status=204)
    api("GET", path, status=404, phase="L3")
    assert api("GET", kind) == []


@pytest.mark.parametrize("kind", DATA)
@pytest.mark.parametrize("payload", [{}, {"user_id": "other"}, {"created_at": dt("10:00")}])
def test_X03_readonly_or_empty_patch(api, kind, payload):
    row = create(api, kind)
    api("PATCH", kind + "/" + row[KEYS[kind]], payload, 422, phase="L2")


@pytest.mark.parametrize("kind", DATA)
@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
def test_X05_missing_resource(api, kind, method):
    api(method, kind + "/unknown", PATCHES[kind] if method == "PATCH" else None, 404, phase="L3")


@pytest.mark.parametrize("kind", DATA)
def test_X06_baseline_owner_filter(api, kind, mutate):
    row = create(api, kind)
    mutate("INSERT INTO user_profiles(user_id) VALUES ('other')")
    mutate("UPDATE planner_resources SET user_id='other' WHERE id=?", (row[KEYS[kind]],))
    for method in ("GET", "PATCH", "DELETE"):
        api(method, kind + "/" + row[KEYS[kind]], PATCHES[kind] if method == "PATCH" else None, 404)
    assert api("GET", kind) == []


@pytest.mark.skip(reason="正式版 X06/X07 登入與雙使用者身分映射未實作；baseline 的 SQL 歸屬測試不等於正式登入驗收")
def test_X07_formal_authentication():
    pass


@pytest.mark.parametrize("kind", DATA)
def test_X08_storage_failure(api, kind, mutate):
    row = create(api, kind)
    mutate("CREATE TRIGGER fail_update AFTER UPDATE ON planner_resources BEGIN SELECT RAISE(FAIL, 'injected failure'); END")
    api("PATCH", kind + "/" + row[KEYS[kind]], PATCHES[kind], 500, phase="L5")
    assert api("GET", kind + "/" + row[KEYS[kind]]) == row


@pytest.mark.parametrize("kind", DATA)
def test_X09_X10_bad_json_and_user_id(api, kind):
    api("POST", kind, raw='{"bad":', status=400, phase="L2")
    api("POST", kind, {**DATA[kind], "user_id": "other"}, 422, phase="L2")


def test_E01_E02_E03_enrollment(api):
    select_rule(api)
    api("POST", "enrollments", {**DATA["enrollments"], "grade": 50}, 422, phase="L3")
    row = create(api, "enrollments")
    assert row["course_snapshot"]["credits"] == 3 and row["course_snapshot"]["version_basis"].startswith("sha256:")
    assert api("GET", "graduation-progress")["earned_credits"] == 3
    api("POST", "enrollments", DATA["enrollments"], 409, phase="L3")
    api("POST", "enrollments", {**DATA["enrollments"], "semester_id": "semester-115-2"}, 409)


def test_T01_E04_timetable_link(api):
    entry = create(api, "timetable-entries")
    enrollment = api("GET", "enrollments/" + entry["enrollment_id"])
    assert len(entry["meetings"]) == 2 and enrollment["enrollment_status"] == "in_progress"
    api("DELETE", "enrollments/" + enrollment["enrollment_id"], status=409)
    api("DELETE", "timetable-entries/" + entry["entry_id"], status=204)
    assert api("GET", "enrollments/" + enrollment["enrollment_id"])


def test_T02_bad_weekday(api):
    api("POST", "timetable-entries", {**DATA["timetable-entries"], "meetings": [meeting(weekday=8)]}, 422, phase="L2")
    assert api("GET", "enrollments") == []


def test_T03_conflicting_timetable(api):
    create(api, "personal-events", starts_at=dt("09:30"), ends_at=dt("10:30"))
    result = api("POST", "timetable-entries", DATA["timetable-entries"], 409, phase="L4")
    assert result["error"]["conflicts"][0]["source_type"] == "personal_event"
    assert api("GET", "enrollments") == []


def test_T04_link_write_rollback(api, mutate):
    mutate("CREATE TRIGGER fail_entry AFTER INSERT ON planner_resources WHEN NEW.kind='timetable-entries' BEGIN SELECT RAISE(FAIL, 'entry failure'); END")
    api("POST", "timetable-entries", DATA["timetable-entries"], 500, phase="L5")
    assert api("GET", "enrollments") == [] and api("GET", "timetable-entries") == []


def test_CA01_calendar_dedup_and_deadlines(api):
    entry = create(api, "timetable-entries")
    create(api, "personal-events")
    create(api, "tasks")
    p = plan(api, allowed_windows=[meeting("11:00", "12:00")])
    confirm(api, p, "11:00", "12:00")
    result = api("GET", "calendar?from=2026-10-05&to=2026-10-11")
    assert len(result["events"]) == 4 and len(result["task_deadlines"]) == 1
    assert {e["source_type"] for e in result["events"]} == {"class", "personal_event", "study_session"}
    assert len({e["event_key"] for e in result["events"]}) == 4
    assert all(entry["entry_id"] in e["source_id"] for e in result["events"] if e["source_type"] == "class")


@pytest.mark.parametrize("range", ["from=2026-10-06&to=2026-10-05", "from=2026-10-01&to=2026-11-01"])
def test_CA02_invalid_calendar_range(api, range):
    api("GET", "calendar?" + range, status=422, phase="L2")


def test_CA03_outside_semester(api):
    create(api, "timetable-entries")
    assert api("GET", "calendar?from=2026-08-03&to=2026-08-09")["events"] == []


def test_TA01_TA02_TA03_task(api):
    t = create(api, "tasks", due_date="2026-10-05")
    assert t["due_time"] is None and t["completed"] is False
    assert api("GET", "calendar?from=2026-10-05&to=2026-10-05")["events"] == []
    updated = api("PATCH", "tasks/" + t["task_id"], {"completed": True})
    assert updated["completed"] and updated["due_time"] is None
    api("POST", "tasks", {**DATA["tasks"], "title": "  "}, 422, phase="L2")


def test_PE01_PE02_cross_day(api):
    row = create(api, "personal-events", starts_at=dt("23:00"), ends_at=dt("01:00", "2026-10-06"))
    for d in ("2026-10-05", "2026-10-06"):
        events = api("GET", f"calendar?from={d}&to={d}")["events"]
        assert len(events) == 1 and events[0]["starts_at"] == row["starts_at"]
    api("POST", "personal-events", {**DATA["personal-events"], "ends_at": dt("19:00")}, 422)


def test_PE03_conflict_with_study(api):
    p = plan(api)
    confirm(api, p)
    error = api("POST", "personal-events", {**DATA["personal-events"], "starts_at": dt("09:30"), "ends_at": dt("10:30")}, 409)
    assert error["error"]["conflicts"][0]["source_type"] == "study_session"


def test_CF01_CF02_overlap_and_boundary(api):
    create(api, "timetable-entries")
    result = api("POST", "schedule/conflicts", {"starts_at": dt("09:30"), "ends_at": dt("10:30")})
    assert result["has_conflict"] and result["check_complete"]
    assert result["conflicts"][0]["overlap_starts_at"] == dt("09:30")
    assert result["conflicts"][0]["overlap_ends_at"] == dt("10:00")
    assert not api("POST", "schedule/conflicts", {"starts_at": dt("10:00"), "ends_at": dt("11:00")})["has_conflict"]


def test_CF03_GE03_unknown_class(api):
    api("POST", "timetable-entries", {"semester_id": SEM, "course_id": "course-demo-002", "offering_id": "offering-demo-003"}, 201)
    result = api("POST", "schedule/conflicts", {"starts_at": dt("09:00"), "ends_at": dt("10:00")})
    assert not result["check_complete"] and result["warnings"]
    p = plan(api)
    assert api("POST", f"study-plans/{p['plan_id']}/generate", status=409)["error"]["code"] == "SCHEDULE_INCOMPLETE"


def test_AV01_AV02_AV03_availability(api):
    create(api, "personal-events", starts_at=dt("10:00"), ends_at=dt("11:00"))
    p = {"from": dt("09:00"), "to": dt("12:00"), "allowed_windows": [{"starts_at": dt("09:00"), "ends_at": dt("12:00")}]}
    result = api("POST", "schedule/availability", p)
    assert result["total_free_minutes"] == 120
    assert [(s["starts_at"], s["ends_at"]) for s in result["free_slots"]] == [(dt("09:00"), dt("10:00")), (dt("11:00"), dt("12:00"))]
    p["allowed_windows"].append({"starts_at": dt("10:00"), "ends_at": dt("12:00")})
    assert api("POST", "schedule/availability", p)["total_free_minutes"] == 120
    p.update(allowed_windows=[{"starts_at": dt("10:00"), "ends_at": dt("11:00")}])
    assert api("POST", "schedule/availability", p)["free_slots"] == []


def test_SP01_SP02_SP03_plan_validation(api):
    p = plan(api)
    assert p["scheduled_minutes"] == 0 and p["plan_version"] == 1
    for change in ({"target_minutes": 0}, {"exam_date": "2026-10-05"}, {"target_minutes": True}):
        api("POST", "study-plans", {**DATA["study-plans"], **change}, 422)
    confirm(api, p)
    api("PATCH", "study-plans/" + p["plan_id"], {"start_date": "2026-10-06", "exam_date": "2026-10-07"}, 409)


def test_GE01_GE02_generation(api):
    p = plan(api)
    result = api("POST", f"study-plans/{p['plan_id']}/generate")
    assert result["scheduled_minutes"] == 180 and result["remaining_minutes"] == 0 and result["generation_status"] == "complete"
    assert api("GET", f"study-plans/{p['plan_id']}/sessions")["sessions"] == []
    create(api, "personal-events", starts_at=dt("10:00"), ends_at=dt("11:00"))
    result = api("POST", f"study-plans/{p['plan_id']}/generate")
    assert result["scheduled_minutes"] == 120 and result["remaining_minutes"] == 60 and result["generation_status"] == "partial"


@pytest.mark.skip(reason="GE04：baseline 不接外部 AI；502 驗收未執行")
def test_GE04_future_ai():
    pass


def test_SS01_SS02_SS03_recheck_and_version(api):
    p = plan(api)
    old = confirm(api, p)
    assert old["plan_version"] == 2
    generated = api("POST", f"study-plans/{p['plan_id']}/generate")
    create(api, "personal-events", starts_at=dt("10:00"), ends_at=dt("11:00"))
    path = f"study-plans/{p['plan_id']}/sessions"
    api("PUT", path, {"plan_version": 2, "sessions": generated["candidates"]}, 409)
    api("PUT", path, {"plan_version": 1, "sessions": []}, 409)
    assert api("GET", path) == old


def test_SS04_SS05_session_adjustment(api):
    p = plan(api)
    saved = confirm(api, p)
    session = saved["sessions"][0]
    create(api, "personal-events", starts_at=dt("10:00"), ends_at=dt("11:00"))
    api("PATCH", "study-sessions/" + session["session_id"], {"plan_version": 2, "starts_at": dt("10:00"), "ends_at": dt("11:00")}, 409)
    api("DELETE", "study-sessions/" + session["session_id"] + "?plan_version=2", status=204)
    current = api("GET", f"study-plans/{p['plan_id']}/sessions")
    assert current["plan_version"] == 3 and current["scheduled_minutes"] == 0


def test_PC01_PC02_planning_does_not_earn_credits(api):
    select_rule(api)
    create(api, "planned-courses")
    assert api("GET", "graduation-progress")["earned_credits"] == 0
    api("POST", "planned-courses", DATA["planned-courses"], 409)


def test_CK01_CK02_planning_check(api):
    result = api("POST", "planned-courses/check", {"target_semester_id": SEM,
        "items": [{"course_id": "course-demo-004"}, {"course_id": "course-demo-004"}]})
    assert result["overall_status"] == "issues_found" and result["duplicate_courses"] == ["course-demo-004"]
    assert result["prerequisite_checks"][0]["status"] == "not_met"
    result = api("POST", "planned-courses/check", {"target_semester_id": SEM, "items": [{"course_id": COURSE}]})
    assert result["overall_status"] == "needs_confirmation" and not result["schedule_check_complete"]


def test_GR01_GR02_PR01_PR02_rules(api):
    rule = api("GET", "graduation-rules/" + RULE)
    assert rule["total_credits_required"] == 133 and rule["sources"] and rule["verification_scope"]
    assert rule["unmapped_required_courses"] and rule["required_course_ids"] == []
    api("GET", "graduation-rules/unknown", status=404)
    ps = api("GET", "programs?rule_set_id=" + RULE)
    assert len(ps) == 3 and all(p["minimum_passed_courses"] == 3 and p["data_status"] == "needs_confirmation" for p in ps)
    api("GET", "programs", status=422, phase="L2")


def test_LP01_LP02_LP03_lectures(api):
    assert api("GET", "lecture-progress") == {"user_id": "user-demo-001", "professional_count": None, "general_count": None, "updated_at": None}
    saved = api("PUT", "lecture-progress", {"professional_count": 10, "general_count": 11})
    for value in (-1, 1.5, True):
        api("PUT", "lecture-progress", {"professional_count": 20, "general_count": value}, 422, phase="L2")
    assert api("GET", "lecture-progress") == saved


def test_GP01_GP02_GP03_GP04_progress(api, mutate):
    select_rule(api)
    mutate("UPDATE courses SET credits=100 WHERE course_id=?", (COURSE,))
    create(api, "enrollments")
    create(api, "enrollments", course_id="course-demo-002", enrollment_status="in_progress", passed=None, grade=None)
    create(api, "planned-courses", course_id="course-demo-003")
    result = api("GET", "graduation-progress")
    total = next(c for c in result["checks"] if c["check_id"] == "total_credits")
    assert total["actual_value"] == 100 and total["remaining_value"] == 33
    assert any(c["status"] == "needs_confirmation" for c in result["checks"])
    api("PUT", "lecture-progress", {"professional_count": 10, "general_count": 11})
    checks = {c["check_id"]: c for c in api("GET", "graduation-progress")["checks"]}
    assert checks["lecture_professional"]["remaining_value"] == 0 and checks["lecture_general"]["remaining_value"] == 1


def test_GP05_allocation_once(api, mutate):
    select_rule(api)
    mutate("UPDATE courses SET credits=24 WHERE course_id=?", (COURSE,))
    mutate("INSERT INTO course_classifications VALUES (?,?,?)", (COURSE, RULE, "department_elective"))
    create(api, "enrollments")
    result = api("GET", "graduation-progress")
    assert result["earned_credits"] == 24
    parts = result["credit_allocation"][0]["allocations"]
    assert parts == [{"category": "department_elective", "credits": 12}, {"category": "free_elective", "credits": 12}]
    assert sum(p["credits"] for p in parts) == 24


def test_DB01_DB02_dashboard(api):
    select_rule(api)
    create(api, "tasks", due_date="2026-10-05")
    p = plan(api)
    confirm(api, p)
    result = api("GET", "dashboard?date=2026-10-05")
    assert result["today_task_summary"] == {"total": 1, "completed": 0}
    assert result["week_study_summary"] == {"scheduled_minutes": 60, "session_count": 1}
    assert result["graduation_summary"]["earned_credits"] == api("GET", "graduation-progress")["earned_credits"]
    api("GET", "dashboard?date=bad", status=422, phase="L2")


def test_MP01_MP02_maps(api, planner_app, evidence):
    maps = api("GET", "campus-maps")
    assert len(maps) == 3 and all(m["alt_text"] for m in maps)
    for m in maps:
        response = planner_app.test_client().get(m["image_url"])
        evidence.append({"image_url": m["image_url"], "actual_status": response.status_code,
                         "content_type": response.content_type, "bytes": len(response.data)})
        assert response.status_code == 200 and response.data.startswith(b"\x89PNG")
    assert api("GET", "campus-maps?campus_id=campus-demo") == []


def test_B01_task_event_reference_cleanup(api):
    event = create(api, "personal-events")
    task = create(api, "tasks", event_id=event["event_id"])
    api("DELETE", "personal-events/" + event["event_id"], status=204)
    assert api("GET", "tasks/" + task["task_id"])["event_id"] is None
    other = create(api, "personal-events")
    task2 = create(api, "tasks", event_id=other["event_id"])
    api("DELETE", "tasks/" + task2["task_id"], status=204)
    assert api("GET", "personal-events/" + other["event_id"])


def test_B02_exam_links_guarded(api):
    task = create(api, "tasks", type="exam", due_date="2026-10-06", course_id=COURSE)
    p = plan(api, exam_task_id=task["task_id"])
    api("PATCH", "tasks/" + task["task_id"], {"due_date": "2026-10-07"}, 409)
    api("PATCH", "tasks/" + task["task_id"], {"type": "todo"}, 409)
    api("DELETE", "tasks/" + task["task_id"], status=409)
    api("PATCH", "study-plans/" + p["plan_id"], {"exam_task_id": None})
    api("DELETE", "tasks/" + task["task_id"], status=204)


def test_B03_plan_sessions_isolation_tail_and_clear(api):
    p = plan(api, target_minutes=90)
    generated = api("POST", f"study-plans/{p['plan_id']}/generate")
    assert [s["ends_at"] for s in generated["candidates"]] == [dt("10:00"), dt("10:30")]
    saved = api("PUT", f"study-plans/{p['plan_id']}/sessions", {"plan_version": 1, "sessions": generated["candidates"]})
    p2 = plan(api)
    other = confirm(api, p2, "11:00", "12:00")
    newer = api("POST", f"study-plans/{p['plan_id']}/generate")
    assert newer["scheduled_minutes"] == 90  # Ignore own sessions; keep other plan occupied.
    api("PUT", f"study-plans/{p['plan_id']}/sessions", {"plan_version": 2, "sessions": []})
    assert api("GET", f"study-plans/{p2['plan_id']}/sessions") == other
    api("DELETE", "study-plans/" + p2["plan_id"], status=204)
    api("PATCH", "study-sessions/" + other["sessions"][0]["session_id"], {"plan_version": 2, "title": "missing"}, 404)


def test_B04_put_rollback_after_delete(api, mutate):
    p = plan(api)
    before = confirm(api, p)
    mutate("CREATE TRIGGER fail_session AFTER INSERT ON planner_resources WHEN NEW.kind='study-sessions' BEGIN SELECT RAISE(FAIL, 'session failure'); END")
    api("PUT", f"study-plans/{p['plan_id']}/sessions", {"plan_version": 2,
        "sessions": [{"title": "later", "starts_at": dt("10:00"), "ends_at": dt("11:00")}]}, 500, phase="L5")
    assert api("GET", f"study-plans/{p['plan_id']}/sessions") == before


@pytest.mark.parametrize("sessions", [
    [{"title": "outside", "starts_at": dt("08:00"), "ends_at": dt("09:00")}],
    [{"title": "long", "starts_at": dt("09:00"), "ends_at": dt("11:00")}],
    [{"title": "short1", "starts_at": dt("09:00"), "ends_at": dt("09:30")},
     {"title": "short2", "starts_at": dt("10:00"), "ends_at": dt("10:30")}],
])
def test_B05_invalid_session_sets(api, sessions):
    p = plan(api)
    api("PUT", f"study-plans/{p['plan_id']}/sessions", {"plan_version": 1, "sessions": sessions}, 422)


def test_B06_exclusion_ownership_and_self_edit(api, mutate):
    event = create(api, "personal-events")
    result = api("POST", "schedule/conflicts", {"starts_at": event["starts_at"], "ends_at": event["ends_at"],
        "exclude_source": {"source_type": "personal_event", "source_id": event["event_id"]}})
    assert not result["has_conflict"]
    api("PATCH", "personal-events/" + event["event_id"], {"title": "self-edit"})
    mutate("INSERT INTO user_profiles(user_id) VALUES ('other')")
    mutate("UPDATE planner_resources SET user_id='other' WHERE id=?", (event["event_id"],))
    api("POST", "schedule/conflicts", {"starts_at": event["starts_at"], "ends_at": event["ends_at"],
        "exclude_source": {"source_type": "personal_event", "source_id": event["event_id"]}}, 404)


def test_B07_enrollment_calendar_and_manual_override(api):
    enrollment = create(api, "enrollments", offering_id="offering-demo-001")
    before = api("GET", "calendar?from=2026-10-05&to=2026-10-11")
    assert len(before["events"]) == 2
    entry = create(api, "timetable-entries", meetings=[meeting("14:00", "15:00")])
    after = api("GET", "calendar?from=2026-10-05&to=2026-10-11")
    assert len(after["events"]) == 1 and after["events"][0]["starts_at"] == dt("14:00")
    assert entry["enrollment_id"] == enrollment["enrollment_id"]
    api("PATCH", "enrollments/" + enrollment["enrollment_id"], {"course_id": "course-demo-002", "offering_id": None}, 409)


def test_B08_catalog_entry_and_mismatched_offering(api):
    api("POST", "timetable-entries", {"course_id": COURSE, "semester_id": SEM, "offering_id": "offering-demo-001", "meetings": [meeting()]}, 422)
    row = api("POST", "timetable-entries", {"course_id": COURSE, "semester_id": SEM, "offering_id": "offering-demo-001"}, 201)
    assert row["source_type"] == "catalog" and row["section_name"] == "A班"
    api("POST", "planned-courses", {**DATA["planned-courses"], "offering_id": "offering-demo-003"}, 422)


def test_B09_task_filter_order_null_and_partial_dates(api):
    late = create(api, "tasks", due_time="12:00")
    no_time = create(api, "tasks")
    early = create(api, "tasks", due_time="09:00", completed=True)
    assert [t["task_id"] for t in api("GET", "tasks")] == [early["task_id"], late["task_id"], no_time["task_id"]]
    assert len(api("GET", "tasks?completed=false&from=2026-10-09&to=2026-10-09")) == 2
    api("GET", "tasks?completed=1", status=422)
    api("GET", "tasks?from=2026-10-10&to=2026-10-09", status=422)


def test_B10_timezone_and_read_only_preview(api):
    create(api, "personal-events", starts_at="2026-10-05T01:00:00Z", ends_at="2026-10-05T02:00:00Z")
    assert api("POST", "schedule/conflicts", {"starts_at": dt("09:00"), "ends_at": dt("10:00")})["has_conflict"]
    api("POST", "personal-events", {**DATA["personal-events"], "starts_at": "2026-10-05T20:00:00"}, 422)


def test_B11_missing_rule_dashboard_no_fake_numbers(api):
    g = api("GET", "graduation-progress")
    assert g["overall_status"] == "needs_confirmation" and g["earned_credits"] is None
    d = api("GET", "dashboard?date=2026-10-05")
    assert d["graduation_summary"]["earned_credits"] is None


def test_B12_snapshot_immutable_and_invalid_output(api, mutate):
    enrollment = create(api, "enrollments")
    mutate("UPDATE courses SET credits=9, name='Changed' WHERE course_id=?", (COURSE,))
    updated = api("PATCH", "enrollments/" + enrollment["enrollment_id"], {"grade": 90})
    assert updated["course_snapshot"] == enrollment["course_snapshot"]
    task = create(api, "tasks")
    mutate("UPDATE planner_resources SET body=json_remove(body,'$.completed') WHERE id=?", (task["task_id"],))
    api("GET", "tasks/" + task["task_id"], status=500)


@pytest.mark.parametrize("kind", DATA)
def test_B13_unknown_query_all_crud(api, kind):
    api("GET", kind + "?typo=1", status=422, phase="L2")


def test_B14_sql_read_error_is_500(api, monkeypatch):
    from app import planner
    original = planner.get_db
    def fail():
        db = original()
        db.set_authorizer(lambda action, *_: sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_READ else sqlite3.SQLITE_OK)
        return db
    monkeypatch.setattr(planner, "get_db", fail)
    api("GET", "graduation-progress", status=500)


def test_B15_openapi_paths(planner_app, evidence):
    spec = planner_app.test_client().get("/openapi.json").json
    for kind in DATA:
        assert {"get", "post"} <= spec["paths"][PREFIX + kind].keys()
    assert "put" in spec["paths"][PREFIX + "study-plans/{plan_id}/sessions"]
    task_input = spec["paths"][PREFIX + "tasks"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    assert task_input["additionalProperties"] is False and "due_date" in task_input["required"]
    assert "201" in spec["paths"][PREFIX + "tasks"]["post"]["responses"]
    evidence.append({"openapi_paths": list(spec["paths"])})


def test_B16_week_boundary_study_minutes(api, mutate):
    # Cross-week persisted session fixture: dashboard clips rather than attributing full duration.
    p = plan(api)
    saved = confirm(api, p)
    s = saved["sessions"][0]
    mutate("UPDATE planner_resources SET body=json_set(body,'$.starts_at',?,'$.ends_at',?) WHERE id=?",
           (dt("23:30", "2026-10-04"), dt("00:30"), s["session_id"]))
    result = api("GET", "dashboard?date=2026-10-05")
    assert result["week_study_summary"] == {"session_count": 1, "scheduled_minutes": 30}


def test_B17_lecture_storage_rollback(api, mutate):
    before = api("PUT", "lecture-progress", {"professional_count": 1, "general_count": 2})
    mutate("CREATE TRIGGER fail_lecture AFTER UPDATE ON lecture_progress BEGIN SELECT RAISE(FAIL, 'failure'); END")
    api("PUT", "lecture-progress", {"professional_count": 10, "general_count": 12}, 500, phase="L5")
    assert api("GET", "lecture-progress") == before


def test_B18_init_preserves_data_and_rule_version(api, planner_app, mutate, evidence):
    row = create(api, "tasks")
    saved = snapshot(planner_app)
    result = planner_app.test_cli_runner().invoke(args=["init-db"])
    evidence.append({"init_exit": result.exit_code, "init_output": result.output})
    assert result.exit_code == 0 and snapshot(planner_app) == saved
    assert api("GET", "tasks/" + row["task_id"]) == row
    mutate("UPDATE graduation_rule_documents SET digest='changed'")
    result = planner_app.test_cli_runner().invoke(args=["init-db"])
    evidence.append({"changed_rule_init_exit": result.exit_code, "error": str(result.exception)})
    assert result.exit_code != 0  # Does not replace an existing version with changed content.


def test_B19_real_http_and_restart(planner_app, evidence):
    code = ("from app import create_app; from werkzeug.serving import make_server; "
            "s=make_server('127.0.0.1',0,create_app()); print(s.server_port,flush=True); s.serve_forever()")
    task_id = None
    for phase in ("create", "restart"):
        proc = subprocess.Popen([sys.executable, "-u", "-c", code], cwd=Path(__file__).resolve().parents[1],
            env=dict(os.environ, ME_DATABASE=planner_app.config["DATABASE"]), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            assert select.select([proc.stdout], [], [], 10)[0]
            port = proc.stdout.readline().strip()
            if not port:
                _, error = proc.communicate(timeout=5)
                pytest.fail(error)
            requests = [("POST", "tasks", DATA["tasks"])] if phase == "create" else [
                ("GET", "tasks/" + task_id, None),
                ("GET", "calendar?from=2026-10-05&to=2026-10-11", None),
                ("GET", "graduation-rules/" + RULE, None),
                ("GET", "dashboard?date=2026-10-09", None)]
            for method, path, payload in requests:
                url = f"http://127.0.0.1:{port}{PREFIX}{path}"
                req = Request(url, data=json.dumps(payload).encode() if payload else None, method=method,
                              headers={"Content-Type": "application/json"})
                with urlopen(req, timeout=5) as response:
                    body = json.load(response)
                    evidence.append({"transport": "real HTTP", "phase": phase, "pid": proc.pid, "url": url,
                                     "method": method, "input": payload, "actual_status": response.status, "actual_body": body})
                    assert response.status == (201 if method == "POST" else 200)
                    if method == "POST":
                        task_id = body["data"]["task_id"]
                    elif path.startswith("tasks/"):
                        assert body["data"]["task_id"] == task_id and body["data"]["due_time"] is None
        finally:
            proc.terminate()
            proc.communicate(timeout=10)


def test_B20_fully_mapped_synthetic_graduation_met(api, planner_app, evidence):
    """Synthetic confirmed mappings exercise the met branch; not actual student records."""
    from app.planner_core import course_snapshot, dump, timestamp
    from app.planner_graduation import document
    select_rule(api)
    with planner_app.app_context():
        db = get_db()
        d = document(db, RULE)
        counter = 0
        def passed_course(name, credits, category, source_key=None, domain=None):
            nonlocal counter
            counter += 1
            cid = "test-confirmed-" + str(counter)
            db.execute("INSERT INTO courses VALUES (?,?,?,?,?,?,?,?)", (cid, None, name, credits, "dept-nutn-csie", "unknown", None, None))
            db.execute("INSERT INTO course_classifications VALUES (?,?,?)", (cid, RULE, category))
            if source_key:
                db.execute("INSERT INTO graduation_course_mappings VALUES (?,?,?)", (RULE, source_key, cid))
            if domain:
                db.execute("INSERT INTO graduation_course_domains VALUES (?,?,?)", (RULE, cid, domain))
            payload = {"course_id": cid, "semester_id": SEM, "offering_id": None, "enrollment_status": "finished",
                       "passed": True, "grade": None, "course_snapshot": course_snapshot(db, cid)}
            now = timestamp()
            db.execute("INSERT INTO planner_resources VALUES (?,?,?,?,?,?)",
                       ("enrollments", "test-record-" + str(counter), "user-demo-001", dump(payload), now, now))
        for c in d["credit_requirements"]["department_required"]["courses"]:
            passed_course(c["name"], c["credits"], "department_required", "required:" + c["course_code"])
        for i, c in enumerate(d["credit_requirements"]["general_education"]["core"]["requirements"]):
            passed_course(c["name"], c["required_credits"], "general_core", f"general_core:{i}")
        passed_course("科技法律", 2, "college_required", "college:0")
        for domain in ("文史哲藝術", "社會脈動", "生命科學"):
            passed_course("測試領域課 " + domain, 4, "general_domain", domain=domain)
        passed_course("測試多元課", 6, "general_diverse")
        passed_course("測試系選修", 12, "department_elective")
        passed_course("測試自由選修", 20, "free_elective")
        for p in d["program_requirements"]["programs"]:
            for i, name in enumerate(p["courses"][:3]):
                passed_course(name + "（零學分測試項目）", 0, "free_elective", f"program:{p['id']}:{i}")
        db.commit()
    evidence.append({"synthetic_fixture": "133 credits with explicit required/core/domain/program mappings; 0-credit program fixtures are test-only"})
    api("PUT", "lecture-progress", {"professional_count": 10, "general_count": 12})
    result = api("GET", "graduation-progress")
    assert result["earned_credits"] == 133
    assert result["overall_status"] == "met" and all(c["status"] == "met" for c in result["checks"])
    assert result["missing_required_courses"] == []
    assert sum(p["credits"] for row in result["credit_allocation"] for p in row["allocations"]) == 133


def test_B21_successful_session_patch_and_version(api):
    p = plan(api)
    result = confirm(api, p)
    s = result["sessions"][0]
    changed = api("PATCH", "study-sessions/" + s["session_id"], {"plan_version": 2, "title": "更新標題"})
    assert changed["session"]["session_id"] == s["session_id"]
    assert changed["session"]["starts_at"] == s["starts_at"] and changed["plan_version"] == 3
    api("DELETE", "study-sessions/" + s["session_id"] + "?plan_version=2", status=409)


def test_B22_in_progress_is_not_passed_prerequisite(api):
    create(api, "enrollments", course_id="course-demo-002", enrollment_status="in_progress", passed=None, grade=None)
    create(api, "enrollments", course_id="course-demo-003", enrollment_status="in_progress", passed=None, grade=None)
    result = api("POST", "planned-courses/check", {"target_semester_id": SEM, "items": [{"course_id": "course-demo-004"}]})
    assert result["prerequisite_checks"][0]["status"] == "not_met"


@pytest.mark.parametrize("method,path", [
    ("GET", "calendar"), ("POST", "schedule/conflicts"), ("POST", "schedule/availability"),
    ("POST", "study-plans/unknown/generate"), ("PUT", "study-plans/unknown/sessions"),
    ("POST", "planned-courses/check"), ("GET", "graduation-rules/" + RULE),
    ("GET", "programs"), ("PUT", "lecture-progress"), ("GET", "graduation-progress"),
    ("GET", "dashboard"), ("GET", "campus-maps"),
])
def test_B23_unknown_query_calculation_endpoints(api, method, path):
    api(method, path + "?typo=1", {} if method in ("POST", "PUT") else None, 422, phase="L2")
