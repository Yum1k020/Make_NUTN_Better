"""Write sanitized live status for the midterm Gemini/ADC main flow."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.study_agent_api import StudyAgentService
from app.study_agent_vertex import VertexProviderError


TAIPEI = ZoneInfo("Asia/Taipei")


def synthetic_request():
    return {
        "startDate": "2026-09-17",
        "examDate": "2026-09-24",
        "hours": 6,
        "sessionHours": 2,
        "allowedPeriods": ["afternoon", "evening"],
        "courseName": "資料結構",
        "personalEvents": [
            {
                "id": "event-club",
                "title": "社團會議",
                "date": "2026-09-17",
                "start": "17:00",
                "end": "18:00",
                "location": "合成地點",
            }
        ],
    }


def source_version(repo: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def run() -> dict:
    repo = Path(__file__).resolve().parents[1]
    configured = {
        "project": bool(os.getenv("GOOGLE_CLOUD_PROJECT")),
        "location": bool(os.getenv("GOOGLE_CLOUD_LOCATION")),
        "model": bool(
            os.getenv("GOOGLE_CLOUD_GEMINI_MODEL") or os.getenv("GEMINI_MODEL")
        ),
    }
    evidence = {
        "schema_version": "midterm-live-v1",
        "executed_at": datetime.now(TAIPEI).isoformat(timespec="seconds"),
        "source_version": source_version(repo),
        "flow": "user request -> Gemini function call -> parameter validation -> deterministic tool -> functionResponse -> Gemini summary",
        "provider": "Google Cloud Vertex AI Gemini",
        "authentication": "Application Default Credentials",
        "input_kind": "synthetic",
        "configured": configured,
        "live_status": "LIVE_NOT_RUN",
        "reason_code": None,
        "actual_call": None,
        "result": None,
        "security": {
            "credentials_recorded": False,
            "tokens_recorded": False,
            "personal_data_recorded": False,
        },
    }
    if not configured["project"] or not configured["model"]:
        evidence["reason_code"] = "GOOGLE_CLOUD_PROJECT_OR_MODEL_NOT_CONFIGURED"
        return evidence
    try:
        result = StudyAgentService().run(synthetic_request())
        evidence["live_status"] = "LIVE_PASS"
        evidence["actual_call"] = {
            "completed": True,
            "model": result["agent"]["model"],
            "tool": result["agent"]["tool"],
            "authentication": "ADC",
        }
        evidence["result"] = {
            "workflow_status": result["workflow"]["status"],
            "scheduled_minutes": result["plan"]["scheduledMinutes"],
            "remaining_minutes": result["plan"]["remainingMinutes"],
            "session_count": len(result["plan"]["sessions"]),
            "citation_count": len(result["agent"]["citations"]),
        }
    except VertexProviderError as error:
        evidence["live_status"] = "LIVE_FAIL" if error.attempted else "LIVE_NOT_RUN"
        evidence["reason_code"] = error.code
        evidence["actual_call"] = {"attempted": error.attempted}
    except Exception as error:  # sanitized: never persist provider payloads
        evidence["live_status"] = "LIVE_FAIL"
        evidence["reason_code"] = type(error).__name__
        evidence["actual_call"] = {"attempted": True}
    return evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="docs/midterm/evidence/study-agent-live.json",
    )
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    output = repo / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    evidence = run()
    output.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(evidence["live_status"])
    print(output)


if __name__ == "__main__":
    main()
