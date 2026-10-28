from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request

from backend.week07_memory import preview_with_memory, save_confirmed_preference

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "week07" / "evidence"
RUNTIME_DIR = ROOT / "week07" / "runtime"
STORE = RUNTIME_DIR / "memory.json"
FIXTURE = ROOT / "tests" / "fixtures" / "week04_plan.json"


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


def response_text(payload: dict) -> str:
    parts = payload["candidates"][0]["content"]["parts"]
    text = "\n".join(part.get("text", "") for part in parts if part.get("text")).strip()
    if not text:
        raise RuntimeError("Gemini response did not contain text")
    return text


def main() -> None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "").strip()
    run_id = datetime.now(timezone.utc).strftime("W07-LIVE-%Y%m%dT%H%M%SZ")
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    trace = {
        "run_id": run_id,
        "route": "A_confirmed_preference",
        "model": model or None,
        "live_status": "LIVE_NOT_RUN",
        "events": [],
    }

    if not api_key or not model:
        trace["reason"] = "missing GEMINI_API_KEY or GEMINI_MODEL"
        out = EVIDENCE_DIR / f"{run_id}.json"
        out.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
        print("LIVE_NOT_RUN: set GEMINI_API_KEY and GEMINI_MODEL.")
        print(f"Evidence saved: {out}")
        return

    user_text = "請記住我之後安排複習時，每次以 60 分鐘為一段。"
    try:
        extract_prompt = (
            "把使用者明確提出的複習時段偏好抽成 JSON。"
            "只允許 preference_type=study_session_minutes，value 必須是整數分鐘。"
            "若沒有明確值不要猜。只輸出 JSON。\nUser: " + user_text
        )
        first = call_gemini(
            api_key,
            model,
            {
                "contents": [{"role": "user", "parts": [{"text": extract_prompt}]}],
                "generationConfig": {
                    "temperature": 0,
                    "responseMimeType": "application/json",
                },
            },
        )
        proposal = json.loads(response_text(first))
        trace["events"].append({"type": "gemini_proposal", "proposal": proposal})

        if proposal.get("preference_type") != "study_session_minutes":
            raise RuntimeError("unexpected preference_type")
        value = proposal.get("value")
        if isinstance(value, bool) or not isinstance(value, int):
            raise RuntimeError("Gemini proposal value must be an integer")

        print(json.dumps(proposal, ensure_ascii=False, indent=2))
        decision = input("確認保存這項偏好？只有輸入 YES 才寫入：").strip()
        confirmed = decision == "YES"
        trace["events"].append({"type": "human_confirmation", "confirmed": confirmed})

        save_result = save_confirmed_preference(
            owner_id="U001",
            actor_id="U001",
            value=value,
            source_id=run_id,
            request_id=f"{run_id}-SAVE",
            confirmed=confirmed,
            store_path=STORE,
            now="2026-10-28T10:00:00",
            expires_at="2026-12-31T23:59:59",
        )
        trace["events"].append({"type": "memory_write_result", "result": save_result})

        if not save_result["executed"]:
            trace["live_status"] = "LIVE_FAIL"
            trace["reason"] = save_result["status"]
        else:
            plan_request = json.loads(FIXTURE.read_text(encoding="utf-8"))
            plan_request["session_minutes"] = None
            new_session = preview_with_memory(
                request=plan_request,
                owner_id="U001",
                reader_id="U001",
                store_path=STORE,
                now="2026-10-28T10:05:00",
            )
            trace["events"].append({"type": "new_session_memory_read_and_preview", "result": new_session})

            summary_prompt = (
                "請根據這個工具結果，用繁體中文簡短說明："
                "讀回了哪個偏好版本、排程用了幾分鐘為一段、總共安排幾分鐘。"
                "不要補猜；並說明偏好只用於排程設定。\n"
                + json.dumps(new_session, ensure_ascii=False)
            )
            second = call_gemini(
                api_key,
                model,
                {
                    "contents": [{"role": "user", "parts": [{"text": summary_prompt}]}],
                    "generationConfig": {"temperature": 0},
                },
            )
            summary = response_text(second)
            trace["events"].append({"type": "gemini_summary", "text": summary})
            trace["live_status"] = "LIVE_PASS"
            print(summary)

    except Exception as exc:
        trace["live_status"] = "LIVE_FAIL"
        trace["error"] = str(exc)
        print(f"LIVE_FAIL: {exc}")

    out = EVIDENCE_DIR / f"{run_id}.json"
    out.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Evidence saved: {out}")


if __name__ == "__main__":
    main()
