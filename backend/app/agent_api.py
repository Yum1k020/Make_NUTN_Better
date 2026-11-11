"""Additive, versioned study-agent API and a separate local verification console."""

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4

from flask import Blueprint, g, send_from_directory

from . import agent_provider
from .agent_engine import MAX_CALLS, MAX_ROLE_TURNS, MAX_SECONDS, ROLE_TOOLS, Runner, VERSION
from .db import DEMO_USER_ID, get_db
from .planner import endpoint, transaction
from .planner_core import (RESOURCE, Problem, at, body, boolean, choice, course_snapshot, day,
                           dump, invalid, moment, owned, query, shape, timestamp)
from .planner_logic import generate, replace_sessions, save, sessions_valid, validate_plan
from .planner_schedule import available, occupied, plan_windows

routes = Blueprint("study_agents", __name__, url_prefix="/api/v1/agent")


def init_db(db):
    db.execute("""CREATE TABLE IF NOT EXISTS agent_runs (
        run_id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES user_profiles(user_id),
        body TEXT NOT NULL CHECK(json_valid(body)), created_at TEXT NOT NULL)""")
    db.execute("CREATE INDEX IF NOT EXISTS agent_runs_owner ON agent_runs(user_id, created_at)")


def plan_input(value):
    # New drafts only: no arbitrary existing-plan ID or exam-task relation.
    _, fields, required, _ = RESOURCE["study-plans"]
    fields = {k: v for k, v in fields.items() if k != "exam_task_id"}
    p = shape(value, fields, required)
    validate_plan(p)
    if p["target_minutes"] > 14400 or not 15 <= p["session_minutes"] <= 240:
        invalid("plan", "目標最多 14400 分鐘，單次時長須為 15～240 分鐘")
    if len(p["allowed_windows"]) > 28:
        invalid("allowed_windows", "最多 28 個每週視窗")
    return p


def digest(value):
    return "sha256:" + sha256(dump(value).encode()).hexdigest()


def snapshot(db, plan):
    course = course_snapshot(db, plan["course_id"])
    start, end = at(day(plan["start_date"])), at(day(plan["exam_date"]))
    events, warnings = occupied(db, start, end)
    # Include source identity and actual intervals; unrelated planner resources do not invalidate a run.
    content = {"course": course, "plan": plan, "events": sorted(events, key=lambda e: e["event_key"]),
               "warnings": sorted(warnings, key=dump), "engine_version": VERSION}
    return digest(content), course, content


def get_run(db, run_id):
    row = db.execute("SELECT body FROM agent_runs WHERE run_id=? AND user_id=?", (run_id, DEMO_USER_ID)).fetchone()
    if row is None:
        raise Problem(404, "RUN_NOT_FOUND", "找不到本人的執行紀錄")
    return json.loads(row["body"])


def put_run(db, run):
    db.execute("INSERT INTO agent_runs VALUES (?,?,?,?) ON CONFLICT(run_id) DO UPDATE SET body=excluded.body",
               (run["run_id"], DEMO_USER_ID, dump(run), run["created_at"]))


def verify(db, run):
    checks = []
    def check(key, passed, detail):
        checks.append({"id": key, "passed": passed, "detail": detail})
    check("run_completed", run["status"] in ("completed", "partial"), "角色已交付可驗證結果；partial 代表時數不足")
    if not run.get("result"):
        return {"passed": False, "checked_at": timestamp(), "checks": checks}
    plan, result = run["request"]["plan"], run["result"]
    # After commit, validate against the persisted plan, excluding only its own sessions.
    committed = run.get("commit")
    if committed:
        try:
            saved = owned(db, "study-plans", committed["plan_id"])
            rows = db.execute("SELECT body FROM planner_resources WHERE kind='study-sessions' AND user_id=?", (DEMO_USER_ID,))
            actual = [json.loads(row["body"]) for row in rows]
            actual = [{k: s[k] for k in ("title", "starts_at", "ends_at")} for s in actual if s["plan_id"] == saved["plan_id"]]
            unchanged = (saved["plan_version"] == committed["plan_version"] and
                         sorted(actual, key=dump) == sorted(result["candidates"], key=dump))
            check("committed_version", unchanged, "已儲存計畫的版本與時段仍與交付一致")
            validation_plan = {**plan, "plan_id": saved["plan_id"]}
        except Problem:
            check("committed_version", False, "已儲存計畫已不存在")
            return {"passed": False, "checked_at": timestamp(), "checks": checks}
    else:
        version, _, _ = snapshot(db, plan)
        check("snapshot_current", version == run["snapshot_version"], "目前課程、忙碌時段與原始快照一致")
        validation_plan = {**plan, "plan_id": run["run_id"]}
    try:
        # Check completeness even when zero sessions were generated.
        availability = available(db, at(day(plan["start_date"])), at(day(plan["exam_date"])),
                                 plan_windows(plan), ignore_plan=validation_plan["plan_id"])
        check("schedule_complete", availability["check_complete"], "課表時間完整，沒有未解析的上課時段")
        sessions_valid(db, validation_plan, result["candidates"])
        check("time_constraints", True, "時段均在考試日前、允許視窗內，且不與目前行程或彼此重疊")
    except Problem as error:
        check("time_constraints", False, error.message)
    total = sum(int((moment(s["ends_at"]) - moment(s["starts_at"])).total_seconds() // 60) for s in result["candidates"])
    check("minute_accounting", total == result["scheduled_minutes"] and
          total + result["remaining_minutes"] == plan["target_minutes"] and result["remaining_minutes"] >= 0,
          "時段加總等於已安排分鐘；已安排加尚缺等於目標")
    evidence = [e for e in run["events"] if e["type"] == "tool_result" and e.get("tool") == "generate_schedule"]
    check("source_grounding", len(evidence) == 1 and evidence[0]["result"] == result,
          "結果與 generate_schedule 工具紀錄一致，保留來源及快照版本")
    return {"passed": all(c["passed"] for c in checks), "checked_at": timestamp(), "checks": checks,
            "scope": "程式驗證時段、分鐘、來源及目前資料；不驗證模型自由文字的所有語意"}


@routes.get("/config")
@endpoint
def config_route():
    query({})
    return {"data": {"version": VERSION, "openai": agent_provider.settings(), "providers": ["offline", "openai"],
                     "architectures": ["multi", "single"], "timezone": "Asia/Taipei", "roles": ROLE_TOOLS,
                     "limits": {"model_calls": MAX_CALLS, "role_turns": MAX_ROLE_TURNS, "run_seconds": MAX_SECONDS},
                     "identity": "固定測試使用者；尚無正式登入", "offline_notice": "固定工具流程，不代表真實模型品質"}}


@routes.get("/examples")
@endpoint
def examples_route():
    query({})
    # Stable example week makes evidence repeatable; it does not insert demo calendar data.
    plan = {"course_id": "course-demo-001", "start_date": "2026-11-16", "exam_date": "2026-11-20",
            "target_minutes": 360, "session_minutes": 60,
            "allowed_windows": [{"weekday": d, "start_time": "19:00", "end_time": "21:00"} for d in range(1, 5)]}
    short = deepcopy(plan)
    short["allowed_windows"] = [{"weekday": 1, "start_time": "19:00", "end_time": "21:00"}]
    return {"data": [{"id": "normal", "label": "六小時複習", "request": {"provider": "offline", "architecture": "multi", "plan": plan}},
                     {"id": "shortage", "label": "時數不足", "request": {"provider": "offline", "architecture": "multi", "plan": short}}]}


@routes.post("/runs")
@endpoint
def create_run():
    query({})
    p = shape(body(), {"provider": (choice("offline", "openai"), False),
                       "architecture": (choice("single", "multi"), False), "plan": (plan_input, False)},
              ["provider", "architecture", "plan"])
    if p["provider"] == "openai" and not agent_provider.settings()["configured"]:
        raise Problem(503, "OPENAI_NOT_CONFIGURED", "請先在後端設定 OPENAI_API_KEY 與 OPENAI_MODEL")
    db = transaction()
    run_id = str(uuid4())
    version, course, source = snapshot(db, p["plan"])
    plan = {**p["plan"], "plan_id": run_id, "plan_version": 1}
    availability = available(db, at(day(plan["start_date"])), at(day(plan["exam_date"])), plan_windows(plan))
    generated, generation_error = None, None
    try:
        generated = generate(db, plan)
    except Problem as error:
        generation_error = error
    # Release the read snapshot before any network call; no database lock held during inference.
    db.commit()
    g.pop("planner_transaction", None)
    db.execute("PRAGMA query_only = OFF")
    run = {"run_id": run_id, "created_at": timestamp(), "request": p, "engine_version": VERSION,
           "snapshot_version": version, "course": course, "commit": None,
           "provider": {"name": p["provider"], "model": agent_provider.settings()["model"] if p["provider"] == "openai" else None},
           "sources": [{"source_id": "AVAILABILITY-01", "kind": "planner_snapshot", "version": version,
                        "data": {"plan": source["plan"], "events": source["events"], "warnings": source["warnings"]}},
                       {"source_id": "SCHEDULE-01", "kind": "planner_logic.generate", "version": VERSION}]}
    Runner(run, availability, generated, generation_error).execute()
    db = transaction(True)
    run["verification"] = verify(db, run)
    put_run(db, run)
    return {"data": run}, 201


@routes.get("/runs")
@endpoint
def list_runs():
    query({})
    db = transaction()
    rows = db.execute("SELECT body FROM agent_runs WHERE user_id=? ORDER BY created_at DESC,run_id DESC LIMIT 20", (DEMO_USER_ID,))
    runs = [json.loads(r["body"]) for r in rows]
    return {"data": [{k: r[k] for k in ("run_id", "created_at", "status", "provider", "request", "metrics", "commit")} for r in runs]}


@routes.get("/runs/<string:run_id>")
@endpoint
def run_detail(run_id):
    query({})
    return {"data": get_run(transaction(), run_id)}


@routes.post("/runs/<string:run_id>/verify")
@endpoint
def verify_run(run_id):
    query({})
    body(empty=True)
    db = transaction()
    run = get_run(db, run_id)
    return {"data": verify(db, run)}


@routes.post("/runs/<string:run_id>/commit")
@endpoint
def commit_run(run_id):
    query({})
    p = shape(body(), {"confirmed": (boolean, False)}, ["confirmed"])
    if not p["confirmed"]:
        invalid("confirmed", "必須明確確認才能儲存")
    db = transaction(True)
    run = get_run(db, run_id)
    if run["commit"]:
        return {"data": run["commit"], "meta": {"idempotent_replay": True}}
    verification = verify(db, run)
    if not verification["passed"]:
        raise Problem(409, "RUN_NOT_COMMITTABLE", "結果失敗、資料已變動或驗證未通過，請重新執行", conflicts=verification["checks"])
    if not run["result"]["candidates"]:
        raise Problem(409, "EMPTY_SCHEDULE", "沒有可儲存的複習時段")
    plan = save(db, "study-plans", run["request"]["plan"])
    result = replace_sessions(db, plan, run["result"]["candidates"], plan["plan_version"])
    run["commit"] = {"plan_id": plan["plan_id"], "plan_version": result["plan_version"],
                     "committed_at": timestamp(), "scheduled_minutes": result["scheduled_minutes"],
                     "remaining_minutes": result["remaining_minutes"]}
    put_run(db, run)
    return {"data": run["commit"]}, 201


def init_app(app, api):
    app.register_blueprint(routes)
    @app.get("/agent-lab")
    @app.get("/agent-lab/")
    def agent_lab():
        return send_from_directory(Path(__file__).parent / "agent_lab", "index.html")

    @app.get("/agent-lab/assets/<path:filename>")
    def agent_asset(filename):
        return send_from_directory(Path(__file__).parent / "agent_lab", filename)

    from .agent_openapi import register_docs
    register_docs(app, api)
