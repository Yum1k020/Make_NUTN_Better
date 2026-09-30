"""OpenAPI request contracts for the planner; shares the editable field allowlists."""

from copy import deepcopy

from .planner_core import RESOURCE


def obj(properties, required=(), **extra):
    return {"type": "object", "properties": properties, "required": list(required), "additionalProperties": False, **extra}


def array(items, minimum=0):
    return {"type": "array", "items": items, "minItems": minimum}


def enum(*values):
    return {"type": "string", "enum": list(values)}


TEXT = {"type": "string", "minLength": 1}
DATE = {"type": "string", "format": "date"}
DATETIME = {"type": "string", "format": "date-time", "description": "必須包含時差；回傳統一為 Asia/Taipei"}
TIME = {"type": "string", "pattern": "^(?:[01][0-9]|2[0-3]):[0-5][0-9]$"}
POSITIVE = {"type": "integer", "minimum": 1}
VERSION = {**POSITIVE, "description": "須與目前計畫版本相同；過期回傳 409"}
WEEKLY = obj({"weekday": {"type": "integer", "minimum": 1, "maximum": 7}, "start_time": TIME, "end_time": TIME}, ["weekday", "start_time", "end_time"])
MEETING = deepcopy(WEEKLY)
MEETING["properties"].update({"campus_id": {**TEXT, "nullable": True}, "location": {"type": "string", "nullable": True}})
INTERVAL = obj({"starts_at": DATETIME, "ends_at": DATETIME}, ["starts_at", "ends_at"])
SESSION = obj({"title": {"type": "string", "minLength": 1, "maxLength": 200}, "starts_at": DATETIME, "ends_at": DATETIME}, ["title", "starts_at", "ends_at"])


def resource_schema(kind, patch=False):
    _, fields, required, _ = RESOURCE[kind]
    properties = {}
    for key, (_, nullable) in fields.items():
        schema = TEXT
        if key in ("start_date", "exam_date", "due_date"):
            schema = DATE
        elif key == "due_time":
            schema = TIME
        elif key in ("starts_at", "ends_at"):
            schema = DATETIME
        elif key in ("target_minutes", "session_minutes"):
            schema = POSITIVE
        elif key == "title":
            schema = {"type": "string", "minLength": 1, "maxLength": 200}
        elif key in ("passed", "completed"):
            schema = {"type": "boolean"}
        elif key == "grade":
            schema = {"type": "number", "minimum": 0, "maximum": 100}
        elif key == "enrollment_status":
            schema = enum("in_progress", "finished")
        elif key == "type":
            schema = enum("todo", "assignment", "report", "exam", "review")
        elif key == "meetings":
            schema = array(MEETING, 1)
        elif key == "allowed_windows":
            schema = array(WEEKLY, 1)
        properties[key] = {**deepcopy(schema), "nullable": nullable}
    result = obj(properties, () if patch else required, minProperties=1)
    if kind == "timetable-entries":
        result["description"] = "offering_id 模式與手動 meetings 互斥；catalog 模式不可提供 section_name 或 meetings。"
    if kind == "enrollments":
        result["description"] = "finished 必須提供 boolean passed；in_progress 的 passed、grade 必須為 null；成績與 passed 必須一致。"
    return result


def register_docs(app, api):
    from flask_smorest.spec.plugins import FlaskPlugin

    by_path = {FlaskPlugin.flaskpath2openapi(rule.rule): rule for rule in app.url_map.iter_rules()}

    def add_path(path, operations):
        api.spec.path(path=path, rule=by_path[path], operations=operations)
    def operation(summary, status=200, schema=None, params=(), output=None):
        responses = {str(status): {"description": "成功；204 無回應內容"}}
        if status != 204:
            responses[str(status)]["content"] = {"application/json": {"schema": output or {"type": "object", "required": ["data"], "properties": {"data": {"type": "object"}}}}}
        for code in (400, 404, 409, 415, 422, 500):
            responses[str(code)] = {"description": "依 API 契約回傳错误，失敗寫入不留下部分更新",
                                   "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ProfileError"}}}}
        result = {"summary": summary, "tags": ["planner"], "responses": responses}
        if params:
            result["parameters"] = list(params)
        if schema is not None:
            result["requestBody"] = {"required": True, "content": {"application/json": {"schema": schema}}}
        return result

    def param(name, schema=TEXT, required=False, location="query"):
        return {"name": name, "in": location, "required": required, "schema": schema}

    list_output = {"type": "object", "required": ["data", "meta"],
                   "properties": {"data": {"type": "array", "items": {"type": "object"}}, "meta": obj({"count": {"type": "integer", "minimum": 0}}, ["count"])}}
    filters = {
        "enrollments": [param("semester_id"), param("enrollment_status", enum("in_progress", "finished"))],
        "timetable-entries": [param("semester_id")],
        "tasks": [param("from", DATE), param("to", DATE), param("completed", enum("true", "false")), param("course_id")],
        "personal-events": [param("from", DATETIME), param("to", DATETIME)],
        "study-plans": [], "planned-courses": [param("target_semester_id")],
    }
    for kind, parameters in filters.items():
        add_path(path="/api/v1/" + kind, operations={
            "get": operation("本人資源清單：" + kind, params=parameters, output=list_output),
            "post": operation("新增：" + kind, 201, resource_schema(kind))})
        params = [param("resource_id", required=True, location="path")]
        add_path(path="/api/v1/" + kind + "/{resource_id}", operations={
            "get": operation("本人資源詳情", params=params),
            "patch": operation("部分修改；未提供欄位保留原值", schema=resource_schema(kind, True), params=params),
            "delete": operation("刪除；關聯限制回傳 409", 204, params=params)})
    specs = [
        ("/calendar", "get", "日／週行事曆，最多 31 個日曆日", None, [param("from", DATE, True), param("to", DATE, True)]),
        ("/schedule/conflicts", "post", "唯讀衝突預覽；未知課表回 check_complete=false", obj({**INTERVAL["properties"],
            "exclude_source": obj({"source_type": enum("class", "personal_event", "study_session"), "source_id": TEXT}, ["source_type", "source_id"])}, INTERVAL["required"]), []),
        ("/schedule/availability", "post", "最多 60 天；可用視窗先合併再扣除佔用", obj({"from": DATETIME, "to": DATETIME,
            "allowed_windows": array(INTERVAL, 1), "min_duration_minutes": {**POSITIVE, "default": 1}}, ["from", "to", "allowed_windows"]), []),
        ("/study-plans/{plan_id}/generate", "post", "生成候選，不保存；此端點不接受 body", None, [param("plan_id", required=True, location="path")]),
        ("/study-plans/{plan_id}/sessions", "get", "已保存時段、版本與時數摘要", None, [param("plan_id", required=True, location="path")]),
        ("/study-plans/{plan_id}/sessions", "put", "整組取代，空陣列代表清空", obj({"plan_version": VERSION, "sessions": array(SESSION)}, ["plan_version", "sessions"]), [param("plan_id", required=True, location="path")]),
        ("/study-sessions/{session_id}", "patch", "調整單筆時段並驗證整組安排", obj({"plan_version": VERSION, **SESSION["properties"]}, ["plan_version"], minProperties=2), [param("session_id", required=True, location="path")]),
        ("/study-sessions/{session_id}", "delete", "刪除時段並增加版本", None, [param("session_id", required=True, location="path"), param("plan_version", VERSION, True)]),
        ("/planned-courses/check", "post", "唯讀檢查候選，問題仍回 200", obj({"target_semester_id": TEXT,
            "items": array(obj({"course_id": TEXT, "offering_id": {**TEXT, "nullable": True}}, ["course_id"]), 1)}, ["target_semester_id", "items"]), []),
        ("/graduation-rules/{rule_id}", "get", "團隊草案規則；未映射課程不虛構 ID", None, [param("rule_id", required=True, location="path")]),
        ("/programs", "get", "學程條件清單，未映射為 needs_confirmation", None, [param("rule_set_id", required=True)]),
        ("/lecture-progress", "get", "本人講座場次，未填為 null", None, []),
        ("/lecture-progress", "put", "完整取代兩類講座場次", obj({key: {"type": "integer", "minimum": 0, "nullable": True} for key in ("professional_count", "general_count")}, ["professional_count", "general_count"]), []),
        ("/graduation-progress", "get", "依 /me 規則計算；非正式校方認證", None, []),
        ("/dashboard", "get", "由同一詳細資料來源計算摘要", None, [param("date", DATE, True)]),
        ("/campus-maps", "get", "靜態校區圖片設定", None, [param("campus_id")]),
    ]
    for path, method, summary, schema, params in specs:
        add_path(path="/api/v1" + path, operations={method: operation(summary, 204 if method == "delete" else 200, schema, params,
            list_output if path in ("/programs", "/campus-maps") else None)})
