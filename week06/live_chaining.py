from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from backend.week06_chaining import run_study_plan_chaining
from week06.gemini_client import GeminiChainingClient

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "week06" / "evidence"

USER_TEXT = (
    "請幫我產生複習排程預覽，不要儲存。"
    "plan_id=plan-001，2026-10-08 開始，2026-10-10 考試，"
    "需要 180 分鐘，每次 60 分鐘；"
    "10/8 09:00-13:00、10/9 09:00-12:00 可用；"
    "10/8 10:00-11:00 有作業系統課，"
    "source_type=class，source_id=class-os。"
)


def main() -> None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "").strip()
    run_id = datetime.now(timezone.utc).strftime("W06-LIVE-%Y%m%dT%H%M%SZ")

    trace: dict = {
        "run_id": run_id,
        "workflow": "prompt_chaining",
        "model": model or None,
        "live_status": "LIVE_NOT_RUN",
        "user_text": USER_TEXT,
    }

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    if not api_key or not model:
        trace["reason"] = "missing GEMINI_API_KEY or GEMINI_MODEL"
        out = EVIDENCE_DIR / f"{run_id}.json"
        out.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
        print("LIVE_NOT_RUN: set GEMINI_API_KEY and GEMINI_MODEL in your private environment.")
        print(f"Evidence saved: {out}")
        return

    client = GeminiChainingClient(api_key=api_key, model=model)
    result = run_study_plan_chaining(
        user_text=USER_TEXT,
        extractor=client.extract_study_plan_request,
        summarizer=client.summarize_preview,
    )

    trace["provider_calls"] = client.calls
    trace["workflow_result"] = result
    trace["live_status"] = "LIVE_PASS" if result["status"] == "answer_ready" else "LIVE_FAIL"

    out = EVIDENCE_DIR / f"{run_id}.json"
    out.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")

    print(trace["live_status"])
    if result.get("answer"):
        print(result["answer"])
    if result.get("errors"):
        print("\n".join(result["errors"]))
    print(f"Evidence saved: {out}")


if __name__ == "__main__":
    main()
