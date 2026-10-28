from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request

from backend.week04_tools import preview_study_plan

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "week04_plan.json"
EVIDENCE_DIR = ROOT / "week04" / "evidence"

TOOL_DECLARATION = {
    "name": "preview_study_plan",
    "description": "Read-only: generate a study-plan preview without persisting data.",
    "parameters": {
        "type": "object",
        "properties": {
            "plan_id": {"type": "string"},
            "start_date": {"type": "string"},
            "exam_date": {"type": "string"},
            "target_minutes": {"type": "integer"},
            "session_minutes": {"type": "integer"},
            "allowed_windows": {"type": "array", "items": {"type": "object"}},
            "busy_intervals": {"type": "array", "items": {"type": "object"}}
        },
        "required": [
            "plan_id", "start_date", "exam_date", "target_minutes",
            "session_minutes", "allowed_windows", "busy_intervals"
        ]
    }
}


def call_gemini(api_key: str, model: str, body: dict) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    req = request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=45) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini HTTP {exc.code}: {detail}") from exc


def first_content(response: dict) -> dict:
    return response["candidates"][0]["content"]


def find_function_call(content: dict) -> dict:
    for part in content.get("parts", []):
        if "functionCall" in part:
            return part["functionCall"]
    raise RuntimeError("Gemini did not return a functionCall")


def text_from_content(content: dict) -> str:
    return "\n".join(
        part.get("text", "")
        for part in content.get("parts", [])
        if part.get("text")
    ).strip()


def main() -> None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "").strip()
    if not api_key or not model:
        raise SystemExit("Set GEMINI_API_KEY and GEMINI_MODEL in your private environment.")

    run_id = datetime.now(timezone.utc).strftime("LIVE-%Y%m%dT%H%M%SZ")
    trace = {"run_id": run_id, "model": model, "live_status": "LIVE_FAIL", "events": []}

    user_text = (
        "請幫我產生複習排程預覽，不要儲存。"
        "plan_id=plan-001，2026-10-08 開始，2026-10-10 考試，"
        "需要 180 分鐘，每次 60 分鐘；10/8 09:00-13:00、"
        "10/9 09:00-12:00 可用；10/8 10:00-11:00 有作業系統課。"
    )

    try:
        body = {
            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
            "tools": [{"functionDeclarations": [TOOL_DECLARATION]}],
            "toolConfig": {
                "functionCallingConfig": {
                    "mode": "ANY",
                    "allowedFunctionNames": ["preview_study_plan"]
                }
            }
        }
        first = call_gemini(api_key, model, body)
        model_content = first_content(first)
        function_call = find_function_call(model_content)
        trace["events"].append({
            "type": "model_function_call",
            "name": function_call.get("name"),
            "args": function_call.get("args", {})
        })

        if function_call.get("name") != "preview_study_plan":
            raise RuntimeError("unexpected tool selected")

        tool_result = preview_study_plan(**function_call.get("args", {}))
        trace["events"].append({"type": "tool_result", "result": tool_result})

        second_body = {
            "contents": [
                {"role": "user", "parts": [{"text": user_text}]},
                model_content,
                {
                    "role": "user",
                    "parts": [{
                        "functionResponse": {
                            "name": "preview_study_plan",
                            "response": {"result": tool_result}
                        }
                    }]
                }
            ]
        }
        second = call_gemini(api_key, model, second_body)
        summary = text_from_content(first_content(second))
        trace["events"].append({"type": "function_response_summary", "text": summary})
        trace["live_status"] = "LIVE_PASS"
        print(summary)

    except Exception as exc:
        trace["error"] = str(exc)
        print(f"LIVE_FAIL: {exc}")

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE_DIR / f"{run_id}.json"
    out.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Evidence saved: {out}")


if __name__ == "__main__":
    main()
