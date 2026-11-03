from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

from backend.week04_tools import preview_study_plan

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "week04" / "evidence"
RESPONSES_URL = "https://api.openai.com/v1/responses"

TOOL_DECLARATION = {
    "type": "function",
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
            "busy_intervals": {"type": "array", "items": {"type": "object"}},
        },
        "required": [
            "plan_id",
            "start_date",
            "exam_date",
            "target_minutes",
            "session_minutes",
            "allowed_windows",
            "busy_intervals",
        ],
    },
}


def call_openai(api_key: str, body: dict) -> dict:
    try:
        response = requests.post(
            RESPONSES_URL,
            json=body,
            timeout=45,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as exc:
        status = getattr(exc.response, "status_code", "unknown")
        raise RuntimeError(f"OpenAI HTTP {status}") from None
    except requests.RequestException:
        raise RuntimeError("OpenAI connection error") from None


def output_text(response: dict) -> str:
    parts = []
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        parts.extend(
            part["text"]
            for part in item.get("content", [])
            if part.get("type") == "output_text" and isinstance(part.get("text"), str)
        )
    text = "\n".join(parts).strip()
    if not text:
        raise RuntimeError("OpenAI response did not contain text")
    return text


def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip()
    if not api_key or not model:
        raise SystemExit("Set OPENAI_API_KEY and OPENAI_MODEL in your private environment.")

    run_id = datetime.now(timezone.utc).strftime("LIVE-%Y%m%dT%H%M%SZ")
    trace = {
        "run_id": run_id,
        "provider": "openai",
        "model": model,
        "live_status": "LIVE_FAIL",
        "events": [],
    }
    user_text = (
        "請幫我產生複習排程預覽，不要儲存。"
        "plan_id=plan-001，2026-10-08 開始，2026-10-10 考試，"
        "需要 180 分鐘，每次 60 分鐘；10/8 09:00-13:00、"
        "10/9 09:00-12:00 可用；10/8 10:00-11:00 有作業系統課。"
    )

    try:
        first = call_openai(
            api_key,
            {
                "model": model,
                "input": user_text,
                "tools": [TOOL_DECLARATION],
                "tool_choice": {"type": "function", "name": "preview_study_plan"},
                "parallel_tool_calls": False,
                "store": False,
            },
        )
        calls = [item for item in first.get("output", []) if item.get("type") == "function_call"]
        if len(calls) != 1:
            raise RuntimeError("OpenAI did not return exactly one function call")
        function_call = calls[0]
        arguments = json.loads(function_call["arguments"])
        trace["events"].append(
            {"type": "model_function_call", "name": function_call.get("name"), "args": arguments}
        )
        if function_call.get("name") != "preview_study_plan":
            raise RuntimeError("unexpected tool selected")
        tool_result = preview_study_plan(**arguments)
        trace["events"].append({"type": "tool_result", "result": tool_result})

        second = call_openai(
            api_key,
            {
                "model": model,
                "instructions": "只能根據工具結果，以繁體中文簡短摘要；不得改寫排程。",
                "input": [
                    {"role": "user", "content": [{"type": "input_text", "text": user_text}]},
                    *first["output"],
                    {
                        "type": "function_call_output",
                        "call_id": function_call["call_id"],
                        "output": json.dumps(tool_result, ensure_ascii=False),
                    },
                ],
                "tools": [TOOL_DECLARATION],
                "tool_choice": "none",
                "store": False,
            },
        )
        summary = output_text(second)
        trace["events"].append({"type": "function_response_summary", "text": summary})
        trace["live_status"] = "LIVE_PASS"
        print(summary)
    except Exception as exc:
        trace["error_type"] = type(exc).__name__
        print(f"LIVE_FAIL: {type(exc).__name__}")

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out = EVIDENCE_DIR / f"{run_id}.json"
    out.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Evidence saved: {out}")


if __name__ == "__main__":
    main()
