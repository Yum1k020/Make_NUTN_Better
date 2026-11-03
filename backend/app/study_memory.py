"""Confirmed study preference stored in the same SQLite backend as planner data."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import re
import sqlite3
from uuid import uuid4

from flask import jsonify, request
from flask_smorest import Blueprint

from .db import DEMO_USER_ID, get_db


routes = Blueprint(
    "study-memory",
    __name__,
    url_prefix="/api/v1/study-memory",
    description="固定測試使用者明確確認的學習偏好；保存於 SQLite。",
)

PREFERENCE_KEY = "study_session_minutes"
OPERATION_ID = re.compile(r"^[A-Za-z0-9_-]{8,120}$")


class MemoryProblem(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def init_study_memory(db):
    db.execute(
        """CREATE TABLE IF NOT EXISTS study_preferences (
            user_id TEXT PRIMARY KEY REFERENCES user_profiles(user_id),
            preference_id TEXT NOT NULL,
            preference_key TEXT NOT NULL,
            value INTEGER,
            status TEXT NOT NULL CHECK(status IN ('active', 'withdrawn')),
            version INTEGER NOT NULL CHECK(version > 0),
            expires_at TEXT,
            updated_at TEXT NOT NULL
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS study_preference_operations (
            operation_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES user_profiles(user_id),
            action TEXT NOT NULL CHECK(action IN ('save', 'withdraw')),
            fingerprint TEXT NOT NULL,
            result TEXT NOT NULL CHECK(json_valid(result)),
            created_at TEXT NOT NULL
        )"""
    )


def _now():
    return datetime.now(timezone.utc)


def _iso(value: datetime):
    return value.isoformat().replace("+00:00", "Z")


def _is_int(value, minimum=None, maximum=None):
    if type(value) is not int:
        return False
    return (minimum is None or value >= minimum) and (
        maximum is None or value <= maximum
    )


def _validate_identity():
    supplied = request.headers.get("X-Demo-User-Id")
    if supplied is not None and supplied != DEMO_USER_ID:
        raise MemoryProblem(
            401,
            "MEMORY_IDENTITY_REQUIRED",
            "目前原型只允許固定示範使用者存取記憶。",
        )
    return DEMO_USER_ID


def _json_body(required):
    if request.mimetype != "application/json":
        raise MemoryProblem(415, "UNSUPPORTED_MEDIA_TYPE", "請使用 application/json。")
    payload = request.get_json(silent=True)
    if type(payload) is not dict:
        raise MemoryProblem(400, "INVALID_JSON", "Request body 必須是 JSON 物件。")
    if set(payload) != set(required):
        raise MemoryProblem(422, "MEMORY_INPUT_INVALID", "記憶操作欄位不完整或含未知欄位。")
    if payload.get("confirmed") is not True:
        raise MemoryProblem(422, "MEMORY_INPUT_INVALID", "必須由使用者明確確認後才能寫入。")
    operation_id = payload.get("operationId")
    if type(operation_id) is not str or not OPERATION_ID.fullmatch(operation_id):
        raise MemoryProblem(422, "MEMORY_INPUT_INVALID", "operationId 格式不正確。")
    return payload


def _row(db, user_id):
    return db.execute(
        "SELECT * FROM study_preferences WHERE user_id=?", (user_id,)
    ).fetchone()


def _active(row, now):
    if row is None or row["status"] != "active" or row["value"] is None:
        return False
    try:
        expiry = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        return False
    return expiry > now


def _record(row, now):
    if not _active(row, now):
        return None
    return {
        "id": row["preference_id"],
        "userId": row["user_id"],
        "key": row["preference_key"],
        "value": row["value"],
        "owner": row["user_id"],
        "source": {"type": "user-confirmed", "surface": "study-planner"},
        "version": row["version"],
        "status": row["status"],
        "expiresAt": row["expires_at"],
        "updatedAt": row["updated_at"],
    }


def _state(row, now):
    return {"record": _record(row, now), "latestVersion": row["version"] if row else 0}


def _fingerprint(action, user_id, payload):
    return json.dumps(
        {"action": action, "userId": user_id, **payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _previous_operation(db, operation_id, fingerprint):
    row = db.execute(
        "SELECT fingerprint,result FROM study_preference_operations WHERE operation_id=?",
        (operation_id,),
    ).fetchone()
    if row is None:
        return None
    if row["fingerprint"] != fingerprint:
        raise MemoryProblem(
            409,
            "MEMORY_OPERATION_CONFLICT",
            "相同 operationId 不可用於不同的記憶操作。",
        )
    return {**json.loads(row["result"]), "replayed": True}


def _save_operation(db, operation_id, user_id, action, fingerprint, result, now):
    db.execute(
        "INSERT INTO study_preference_operations VALUES (?,?,?,?,?,?)",
        (
            operation_id,
            user_id,
            action,
            fingerprint,
            json.dumps(result, ensure_ascii=False, sort_keys=True),
            _iso(now),
        ),
    )


def _execute(action, mutation):
    try:
        user_id = _validate_identity()
        db = get_db()
        db.execute("BEGIN IMMEDIATE")
        if db.execute(
            "SELECT 1 FROM user_profiles WHERE user_id=?", (user_id,)
        ).fetchone() is None:
            raise MemoryProblem(500, "MEMORY_SERVICE_FAILED", "示範使用者尚未初始化。")
        result = mutation(db, user_id)
        db.commit()
        return jsonify(result)
    except MemoryProblem as error:
        db = get_db()
        if db.in_transaction:
            db.rollback()
        return jsonify({"error": error.message, "code": error.code}), error.status
    except (sqlite3.Error, ValueError, TypeError, KeyError, json.JSONDecodeError):
        db = get_db()
        if db.in_transaction:
            db.rollback()
        return jsonify(
            {
                "error": "記憶服務暫時無法使用；本次規劃條件仍可手動設定。",
                "code": "MEMORY_SERVICE_FAILED",
            }
        ), 500


@routes.get("/preference")
def get_preference():
    try:
        user_id = _validate_identity()
        return jsonify(_state(_row(get_db(), user_id), _now()))
    except MemoryProblem as error:
        return jsonify({"error": error.message, "code": error.code}), error.status


@routes.put("/preference")
def save_preference():
    def mutation(db, user_id):
        payload = _json_body(
            {"operationId", "expectedVersion", "value", "expiresInDays", "confirmed"}
        )
        if not _is_int(payload["expectedVersion"], 0) or not _is_int(
            payload["value"], 15, 240
        ) or not _is_int(payload["expiresInDays"], 1, 365):
            raise MemoryProblem(422, "MEMORY_INPUT_INVALID", "記憶值、版本或期限不合法。")
        fingerprint = _fingerprint("save", user_id, payload)
        previous = _previous_operation(db, payload["operationId"], fingerprint)
        if previous is not None:
            return previous

        now = _now()
        existing = _row(db, user_id)
        current_version = existing["version"] if existing else 0
        if payload["expectedVersion"] != current_version:
            raise MemoryProblem(
                409,
                "MEMORY_VERSION_CONFLICT",
                "記憶版本已變更，請重新讀取後再儲存。",
            )

        preference_id = existing["preference_id"] if existing else f"memory-{uuid4()}"
        version = current_version + 1
        expires_at = _iso(now + timedelta(days=payload["expiresInDays"]))
        updated_at = _iso(now)
        db.execute(
            """INSERT INTO study_preferences VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET
                 value=excluded.value,status=excluded.status,version=excluded.version,
                 expires_at=excluded.expires_at,updated_at=excluded.updated_at""",
            (
                user_id,
                preference_id,
                PREFERENCE_KEY,
                payload["value"],
                "active",
                version,
                expires_at,
                updated_at,
            ),
        )
        result = _state(_row(db, user_id), now)
        _save_operation(
            db,
            payload["operationId"],
            user_id,
            "save",
            fingerprint,
            result,
            now,
        )
        return {**result, "replayed": False}

    return _execute("save", mutation)


@routes.delete("/preference")
def withdraw_preference():
    def mutation(db, user_id):
        payload = _json_body(
            {"operationId", "expectedVersion", "confirmed"}
        )
        if not _is_int(payload["expectedVersion"], 1):
            raise MemoryProblem(422, "MEMORY_INPUT_INVALID", "記憶版本不合法。")
        fingerprint = _fingerprint("withdraw", user_id, payload)
        previous = _previous_operation(db, payload["operationId"], fingerprint)
        if previous is not None:
            return previous

        now = _now()
        existing = _row(db, user_id)
        if not _active(existing, now):
            raise MemoryProblem(404, "MEMORY_NOT_FOUND", "目前沒有可撤回的有效學習偏好。")
        if payload["expectedVersion"] != existing["version"]:
            raise MemoryProblem(
                409,
                "MEMORY_VERSION_CONFLICT",
                "記憶版本已變更，請重新讀取後再撤回。",
            )

        db.execute(
            """UPDATE study_preferences
               SET value=NULL,status='withdrawn',version=version+1,
                   expires_at=NULL,updated_at=? WHERE user_id=?""",
            (_iso(now), user_id),
        )
        result = _state(_row(db, user_id), now)
        _save_operation(
            db,
            payload["operationId"],
            user_id,
            "withdraw",
            fingerprint,
            result,
            now,
        )
        return {**result, "replayed": False}

    return _execute("withdraw", mutation)
