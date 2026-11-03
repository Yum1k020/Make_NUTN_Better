"""Explicit bodyless POST for a bounded read-only explanation workflow."""

import sqlite3
import os

from flask import Blueprint, current_app, jsonify, request, session

from .db import get_db
from .graduation_explanation_core import explain
from .graduation_gemini import generate
from .planner_core import Problem, invalid, query
from .planner_graduation import progress
from .graduation_validity import context, lease, current_rule_digest

routes = Blueprint("graduation_explanations", __name__)


@routes.post("/api/v1/graduation-explanation")
def explanation_route():
    try:
        query({})
        same_origin()
        if request.get_data():
            invalid("body", "此操作不接受內容；使用目前使用者的資料")
        # Release the read transaction before waiting for the provider.
        db = get_db()
        db.execute("PRAGMA query_only = ON")
        db.execute("BEGIN")
        try:
            result = progress(db)
            initial = context(result, current_rule_digest(db, result["rule_set_id"]))
        finally:
            db.rollback()
        provider = current_app.config.get("GRADUATION_EXPLANATION_PROVIDER", generate) if current_app.testing else generate
        output = explain(result, provider)
        # Check again after provider I/O: data may have changed while it ran.
        db.execute("BEGIN")
        try:
            latest = progress(db)
            final = context(latest, current_rule_digest(db, latest["rule_set_id"]))
        finally:
            db.rollback()
        if final["source_sha256"] != initial["source_sha256"]:
            output.update(status="stale", stop_reason="SOURCE_CHANGED", explanation=[])
            result = latest
        output["validity"] = lease(initial)
        if final["server_now_ms"] >= output["validity"]["expires_at_ms"]:
            output.update(status="stale", stop_reason="EXPIRED", explanation=[])

        current_app.logger.info("graduation explanation completed", extra={
            "run_id": output["run_id"], "stop_reason": output["stop_reason"], "model_calls": output["model_calls"]})
        response = jsonify(data={"progress": result, "workflow": output})
        response.headers["Cache-Control"] = "no-store"
        return response
    except Problem as error:
        return jsonify(error={"code": error.code, "message": error.message, "fields": error.fields}), error.status
    except (ValueError, TypeError, KeyError, sqlite3.Error):
        return jsonify(error={"code": "GRADUATION_DATA_ERROR", "message": "無法讀取畢業進度，請確認規則與資料庫", "fields": []}), 500



def same_origin():
    origin = request.headers.get("Origin")
    allowed = {request.host_url.rstrip("/")} | {
        value.strip() for value in os.environ.get("GRADUATION_ALLOWED_ORIGINS", "").split(",") if value.strip()}
    if request.headers.get("Sec-Fetch-Site") == "cross-site" or (origin and origin not in allowed):
        raise Problem(403, "CROSS_ORIGIN_DENIED", "請從本系統頁面產生說明")


def read_current():
    db = get_db()
    db.execute("PRAGMA query_only = ON")
    db.execute("BEGIN")
    try:
        result = progress(db)
        return context(result, current_rule_digest(db, result["rule_set_id"]))
    finally:
        db.rollback()


@routes.get("/api/v1/graduation-context")
def context_route():
    try:
        query({})
        same_origin()
        if request.get_data():
            invalid("body", "此操作不接受內容")
        response = jsonify(data=read_current())
        response.headers["Cache-Control"] = "no-store"
        return response
    except Problem as error:
        return jsonify(error={"code": error.code, "message": error.message, "fields": error.fields}), error.status
    except (ValueError, TypeError, KeyError, sqlite3.Error):
        return jsonify(error={"code": "GRADUATION_DATA_ERROR", "message": "無法確認目前資料，舊說明暫停使用"}), 500


@routes.post("/api/v1/graduation-session/reset")
def reset_route():
    try:
        query({})
        same_origin()
        if request.get_data():
            invalid("body", "此操作不接受內容")
        session.pop("graduation_scope", None)
        return jsonify(data=read_current())
    except Problem as error:
        return jsonify(error={"code": error.code, "message": error.message, "fields": error.fields}), error.status
    except (ValueError, TypeError, KeyError, sqlite3.Error):
        return jsonify(error={"code": "GRADUATION_DATA_ERROR", "message": "無法建立新工作階段"}), 500


def register(app, api):
    app.register_blueprint(routes)
    for endpoint, path, method, summary in (
        ("context_route", "/api/v1/graduation-context", "get", "重查工作階段與畢業來源指紋；無模型呼叫"),
        ("reset_route", "/api/v1/graduation-session/reset", "post", "開始新說明工作階段；不修改修課或規則資料"),
    ):
        route = next(r for r in app.url_map.iter_rules() if r.endpoint == "graduation_explanations." + endpoint)
        api.spec.path(path=path, rule=route, operations={method: {
            "summary": summary, "tags": ["graduation"],
            "responses": {"200": {"description": "scope_id、source_sha256、server_now_ms；Cache-Control: no-store"},
                          "422": {"description": "不接受額外輸入"}, "403": {"description": "拒絕跨來源"},
                          "500": {"description": "資料無效；不得沿用舊說明"}}}})
    rule = next(rule for rule in app.url_map.iter_rules() if rule.endpoint == "graduation_explanations.explanation_route")
    api.spec.path(path="/api/v1/graduation-explanation", rule=rule, operations={"post": {
        "summary": "使用目前規則的去識別摘要產生說明；最多修正一次，無資料庫寫入",
        "tags": ["graduation"],
        "responses": {"200": {"description": "data.progress 與 data.workflow：來源、A/B、評估、停止原因、用量；失敗回退基本進度"},
                      "422": {"description": "不接受 query 或 request body，模型呼叫 0 次"},
                      "403": {"description": "拒絕其他網站觸發模型呼叫"},
                      "500": {"description": "規則或資料庫錯誤，模型呼叫 0 次"}}}})
