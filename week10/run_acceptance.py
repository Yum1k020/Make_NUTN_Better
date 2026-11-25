from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from backend.app.study_agent_api import StudyAgentService
from backend.app.study_agent_contract import TOOL_NAME
from backend.app.study_agent_openai import EXPERT_CONTEXT_CANDIDATE

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "week10" / "evidence" / "offline_data_package.json"


def fixed_request() -> dict:
    return {
        "startDate": "2026-11-25",
        "examDate": "2026-12-02",
        "hours": 4,
        "sessionHours": 2,
        "allowedPeriods": ["afternoon", "evening"],
        "courseName": "資料結構",
        "weeklyClasses": [
            {
                "id": "backend-class-001",
                "title": "計算機組織",
                "weekday": 3,
                "start": "14:00",
                "end": "16:00",
                "location": "J201",
            }
        ],
        "personalEvents": [
            {
                "id": "backend-event-001",
                "title": "不應進入資料包的私人文字",
                "date": "2026-11-25",
                "start": "18:00",
                "end": "19:00",
                "location": "不應進入資料包的私人地點",
            }
        ],
    }


class OfflineProvider:
    provider_name = "offline-injected"
    authentication = "none"
    framework = "offline-injected"

    def __init__(self) -> None:
        self.config = SimpleNamespace(model="offline-week10-stub")

    def choose_tool(self, data):
        return (
            {"name": TOOL_NAME, "args": data},
            [{"role": "user", "content": [{"type": "input_text", "text": "synthetic"}]}],
            {"usage": {}},
        )

    def review_plan(self, packet, *, context_variant=EXPERT_CONTEXT_CANDIDATE):
        remaining = packet["plan"]["remainingMinutes"]
        assessment = "insufficient" if remaining > 0 else "balanced"
        return (
            {
                "assessment": assessment,
                "summary": "離線驗收用受限專家輸出。",
                "recommendations": [],
                "citations": ["planner-rule", "study-load-review"],
            },
            {"usage": {}, "contextVersion": context_variant},
        )

    def summarize(self, history, plan, expert_review=None):
        return (
            {
                "summary": "離線驗收完成。",
                "warnings": [],
                "citations": [
                    "planner-rule",
                    "weekly-classes-backend-sqlite",
                    "planner-backend-sqlite",
                ],
                "refused": False,
            },
            {"usage": {}},
        )


def main() -> None:
    result = StudyAgentService(provider_factory=OfflineProvider).run(fixed_request())
    package = result["dataPackage"]
    serialized_events = json.dumps(
        package["environment"]["personalEvents"]["records"],
        ensure_ascii=False,
    )

    evidence = {
        "schema_version": "week10-offline-v1",
        "baseline_sha": "1b5124f9ab212f5efefc10dd4997cd65661aae6f",
        "evidence_kind": "OFFLINE_INJECTED",
        "task": fixed_request(),
        "dataPackage": package,
        "checks": {
            "backend_timetable_integrated": (
                package["environment"]["weeklyClasses"]["source"]
                == "flask-sqlite:academic-timetable"
                and package["environment"]["weeklyClasses"]["count"] == 1
            ),
            "backend_personal_events_integrated": (
                package["environment"]["personalEvents"]["source"]
                == "flask-sqlite:personal-events"
                and package["environment"]["personalEvents"]["count"] == 1
            ),
            "private_event_text_redacted": (
                "不應進入資料包的私人文字" not in serialized_events
                and "不應進入資料包的私人地點" not in serialized_events
            ),
            "trajectory_recorded": package["trajectory"]["stepCount"] == 7,
            "verifier_passed": package["verifier"]["passed"] is True,
            "credentials_excluded": (
                package["provenance"]["credentialsIncluded"] is False
            ),
            "classmate_data_marked": (
                package["provenance"]["integratesClassmateData"] is True
            ),
        },
    }
    evidence["offline_all_pass"] = all(evidence["checks"].values())

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    if not evidence["offline_all_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
