"""Read-only shared catalog API. No implicit user-specific rules or enrollment data."""

from functools import wraps
import re
import sqlite3

from flask import current_app, jsonify, request
from flask_smorest import Blueprint
from marshmallow import ValidationError

from .db import get_db
from .profile import ProfileErrorSchema
from .catalog_schemas import (
    CourseListSchema, CourseResponseSchema, OfferingListSchema, SemesterListSchema,
)

routes = Blueprint("catalog", __name__, url_prefix="/api/v1", description="共用測試資料查詢（唯讀）")
REFERENCES = {
    "department_id": ("departments", "id", "系所不存在"),
    "rule_set_id": ("rule_sets", "id", "規則不存在"),
    "semester_id": ("semesters", "id", "學期不存在"),
    "course_id": ("courses", "course_id", "課程不存在"),
}


class QueryError(Exception):
    def __init__(self, fields=(), status=422, code="VALIDATION_ERROR", message="查詢參數不合法"):
        self.fields, self.status, self.code, self.message = list(fields), status, code, message


def error_response(code, message, fields, status):
    return jsonify(error={"code": code, "message": message, "fields": fields}), status


def parse_query(allowed, required):
    errors = []
    values = {}
    for key in request.args:
        entries = request.args.getlist(key)
        reason = None
        if key not in allowed:
            reason = "不支援的查詢參數"
        elif len(entries) != 1:
            reason = "查詢參數不可重複"
        else:
            value = entries[0]
            if key == "q":
                value = value.strip()
                if not 1 <= len(value) <= 100:
                    reason = "搜尋文字去除前後空白後須為 1～100 字"
            elif key == "academic_year":
                if not re.fullmatch(r"[0-9]+", value) or not value.strip("0"):
                    reason = "必須為正整數民國學年度"
                else:
                    # Keep decimal text so even arbitrarily large valid years yield an empty list.
                    value = value.lstrip("0")
            elif not value.strip():
                reason = "識別碼不可為空"
            values[key] = value
        if reason:
            errors.append({"field": key, "reason": reason})
    errors.extend({"field": key, "reason": "此欄位為必填"} for key in required if key not in request.args)
    if request.get_data():
        errors.append({"field": "body", "reason": "此查詢 API 不接受 Request body"})
    if errors:
        raise QueryError(errors)
    return values


def exists(db, table, column, value):
    # Identifiers are internal constants, never caller input.
    return db.execute(f"SELECT 1 FROM {table} WHERE {column} = ?", (value,)).fetchone() is not None


def require_stored_reference(db, table, column, value):
    if value is not None and not exists(db, table, column, value):
        raise ValueError("Stored reference is invalid")


def read_query(allowed, schema, required=()):
    def decorate(func):
        @wraps(func)
        def wrapped(**path):
            try:
                query = parse_query(allowed, required)
                db = get_db()
                # SQLite itself rejects accidental writes in these endpoints.
                db.execute("PRAGMA query_only = ON")
                with db:
                    db.execute("BEGIN")
                    errors = []
                    for key in query.keys() & REFERENCES.keys():
                        table, column, reason = REFERENCES[key]
                        if not exists(db, table, column, query[key]):
                            errors.append({"field": key, "reason": reason})
                    if errors:
                        raise QueryError(sorted(errors, key=lambda error: error["field"]))
                    result = schema().load(func(db, query, **path))
                return result
            except QueryError as error:
                return error_response(error.code, error.message, error.fields, error.status)
            except (sqlite3.Error, ValidationError, ValueError, TypeError):
                current_app.logger.exception("Catalog read or response validation failed")
                return error_response("INTERNAL_ERROR", "無法讀取查詢資料", [], 500)
        return wrapped
    return decorate


def parameters(*names, required=()):
    return [{"in": "query", "name": name, "required": name in required,
             "schema": ({"type": "integer", "minimum": 1} if name == "academic_year" else
                        {"type": "string", "minLength": 1, "maxLength": 100} if name == "q" else
                        {"type": "string", "minLength": 1})} for name in names]


def listing(data):
    return {"data": data, "meta": {"count": len(data)}}


def course_data(db, row, rule_id):
    require_stored_reference(db, "departments", "id", row["offering_department_id"])
    data = {key: row[key] for key in ("course_id", "course_code", "name", "credits", "offering_department_id")}
    data["classification"] = None
    if rule_id is not None:
        category = db.execute("""SELECT credit_category FROM course_classifications
                              WHERE course_id=? AND rule_set_id=?""", (row["course_id"], rule_id)).fetchone()
        data["classification"] = {"rule_set_id": rule_id,
                                  "credit_category": category[0] if category else None,
                                  "status": "classified" if category else "unclassified"}
    return data


@routes.get("/semesters")
@routes.doc(parameters=parameters("academic_year"))
@routes.response(200, SemesterListSchema)
@routes.alt_response(422, schema=ProfileErrorSchema)
@routes.alt_response(500, schema=ProfileErrorSchema)
@read_query({"academic_year"}, SemesterListSchema)
def semesters(db, query):
    """學期清單；日期為展示資料，不代表校曆。"""
    sql = "SELECT id AS semester_id, academic_year, term, starts_on, ends_on, timezone FROM semesters"
    args = ()
    if "academic_year" in query:
        sql += " WHERE academic_year=?"
        args = (query["academic_year"],)
    return listing([dict(row) for row in db.execute(sql + " ORDER BY academic_year DESC, term, id", args)])


@routes.get("/courses")
@routes.doc(parameters=parameters("q", "department_id", "rule_set_id"))
@routes.response(200, CourseListSchema)
@routes.alt_response(422, schema=ProfileErrorSchema)
@routes.alt_response(500, schema=ProfileErrorSchema)
@read_query({"q", "department_id", "rule_set_id"}, CourseListSchema)
def courses(db, query):
    """課程目錄；只有明確指定規則時才附分類，未分類課程仍保留。"""
    clauses, args = [], []
    if "q" in query:
        clauses.append("(instr(lower(name), lower(?)) > 0 OR instr(lower(COALESCE(course_code, '')), lower(?)) > 0)")
        args.extend([query["q"], query["q"]])
    if "department_id" in query:
        clauses.append("offering_department_id=?")
        args.append(query["department_id"])
    sql = "SELECT * FROM courses" + (" WHERE " + " AND ".join(clauses) if clauses else "")
    rows = db.execute(sql + " ORDER BY course_id", args).fetchall()
    return listing([course_data(db, row, query.get("rule_set_id")) for row in rows])


@routes.get("/courses/<string:course_id>")
@routes.doc(parameters=parameters("rule_set_id"))
@routes.response(200, CourseResponseSchema)
@routes.alt_response(404, schema=ProfileErrorSchema)
@routes.alt_response(422, schema=ProfileErrorSchema)
@routes.alt_response(500, schema=ProfileErrorSchema)
@read_query({"rule_set_id"}, CourseResponseSchema)
def course_detail(db, query, course_id):
    """課程詳情與先修規定；不判斷個人是否符合先修。"""
    row = db.execute("SELECT * FROM courses WHERE course_id=?", (course_id,)).fetchone()
    if row is None:
        raise QueryError(status=404, code="COURSE_NOT_FOUND", message="課程不存在")
    data = course_data(db, row, query.get("rule_set_id"))
    ids = [r[0] for r in db.execute("SELECT prerequisite_id FROM course_prerequisites WHERE course_id=? ORDER BY prerequisite_id", (course_id,))]
    for prereq in ids:
        require_stored_reference(db, "courses", "course_id", prereq)
    if row["prerequisite_status"] != "known" and ids:
        raise ValueError("Unknown/none prerequisites have stored course IDs")
    data["prerequisites"] = {"status": row["prerequisite_status"], "mode": row["prerequisite_mode"],
                             "source": row["prerequisite_source"],
                             "course_ids": None if row["prerequisite_status"] == "unknown" else ids}
    return {"data": data}


@routes.get("/course-offerings")
@routes.doc(parameters=parameters("semester_id", "course_id", required={"semester_id"}))
@routes.response(200, OfferingListSchema)
@routes.alt_response(422, schema=ProfileErrorSchema)
@routes.alt_response(500, schema=ProfileErrorSchema)
@read_query({"semester_id", "course_id"}, OfferingListSchema, required={"semester_id"})
def offerings(db, query):
    """指定學期的班別與每週固定時段；unknown 不代表已確認無衝突。"""
    sql = "SELECT * FROM course_offerings WHERE semester_id=?"
    args = [query["semester_id"]]
    if "course_id" in query:
        sql += " AND course_id=?"
        args.append(query["course_id"])
    result = []
    for row in db.execute(sql + " ORDER BY course_id, offering_id", args).fetchall():
        course = db.execute("SELECT * FROM courses WHERE course_id=?", (row["course_id"],)).fetchone()
        if course is None:
            raise ValueError("Offering references a missing course")
        meetings = [dict(r) for r in db.execute("""SELECT meeting_id, weekday, start_time, end_time, campus_id, location
                    FROM class_meetings WHERE offering_id=? ORDER BY weekday, start_time, meeting_id""", (row["offering_id"],))]
        for meeting in meetings:
            require_stored_reference(db, "campuses", "id", meeting["campus_id"])
        result.append(dict(row, course_name=course["name"], class_meetings=meetings))
    return listing(result)
