from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from backend.app.study_agent_api import StudyAgentService
from backend.app.study_agent_openai import (
    EXPERT_CONTEXT_BASELINE,
    EXPERT_CONTEXT_CANDIDATE,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "week09" / "evidence" / "offline_comparison.json"


def fixed_request() -> dict:
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
                "location": "活動中心 3 樓",
            }
        ],
    }


class OfflineComparisonProvider:
    provider_name = "offline-injected"
    authentication = "none"
    framework = "offline-injected"

    def __init__(self) -> None:
        self.config = SimpleNamespace(model="offline-week09-stub")
        self.packets: list[dict] = []

    def review_plan(self, packet, *, context_variant=EXPERT_CONTEXT_CANDIDATE):
        self.packets.append(packet)
        assessment = (
            "concentrated"
            if context_variant == EXPERT_CONTEXT_BASELINE
            else "balanced"
        )
        return (
            {
                "assessment": assessment,
                "summary": f"{context_variant} 的離線注入輸出。",
                "recommendations": [],
                "citations": ["planner-rule", "study-load-review"],
            },
            {
                "usage": {},
                "contextVersion": context_variant,
            },
        )


def main() -> None:
    provider = OfflineComparisonProvider()
    service = StudyAgentService(provider_factory=lambda: provider)
    result = service.compare_context(fixed_request())

    evidence = {
        "schema_version": "week09-offline-comparison-v1",
        "method": "few-shot prompting",
        "baseline_sha": "cf7376f97c6a85129c796580957df589512e2ef2",
        "input": fixed_request(),
        "comparison": result,
        "checks": {
            "same_expert_packet": provider.packets[0] == provider.packets[1],
            "same_deterministic_plan": result["sharedContext"]["sameDeterministicPlan"],
            "baseline_version": (
                result["versions"]["baseline"]["contextVersion"]
                == EXPERT_CONTEXT_BASELINE
            ),
            "candidate_version": (
                result["versions"]["candidate"]["contextVersion"]
                == EXPERT_CONTEXT_CANDIDATE
            ),
            "baseline_failed_fixed_metric": (
                result["versions"]["baseline"]["evaluation"]["pass"] is False
            ),
            "candidate_passed_fixed_metric": (
                result["versions"]["candidate"]["evaluation"]["pass"] is True
            ),
        },
        "offline_all_pass": False,
        "evidence_kind": "OFFLINE_INJECTED",
        "live_status": "LIVE_NOT_RUN",
        "note": (
            "This proves the comparison plumbing and fixed evaluator only. "
            "It is not evidence that a real model improved."
        ),
    }
    evidence["offline_all_pass"] = all(evidence["checks"].values())

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    if not evidence["offline_all_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
