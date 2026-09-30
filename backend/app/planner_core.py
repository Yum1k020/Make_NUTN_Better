"""Shared validation and transaction-local storage for the fixed-user planner."""

from datetime import date, datetime, timedelta
from hashlib import sha256
import json
import math
import re
from uuid import uuid4
from zoneinfo import ZoneInfo

from flask import g, request
from werkzeug.exceptions import BadRequest

from .db import DEMO_USER_ID

TZ = ZoneInfo("Asia/Taipei")


class Problem(Exception):
    def __init__(self, status=422, code="VALIDATION_ERROR", message="輸入資料不合法", fields=(), conflicts=None):
        self.status, self.code, self.message = status, code, message
        self.fields, self.conflicts = list(fields), conflicts


def invalid(field, reason):
    raise Problem(fields=[{"field": field, "reason": reason}])


def conflict(message, code="CONFLICT", conflicts=None):
    raise Problem(409, code, message, conflicts=conflicts)


def stage(name):
    g.planner_stage = name


def timestamp():
    return datetime.now(TZ).isoformat()


def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def day(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("日期須為 YYYY-MM-DD")
    return date.fromisoformat(value)


def clock(value):
    if not isinstance(value, str) or not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value):
        raise ValueError("時間須為 HH:mm")
    return value


def moment(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(?::[0-9]{2}(?:\.[0-9]{1,6})?)?(?:Z|[+-][0-9]{2}:[0-9]{2})", value
    ):
        raise ValueError("日期時間必須為含時差的 ISO 8601")
    return datetime.fromisoformat(value).astimezone(TZ)


def at(d, time="00:00"):
    return datetime.combine(d, datetime.strptime(time, "%H:%M").time(), TZ)


def checked(parser, value, field):
    try:
        return parser(value)
    except (ValueError, TypeError, OverflowError):
        invalid(field, "格式或數值不合法")


def integer(value, minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError("須為整數")
    return value


def string(value, maximum=None):
    if type(value) is not str:
        raise ValueError("須為字串")
    value = value.strip()
    if not value or maximum is not None and len(value) > maximum:
        raise ValueError("字串長度不合法")
    return value


def boolean(value):
    if type(value) is not bool:
        raise ValueError("須為 boolean")
    return value


def grade(value):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 100:
        raise ValueError("成績須介於 0～100")
    return value


def choice(*allowed):
    def parse(value):
        if value not in allowed or type(value) is not str:
            raise ValueError("不支援的值")
        return value
    return parse


def shape(data, fields, required=(), defaults=None):
    if type(data) is not dict:
        invalid("body", "必須為 JSON 物件")
    for key in data.keys() - fields.keys():
        invalid(key, "不允許的欄位")
    for key in required:
        if key not in data:
            invalid(key, "此欄位為必填")
    result = dict(defaults or {})
    for key, value in data.items():
        parser, nullable = fields[key]
        result[key] = None if value is None and nullable else checked(parser, value, key)
    return result


def body(empty=False):
    stage("L2")
    if empty:
        if request.get_data():
            invalid("body", "此端點不接受 Request body")
        return None
    if request.mimetype != "application/json":
        raise Problem(415, "UNSUPPORTED_MEDIA_TYPE", "請使用 application/json")
    try:
        value = request.get_json()
    except BadRequest:
        raise Problem(400, "INVALID_JSON", "JSON 格式錯誤") from None
    if type(value) is not dict:
        invalid("body", "必須為 JSON 物件")
    return value


def query(fields, required=()):
    stage("L2")
    raw = {}
    for key in request.args:
        if len(request.args.getlist(key)) != 1:
            invalid(key, "查詢參數不可重複")
        raw[key] = request.args[key]
    return shape(raw, {k: (v, False) for k, v in fields.items()}, required)


def interval(start, end, field="ends_at", max_days=None):
    if end <= start or max_days is not None and end - start > timedelta(days=max_days):
        invalid(field, "結束必須晚於開始且在允許範圍內")


def weekly(value, locations=False):
    if type(value) is not list or not value:
        raise ValueError("須有至少一個時段")
    fields = {"weekday": (lambda v: integer(v) if v <= 7 else (_ for _ in ()).throw(ValueError()), False),
              "start_time": (clock, False), "end_time": (clock, False)}
    if locations:
        fields.update(campus_id=(string, True), location=(lambda v: string(v, 500), True))
    result = []
    for row in value:
        # Compare weekday only after type validation (avoid bool/coercion).
        if type(row) is not dict or type(row.get("weekday")) is not int:
            raise ValueError("weekday 須為整數")
        item = shape(row, fields, ["weekday", "start_time", "end_time"],
                     {"campus_id": None, "location": None} if locations else None)
        if item["end_time"] <= item["start_time"]:
            raise ValueError("結束必須晚於開始")
        result.append(item)
    return sorted(result, key=lambda r: (r["weekday"], r["start_time"], r["end_time"]))


ID = (string, False)
NULL_ID = (string, True)
TITLE = (lambda v: string(v, 200), False)
DATE = (lambda v: day(v).isoformat(), False)
DATETIME = (lambda v: moment(v).isoformat(), False)
RESOURCE = {
    "enrollments": ("enrollment_id", {"course_id": ID, "semester_id": ID, "offering_id": NULL_ID,
        "enrollment_status": (choice("in_progress", "finished"), False), "passed": (boolean, True), "grade": (grade, True)},
        ["course_id", "semester_id", "enrollment_status"], {"offering_id": None, "passed": None, "grade": None}),
    "timetable-entries": ("entry_id", {"semester_id": ID, "course_id": ID, "offering_id": NULL_ID,
        "section_name": (lambda v: string(v, 200), True), "meetings": (lambda v: weekly(v, True), False)},
        ["semester_id", "course_id"], {"offering_id": None, "section_name": None}),
    "tasks": ("task_id", {"title": TITLE, "type": (choice("todo", "assignment", "report", "exam", "review"), False),
        "course_id": NULL_ID, "due_date": DATE, "due_time": (clock, True), "completed": (boolean, False), "event_id": NULL_ID},
        ["title", "type", "due_date"], {"course_id": None, "due_time": None, "completed": False, "event_id": None}),
    "personal-events": ("event_id", {"title": TITLE, "starts_at": DATETIME, "ends_at": DATETIME,
        "location": (lambda v: string(v, 500), True)}, ["title", "starts_at", "ends_at"], {"location": None}),
    "study-plans": ("plan_id", {"course_id": ID, "exam_task_id": NULL_ID, "start_date": DATE, "exam_date": DATE,
        "target_minutes": (integer, False), "session_minutes": (integer, False), "allowed_windows": (weekly, False)},
        ["course_id", "start_date", "exam_date", "target_minutes", "session_minutes", "allowed_windows"], {"exam_task_id": None}),
    "planned-courses": ("planned_course_id", {"target_semester_id": ID, "course_id": ID, "offering_id": NULL_ID},
        ["target_semester_id", "course_id"], {"offering_id": None}),
    "study-sessions": ("session_id", {"title": TITLE, "starts_at": DATETIME, "ends_at": DATETIME},
        ["title", "starts_at", "ends_at"], {}),
}


def init_planner(db):
    db.execute("""CREATE TABLE IF NOT EXISTS planner_resources (
        kind TEXT NOT NULL, id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES user_profiles(user_id),
        body TEXT NOT NULL CHECK(json_valid(body)), created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
    db.execute("CREATE INDEX IF NOT EXISTS planner_owner ON planner_resources(user_id, kind)")
    db.execute("""CREATE UNIQUE INDEX IF NOT EXISTS enrollment_course_unique ON planner_resources
        (user_id, json_extract(body, '$.course_id')) WHERE kind='enrollments'""")
    for kind, field in (("timetable-entries", "semester_id"), ("planned-courses", "target_semester_id")):
        name = kind.replace("-", "_")
        db.execute(f"""CREATE UNIQUE INDEX IF NOT EXISTS {name}_unique ON planner_resources
            (user_id, json_extract(body, '$.{field}'), json_extract(body, '$.course_id')) WHERE kind='{kind}'""")
    db.execute("""CREATE TABLE IF NOT EXISTS lecture_progress (
        user_id TEXT PRIMARY KEY REFERENCES user_profiles(user_id), professional_count INTEGER,
        general_count INTEGER, updated_at TEXT)""")


def unpack(row):
    data = json.loads(row["body"])
    if type(data) is not dict:
        raise ValueError("Invalid stored resource object")
    id_field, fields, required, _ = RESOURCE[row["kind"]]
    try:
        visible = {k: v for k, v in data.items() if k in fields}
        required = set(fields)
        if row["kind"] == "timetable-entries" and data.get("source_type") == "catalog" and visible.get("meetings") == []:
            visible.pop("meetings")
            required.remove("meetings")
        shape(visible, fields, required)
        checked(moment, row["created_at"], "created_at")
        checked(moment, row["updated_at"], "updated_at")
    except Problem as error:
        raise ValueError("Invalid stored resource") from error
    if row["kind"] == "study-plans" and (type(data.get("plan_version")) is not int or data["plan_version"] < 1):
        raise ValueError("Invalid stored plan version")
    if row["kind"] == "study-sessions" and not isinstance(data.get("plan_id"), str):
        raise ValueError("Missing session parent")
    if row["kind"] == "timetable-entries" and (not data.get("enrollment_id") or data.get("source_type") not in ("catalog", "manual") or not isinstance(data.get("warnings"), list)):
        raise ValueError("Invalid stored timetable relationship")
    if row["kind"] == "enrollments":
        snapshot = data.get("course_snapshot")
        if (not isinstance(snapshot, dict) or snapshot.get("course_id") != data["course_id"]
                or not snapshot.get("name") or not snapshot.get("version_basis")
                or type(snapshot.get("credits")) not in (int, float) or not math.isfinite(snapshot["credits"]) or snapshot["credits"] < 0):
            raise ValueError("Invalid stored course snapshot")
        if (data["enrollment_status"] == "in_progress" and (data["passed"] is not None or data["grade"] is not None)
                or data["enrollment_status"] == "finished" and type(data["passed"]) is not bool
                or data["grade"] is not None and data["passed"] != (data["grade"] >= 60)):
            raise ValueError("Stored enrollment status and grade disagree")
    return {**data, id_field: row["id"], "user_id": row["user_id"],
            "created_at": row["created_at"], "updated_at": row["updated_at"]}


def records(db, kind):
    return [unpack(r) for r in db.execute("SELECT * FROM planner_resources WHERE kind=? AND user_id=? ORDER BY id",
                                       (kind, DEMO_USER_ID))]


def owned(db, kind, resource_id):
    row = db.execute("SELECT * FROM planner_resources WHERE kind=? AND id=? AND user_id=?", (kind, resource_id, DEMO_USER_ID)).fetchone()
    if row is None:
        raise Problem(404, "RESOURCE_NOT_FOUND", "資源不存在")
    return unpack(row)


def store_resource(db, kind, data, old=None):
    stage("L5")
    key = RESOURCE[kind][0]
    resource_id = old[key] if old else str(uuid4())
    now = timestamp()
    content = {k: v for k, v in data.items() if k not in (key, "user_id", "created_at", "updated_at", "scheduled_minutes", "remaining_minutes")}
    if old:
        db.execute("UPDATE planner_resources SET body=?, updated_at=? WHERE kind=? AND id=? AND user_id=?",
                   (dump(content), now, kind, resource_id, DEMO_USER_ID))
    else:
        db.execute("INSERT INTO planner_resources VALUES (?,?,?,?,?,?)",
                   (kind, resource_id, DEMO_USER_ID, dump(content), now, now))
    stage("L6")
    return owned(db, kind, resource_id)


def remove(db, kind, resource_id):
    stage("L5")
    db.execute("DELETE FROM planner_resources WHERE kind=? AND id=? AND user_id=?", (kind, resource_id, DEMO_USER_ID))


def reference(db, table, key, value, field):
    row = db.execute(f"SELECT * FROM {table} WHERE {key}=?", (value,)).fetchone()
    if row is None:
        invalid(field, "參照資料不存在")
    return dict(row)


def course_snapshot(db, course_id):
    course = reference(db, "courses", "course_id", course_id, "course_id")
    if not course["name"] or type(course["credits"]) not in (int, float) or not math.isfinite(course["credits"]) or course["credits"] < 0:
        raise ValueError("Invalid course data")
    return {"course_id": course_id, "name": course["name"], "credits": course["credits"],
            "version_basis": "sha256:" + sha256(dump(course).encode()).hexdigest()}


def offering(db, offering_id, course_id, semester_id):
    row = reference(db, "course_offerings", "offering_id", offering_id, "offering_id")
    if row["course_id"] != course_id or row["semester_id"] != semester_id:
        invalid("offering_id", "班別與課程或學期不一致")
    meetings = [dict(r) for r in db.execute("SELECT weekday,start_time,end_time,campus_id,location FROM class_meetings WHERE offering_id=? ORDER BY weekday,start_time,meeting_id", (offering_id,))]
    try:
        if row["schedule_status"] == "scheduled":
            weekly(meetings, True)
        elif row["schedule_status"] != "unknown" or meetings:
            raise ValueError("Invalid schedule status")
    except Problem as error:
        raise ValueError("Invalid catalog meetings") from error
    return row, meetings
