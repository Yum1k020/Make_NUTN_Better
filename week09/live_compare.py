from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from backend.app.study_agent_api import StudyAgentService
from week09.run_acceptance import fixed_request

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "week09" / "evidence"


def main() -> None:
    if not os.getenv("OPENAI_API_KEY", "").strip():
        print("LIVE_NOT_RUN: OPENAI_API_KEY is not configured.")
        return

    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence = {
        "schema_version": "week09-live-v1",
        "run_at_utc": run_stamp,
        "input_kind": "synthetic",
        "live_status": "LIVE_FAIL",
    }
    try:
        result = StudyAgentService().compare_context(fixed_request())
        evidence.update(
            {
                "live_status": "LIVE_PASS",
                "provider": "OpenAI Responses API",
                "model": result["model"],
                "comparison": result,
                "credentials_recorded": False,
            }
        )
    except Exception as error:
        evidence.update(
            {
                "error_type": type(error).__name__,
                "error": str(error),
                "credentials_recorded": False,
            }
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"W09-LIVE-{run_stamp}.json"
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(evidence["live_status"])
    print(f"Evidence: {out}")


if __name__ == "__main__":
    main()
