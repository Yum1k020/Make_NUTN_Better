"""HTTP boundary for planner resources; one transaction covers validation and all writes."""

from datetime import timedelta
from functools import wraps
import json
from pathlib import Path
import sqlite3

from flask import current_app, g, jsonify, request, send_from_directory
from flask_smorest import Blueprint
from marshmallow import ValidationError

from .db import DEMO_USER_ID, get_db
from .planner_core import (
    RESOURCE, DATETIME, ID, NULL_ID, TITLE, Problem, at, body, boolean, checked, choice,
    day, dump, integer, interval, invalid, moment, owned, query, records, reference,
    remove, shape, stage, store_resource, string, timestamp,
)
from .planner_logic import (
    delete, generate, output, plan_sessions, replace_sessions, save, session_result,
    sessions_valid, version_matches,
)
from .planner_schedule import available, calendar, check, validate_exclude
from .planner_graduation import MAPS, lectures, programs, progress, rules
from .planner_checks import dashboard, planned_check

routes = Blueprint("planner", __name__, url_prefix="/api/v1", description="固定測試使用者的安排系統；無正式登入或 AI")


def endpoint(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        stage("L1")
        db = None
        try:
            # Parse shape/query before a database transaction is acquired.
            stage("L2")
            if request.method in ("GET", "DELETE") and request.get_data():
                invalid("body", "此操作不接受 Request body")
            result = func(*args, **kwargs)
            payload, status = result if isinstance(result, tuple) else (result, 200)
            stage("L6")
            if status != 204:
                dump(payload)  # finite numbers and JSON types, before commit
                response = jsonify(payload)
            else:
                response = current_app.response_class(status=204)
            db = g.get("planner_transaction")
            if db is not None:
                if request.method not in ("GET",) and request.path not in ("/api/v1/schedule/conflicts", "/api/v1/schedule/availability", "/api/v1/planned-courses/check") and not request.path.endswith("/generate"):
                    stage("L5")
                db.commit()
                stage("L6")
            current_app.logger.info("planner success", extra={"planner_stage": g.planner_stage, "planner_status": status})
            return response, status
        except Problem as error:
            payload = {"error": {"code": error.code, "message": error.message, "fields": error.fields}}
            if error.conflicts is not None:
                payload["error"]["conflicts"] = error.conflicts
            status = error.status
        except (sqlite3.Error, ValueError, TypeError, KeyError, ValidationError, OverflowError):
            current_app.logger.exception("Planner operation failed")
            status = 500
            payload = {"error": {"code": "INTERNAL_ERROR", "message": "無法完成操作", "fields": []}}
        db = g.get("planner_transaction")
        if db is not None:
            db.rollback()
        current_app.logger.info("planner failure", extra={"planner_stage": g.planner_stage, "planner_status": status})
        return jsonify(payload), status
    return wrapped


def transaction(write=False):
    stage("L3")
    db = get_db()
    if not write:
        db.execute("PRAGMA query_only = ON")
    db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
    g.planner_transaction = db
    if db.execute("SELECT 1 FROM user_profiles WHERE user_id=?", (DEMO_USER_ID,)).fetchone() is None:
        raise ValueError("Current user missing; run init-db")
    return db


def listed(data):
    return {"data": data, "meta": {"count": len(data)}}


def query_bool(value):
    if value not in ("true", "false"):
        raise ValueError()
    return value == "true"


FILTERS = {
    "enrollments": {"semester_id": string, "enrollment_status": choice("in_progress", "finished")},
    "timetable-entries": {"semester_id": string},
    "tasks": {"from": day, "to": day, "completed": query_bool, "course_id": string},
    "personal-events": {"from": moment, "to": moment},
    "study-plans": {}, "planned-courses": {"target_semester_id": string},
}


def resource_list(db, kind, params):
    for key in ("semester_id", "target_semester_id"):
        if key in params:
            reference(db, "semesters", "id", params[key], key)
    if "course_id" in params:
        reference(db, "courses", "course_id", params["course_id"], "course_id")
    if "from" in params and "to" in params and (params["to"] < params["from"] or kind == "personal-events" and params["to"] == params["from"]):
        invalid("to", "結束不能早於開始")
    result = []
    for r in records(db, kind):
        if any(r[k] != v for k, v in params.items() if k not in ("from", "to")):
            continue
        if kind == "tasks" and ("from" in params and day(r["due_date"]) < params["from"] or "to" in params and day(r["due_date"]) > params["to"]):
            continue
        if kind == "personal-events" and ("from" in params and moment(r["ends_at"]) <= params["from"] or "to" in params and moment(r["starts_at"]) >= params["to"]):
            continue
        result.append(output(db, kind, r))
    if kind == "tasks":
        result.sort(key=lambda t: (t["due_date"], t["due_time"] is None, t["due_time"] or "", t["task_id"]))
    if kind == "personal-events":
        result.sort(key=lambda e: (e["starts_at"], e["event_id"]))
    return result


def register_resource(kind):
    @endpoint
    def collection():
        if request.method == "GET":
            params = query(FILTERS[kind])
            return listed(resource_list(transaction(), kind, params))
        query({})
        payload = body()
        # Reject unknown/missing fields before any reads.
        shape(payload, RESOURCE[kind][1], RESOURCE[kind][2])
        return {"data": save(transaction(True), kind, payload)}, 201

    @endpoint
    def item(resource_id):
        query({})
        payload = body() if request.method == "PATCH" else None
        if payload is not None:
            if not payload:
                invalid("body", "PATCH 至少提供一個可修改欄位")
            shape(payload, RESOURCE[kind][1])
        db = transaction(request.method != "GET")
        old = owned(db, kind, resource_id)
        if request.method == "GET":
            return {"data": output(db, kind, old)}
        if request.method == "PATCH":
            return {"data": save(db, kind, payload, old)}
        delete(db, kind, old)
        return None, 204

    routes.add_url_rule("/" + kind, endpoint=kind + "_collection", view_func=collection, methods=["GET", "POST"])
    routes.add_url_rule("/" + kind + "/<string:resource_id>", endpoint=kind + "_item", view_func=item, methods=["GET", "PATCH", "DELETE"])


for resource in FILTERS:
    register_resource(resource)


@routes.get("/calendar")
@endpoint
def calendar_route():
    params = query({"from": day, "to": day}, ["from", "to"])
    if not 0 <= (params["to"] - params["from"]).days <= 30:
        invalid("to", "日期範圍須為 1～31 個日曆日")
    return {"data": calendar(transaction(), params["from"], params["to"])}


@routes.post("/schedule/conflicts")
@endpoint
def conflicts_route():
    query({})
    fields = {"starts_at": DATETIME, "ends_at": DATETIME, "exclude_source": (
        lambda v: shape(v, {"source_type": (choice("class", "personal_event", "study_session"), False), "source_id": ID}, ["source_type", "source_id"]), False)}
    p = shape(body(), fields, ["starts_at", "ends_at"])
    a, b = moment(p["starts_at"]), moment(p["ends_at"])
    interval(a, b)
    db = transaction()
    return {"data": check(db, a, b, exclude=validate_exclude(db, p.get("exclude_source"), a, b))}


@routes.post("/schedule/availability")
@endpoint
def availability_route():
    query({})
    p = shape(body(), {"from": DATETIME, "to": DATETIME, "allowed_windows": (lambda v: interval_items(v), False),
                       "min_duration_minutes": (integer, False)}, ["from", "to", "allowed_windows"], {"min_duration_minutes": 1})
    a, b = moment(p["from"]), moment(p["to"])
    interval(a, b, "to", 60)
    windows = []
    for w in p["allowed_windows"]:
        start, end = moment(w["starts_at"]), moment(w["ends_at"])
        interval(start, end)
        if start < a or end > b:
            invalid("allowed_windows", "視窗須在查詢範圍內")
        windows.append((start, end))
    return {"data": available(transaction(), a, b, windows, p["min_duration_minutes"])}


def interval_items(value, sessions=False, empty=False):
    if type(value) is not list or not value and not empty:
        raise ValueError("須為時段陣列")
    fields = {"starts_at": DATETIME, "ends_at": DATETIME}
    if sessions:
        fields["title"] = TITLE
    return [shape(row, fields, fields.keys()) for row in value]


@routes.post("/study-plans/<string:plan_id>/generate")
@endpoint
def generate_route(plan_id):
    query({})
    body(empty=True)
    db = transaction()
    return {"data": generate(db, owned(db, "study-plans", plan_id))}


@routes.route("/study-plans/<string:plan_id>/sessions", methods=["GET", "PUT"])
@endpoint
def sessions_route(plan_id):
    query({})
    p = shape(body(), {"plan_version": (integer, False), "sessions": (lambda v: interval_items(v, True, True), False)},
              ["plan_version", "sessions"]) if request.method == "PUT" else None
    db = transaction(p is not None)
    plan = owned(db, "study-plans", plan_id)
    return {"data": session_result(db, plan) if p is None else replace_sessions(db, plan, p["sessions"], p["plan_version"])}


def query_version(value):
    if not value.isascii() or not value.isdigit():
        raise ValueError()
    return integer(int(value))


@routes.route("/study-sessions/<string:session_id>", methods=["PATCH", "DELETE"])
@endpoint
def session_route(session_id):
    if request.method == "DELETE":
        p = query({"plan_version": query_version}, ["plan_version"])
    else:
        query({})
        p = shape(body(), {"plan_version": (integer, False), **RESOURCE["study-sessions"][1]}, ["plan_version"])
        if len(p) == 1:
            invalid("body", "至少提供一個時段修改欄位")
    db = transaction(True)
    session = owned(db, "study-sessions", session_id)
    plan = owned(db, "study-plans", session["plan_id"])
    version_matches(plan, p.pop("plan_version"))
    if request.method == "DELETE":
        remove(db, "study-sessions", session_id)
    else:
        revised = {**session, **p}
        sessions = [revised if s["session_id"] == session_id else s for s in plan_sessions(db, plan["plan_id"])]
        sessions_valid(db, plan, sessions)
        revised = store_resource(db, "study-sessions", revised, session)
    plan = store_resource(db, "study-plans", dict(plan, plan_version=plan["plan_version"] + 1), plan)
    if request.method == "DELETE":
        return None, 204
    return {"data": {"session": revised, **session_result(db, plan)}}


@routes.post("/planned-courses/check")
@endpoint
def planned_check_route():
    query({})
    def items(v):
        if type(v) is not list or not v:
            raise ValueError()
        return [shape(x, {"course_id": ID, "offering_id": NULL_ID}, ["course_id"], {"offering_id": None}) for x in v]
    p = shape(body(), {"target_semester_id": ID, "items": (items, False)}, ["target_semester_id", "items"])
    return {"data": planned_check(transaction(), p["target_semester_id"], p["items"])}


@routes.get("/graduation-rules/<string:rule_id>")
@endpoint
def rules_route(rule_id):
    query({})
    return {"data": rules(transaction(), rule_id)}


@routes.get("/programs")
@endpoint
def programs_route():
    p = query({"rule_set_id": string}, ["rule_set_id"])
    return listed(programs(transaction(), p["rule_set_id"]))


@routes.route("/lecture-progress", methods=["GET", "PUT"])
@endpoint
def lecture_route():
    query({})
    p = shape(body(), {"professional_count": (lambda v: integer(v, 0), True), "general_count": (lambda v: integer(v, 0), True)},
              ["professional_count", "general_count"]) if request.method == "PUT" else None
    db = transaction(p is not None)
    if p is not None:
        stage("L5")
        db.execute("""INSERT INTO lecture_progress VALUES (?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET
                   professional_count=excluded.professional_count,general_count=excluded.general_count,updated_at=excluded.updated_at""",
                   (DEMO_USER_ID, p["professional_count"], p["general_count"], timestamp()))
    return {"data": lectures(db)}


@routes.get("/graduation-progress")
@endpoint
def progress_route():
    query({})
    return {"data": progress(transaction())}


@routes.get("/dashboard")
@endpoint
def dashboard_route():
    p = query({"date": day}, ["date"])
    return {"data": dashboard(transaction(), p["date"])}


@routes.get("/campus-maps")
@endpoint
def maps_route():
    p = query({"campus_id": string})
    db = transaction()
    if "campus_id" in p:
        reference(db, "campuses", "id", p["campus_id"], "campus_id")
    return listed([m for m in MAPS if "campus_id" not in p or m["campus_id"] == p["campus_id"]])


def init_app(app, api):
    api.register_blueprint(routes)
    from .planner_openapi import register_docs
    register_docs(app, api)

    @app.get("/maps/<string:filename>")
    def map_image(filename):
        if filename not in {m["image_url"].rsplit("/", 1)[-1] for m in MAPS}:
            return jsonify(error={"code": "MAP_NOT_FOUND", "message": "圖片不存在", "fields": []}), 404
        return send_from_directory(Path(__file__).resolve().parents[2] / "frontend" / "public" / "maps", filename)
