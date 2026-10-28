"""Explicit bodyless POST for a bounded read-only explanation workflow."""

import sqlite3
import os

from flask import Blueprint, current_app, jsonify, request

from .db import get_db
from .graduation_explanation_core import explain
from .graduation_gemini import generate
from .planner_core import Problem, invalid, query
from .planner_graduation import progress

routes = Blueprint("graduation_explanations", __name__)


@routes.post("/api/v1/graduation-explanation")
def explanation_route():
    try:
        query({})
        origin = request.headers.get("Origin")
        allowed = {request.host_url.rstrip("/")} | {
            value.strip() for value in os.environ.get("GRADUATION_ALLOWED_ORIGINS", "").split(",") if value.strip()}
        if request.headers.get("Sec-Fetch-Site") == "cross-site" or (origin and origin not in allowed):
            raise Problem(403, "CROSS_ORIGIN_DENIED", "請從本系統頁面產生說明")
        if request.get_data():
            invalid("body", "此操作不接受內容；使用目前使用者的資料")
        # Release the read transaction before waiting for the provider.
        db = get_db()
        db.execute("PRAGMA query_only = ON")
        db.execute("BEGIN")
        try:
            result = progress(db)
        finally:
            db.rollback()
        provider = current_app.config.get("GRADUATION_EXPLANATION_PROVIDER", generate) if current_app.testing else generate
        output = explain(result, provider)
        current_app.logger.info("graduation explanation completed", extra={
            "run_id": output["run_id"], "stop_reason": output["stop_reason"], "model_calls": output["model_calls"]})
        return jsonify(data={"progress": result, "workflow": output})
    except Problem as error:
        return jsonify(error={"code": error.code, "message": error.message, "fields": error.fields}), error.status
    except (ValueError, TypeError, KeyError, sqlite3.Error):
        return jsonify(error={"code": "GRADUATION_DATA_ERROR", "message": "無法讀取畢業進度，請確認規則與資料庫", "fields": []}), 500


def register(app, api):
    app.register_blueprint(routes)
    rule = next(rule for rule in app.url_map.iter_rules() if rule.endpoint == "graduation_explanations.explanation_route")
    api.spec.path(path="/api/v1/graduation-explanation", rule=rule, operations={"post": {
        "summary": "使用目前規則的去識別摘要產生說明；最多修正一次，無資料庫寫入",
        "tags": ["graduation"],
        "responses": {"200": {"description": "data.progress 與 data.workflow：來源、A/B、評估、停止原因、用量；失敗回退基本進度"},
                      "422": {"description": "不接受 query 或 request body，模型呼叫 0 次"},
                      "403": {"description": "拒絕其他網站觸發模型呼叫"},
                      "500": {"description": "規則或資料庫錯誤，模型呼叫 0 次"}}}})
