"""The fixed-identity /me baseline. No authentication is implied."""

import sqlite3

from flask import current_app, jsonify, request
from flask.views import MethodView
from flask_smorest import Blueprint
from marshmallow import Schema, ValidationError, fields, validate
from werkzeug.exceptions import BadRequest

from .db import DEMO_USER_ID, get_db

routes = Blueprint("profile", __name__, url_prefix="/api/v1",
                   description="固定測試身分的本機使用者資料 API")
EDITABLE = {
    "department_id": (str, "departments", "id", "系所不存在"),
    "admission_year": (int, "admission_years", "year", "入學年度不受支援"),
    "current_semester_id": (str, "semesters", "id", "學期不存在"),
}


class ProfileSchema(Schema):
    user_id = fields.String(required=True)
    department_id = fields.String(required=True, allow_none=True)
    admission_year = fields.Integer(required=True, allow_none=True, strict=True)
    rule_set_id = fields.String(required=True, allow_none=True)
    current_semester_id = fields.String(required=True, allow_none=True)
    profile_complete = fields.Boolean(required=True)
    rule_status = fields.String(required=True, validate=validate.OneOf(
        ["matched", "not_found", "profile_incomplete"]))


class ResponseSchema(Schema):
    data = fields.Nested(ProfileSchema, required=True)


class FieldErrorSchema(Schema):
    field = fields.String(required=True)
    reason = fields.String(required=True)


class ErrorDetailSchema(Schema):
    code = fields.String(required=True)
    message = fields.String(required=True)
    fields = fields.List(fields.Nested(FieldErrorSchema), required=True)


class ProfileErrorSchema(Schema):
    error = fields.Nested(ErrorDetailSchema, required=True)


class InputError(Exception):
    def __init__(self, fields, status=422, code="VALIDATION_ERROR", message="輸入資料不合法"):
        self.fields, self.status, self.code, self.message = fields, status, code, message


def field_error(field, reason):
    return {"field": field, "reason": reason}


def parse_patch():
    if request.mimetype != "application/json":
        raise InputError([], 415, "UNSUPPORTED_MEDIA_TYPE", "請使用 application/json")
    try:
        payload = request.get_json()
    except BadRequest:
        raise InputError([], 400, "INVALID_JSON", "請求 JSON 格式錯誤") from None
    if not isinstance(payload, dict) or not payload:
        raise InputError([field_error("body", "必須為至少包含一個可修改欄位的 JSON 物件")])
    errors = []
    for key, value in payload.items():
        if key not in EDITABLE:
            errors.append(field_error(key, "不允許修改此欄位"))
        elif type(value) is not EDITABLE[key][0]:
            reason = ("必須為系統支援的民國年度整數" if key == "admission_year"
                      else "必須為非 null 的字串")
            errors.append(field_error(key, reason))
    if errors:
        raise InputError(errors)
    return payload


def validate_references(db, profile):
    errors = []
    for key, (_, table, column, reason) in EDITABLE.items():
        value = profile[key]
        # table/column come exclusively from the constant allowlist above.
        if value is not None and db.execute(
            f"SELECT 1 FROM {table} WHERE {column} = ?", (value,)
        ).fetchone() is None:
            errors.append(field_error(key, reason))
    if errors:
        raise InputError(errors)


def find_rule(db, profile):
    row = db.execute(
        "SELECT id FROM rule_sets WHERE department_id = ? AND admission_year = ?",
        (profile["department_id"], profile["admission_year"]),
    ).fetchone()
    return row["id"] if row else None


def make_response_data(db, profile):
    try:
        validate_references(db, profile)
    except InputError as error:
        raise ValueError("Stored profile references invalid data") from error
    if profile["user_id"] != DEMO_USER_ID or profile["rule_set_id"] != find_rule(db, profile):
        raise ValueError("Stored profile violates the response contract")
    complete = all(profile[key] is not None for key in EDITABLE)
    data = dict(profile, profile_complete=complete,
                rule_status=("profile_incomplete" if not complete else
                             "matched" if profile["rule_set_id"] else "not_found"))
    # Validate before committing any update, rather than relying on serialization.
    return ResponseSchema().load({"data": data})


def handle_me(patch=False):
    try:
        payload = parse_patch() if patch else None
        db = get_db()
        with db:
            db.execute("BEGIN IMMEDIATE" if patch else "BEGIN")
            row = db.execute("SELECT * FROM user_profiles WHERE user_id = ?",
                             (DEMO_USER_ID,)).fetchone()
            if row is None:
                raise ValueError("Run init-db before using /me")
            profile = dict(row)
            if patch:
                profile.update(payload)
                validate_references(db, profile)
                profile["rule_set_id"] = find_rule(db, profile)
                db.execute("""UPDATE user_profiles SET department_id = ?, admission_year = ?,
                           current_semester_id = ?, rule_set_id = ? WHERE user_id = ?""",
                           (profile["department_id"], profile["admission_year"],
                            profile["current_semester_id"], profile["rule_set_id"], DEMO_USER_ID))
            result = make_response_data(db, profile)
        return result
    except InputError as error:
        if patch:
            return jsonify(error={"code": error.code, "message": error.message,
                                  "fields": error.fields}), error.status
        current_app.logger.exception("Invalid stored profile")
    except (sqlite3.Error, ValueError, ValidationError):
        current_app.logger.exception("Profile request failed")
    return jsonify(error={"code": "INTERNAL_ERROR", "message": "無法讀取或保存使用者資料",
                          "fields": []}), 500


@routes.route("/me")
class Me(MethodView):
    @routes.response(200, ResponseSchema)
    @routes.alt_response(500, schema=ProfileErrorSchema)
    def get(self):
        """取得固定測試使用者資料（無登入驗證）。"""
        return handle_me()

    @routes.doc(requestBody={"required": True, "content": {"application/json": {
        "schema": {"type": "object", "minProperties": 1, "additionalProperties": False,
                   "properties": {"department_id": {"type": "string"},
                                  "admission_year": {"type": "integer"},
                                  "current_semester_id": {"type": "string"}}}}}})
    @routes.response(200, ResponseSchema)
    @routes.alt_response(400, schema=ProfileErrorSchema)
    @routes.alt_response(415, schema=ProfileErrorSchema)
    @routes.alt_response(422, schema=ProfileErrorSchema)
    @routes.alt_response(500, schema=ProfileErrorSchema)
    def patch(self):
        """部分更新；缺規則仍保存，無效欄位全部不保存。"""
        return handle_me(patch=True)
