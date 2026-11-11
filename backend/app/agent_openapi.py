"""Public request/response contract registered in the existing Swagger document."""

from .planner_openapi import resource_schema


def register_docs(app, api):
    by_path = {rule.rule.replace("<string:run_id>", "{run_id}"): rule for rule in app.url_map.iter_rules()}
    plan = resource_schema("study-plans")
    plan["properties"].pop("exam_task_id", None)
    plan["properties"]["target_minutes"]["maximum"] = 14400
    plan["properties"]["session_minutes"].update(minimum=15, maximum=240)
    plan["properties"]["allowed_windows"]["maxItems"] = 28
    request = {"type": "object", "additionalProperties": False, "required": ["provider", "architecture", "plan"],
               "properties": {"provider": {"type": "string", "enum": ["offline", "openai"]},
                              "architecture": {"type": "string", "enum": ["single", "multi"]}, "plan": plan}}
    api.spec.components.schema("AgentRunRequest", request)
    operations = [
        ("/config", "get", "角色、上限與 OpenAI 設定狀態", None, 200),
        ("/examples", "get", "可重現的請求範例，不寫入資料", None, 200),
        ("/runs", "get", "最近 20 筆本人的執行摘要", None, 200),
        ("/runs", "post", "同步執行並保存證據；201 也可能包含 status=failed，必須檢查 data.status", {"$ref": "#/components/schemas/AgentRunRequest"}, 201),
        ("/runs/{run_id}", "get", "讀取結果、工具紀錄、來源與原始驗證", None, 200),
        ("/runs/{run_id}/verify", "post", "重新檢查目前課表，無 request body、不改寫紀錄", None, 200),
        ("/runs/{run_id}/commit", "post", "明確確認後原子儲存；重送回 200，不重複新增", {
            "type": "object", "additionalProperties": False, "required": ["confirmed"],
            "properties": {"confirmed": {"type": "boolean", "enum": [True]}}}, 201),
    ]
    for path, method, summary, schema, status in operations:
        op = {"tags": ["Study agents"], "summary": summary, "responses": {
            str(status): {"description": "成功；資料在 data 中。完整欄位說明見 docs/week08/README.md", "content": {
                "application/json": {"schema": {"type": "object", "required": ["data"], "properties": {"data": {}}}}}},
            **{str(code): {"description": description} for code, description in (
                (400, "JSON 錯誤"), (404, "紀錄不存在"), (409, "版本／驗證衝突"),
                (415, "需要 application/json"), (422, "契約不合法"), (503, "OpenAI 未設定"))}}}
        if "{run_id}" in path:
            op["parameters"] = [{"name": "run_id", "in": "path", "required": True, "schema": {"type": "string"}}]
        if schema:
            op["requestBody"] = {"required": True, "content": {"application/json": {"schema": schema}}}
        if path.endswith("/commit"):
            op["responses"]["200"] = {"description": "已確認紀錄的冪等重送"}
        api.spec.path(path="/api/v1/agent" + path, rule=by_path["/api/v1/agent" + path], operations={method: op})
