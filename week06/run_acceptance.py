from __future__ import annotations

import json
from pathlib import Path

from backend.week04_tools import preview_study_plan
from backend.week06_chaining import run_study_plan_chaining

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "week04_plan.json"
OUT = ROOT / "week06" / "evidence" / "offline_comparison.json"


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _summary(preview: dict) -> str:
    return (
        f"已安排 {preview['scheduled_minutes']} 分鐘，"
        f"剩餘 {preview['remaining_minutes']} 分鐘；"
        "這是預覽，尚未寫入。"
    )


def main() -> None:
    request = _fixture()
    baseline = preview_study_plan(**request)

    candidate = run_study_plan_chaining(
        user_text="offline fixed case",
        extractor=lambda _text: request,
        summarizer=_summary,
    )

    empty_input = run_study_plan_chaining(
        user_text="",
        extractor=lambda _text: (_ for _ in ()).throw(AssertionError("extractor must not run")),
        summarizer=_summary,
    )

    def provider_down(_text: str) -> dict:
        raise RuntimeError("injected provider unavailable")

    provider_failure = run_study_plan_chaining(
        user_text="valid-looking request",
        extractor=provider_down,
        summarizer=_summary,
    )

    invalid_after_extract = dict(request)
    invalid_after_extract["session_minutes"] = 0
    gate_rejection = run_study_plan_chaining(
        user_text="extracted but invalid request",
        extractor=lambda _text: invalid_after_extract,
        summarizer=lambda _preview: (_ for _ in ()).throw(
            AssertionError("summarizer must not run after Gate rejection")
        ),
    )

    checks = {
        "offline_candidate_matches_baseline_preview": candidate["preview"] == baseline,
        "empty_input_rejected_before_model_or_tool": (
            empty_input["status"] == "rejected"
            and empty_input["counts"] == {
                "extractor_calls": 0,
                "preview_tool_calls": 0,
                "summarizer_calls": 0,
            }
        ),
        "provider_failure_has_finite_stop": (
            provider_failure["status"] == "failed"
            and provider_failure["stop_reason"] == "provider_failure"
            and provider_failure["counts"]["preview_tool_calls"] == 0
        ),
        "gate_rejection_stops_all_downstream": (
            gate_rejection["status"] == "rejected"
            and gate_rejection["stop_reason"] == "gate_rejected"
            and gate_rejection["counts"]["preview_tool_calls"] == 0
            and gate_rejection["counts"]["summarizer_calls"] == 0
        ),
    }

    artifact = {
        "workflow": "prompt_chaining",
        "baseline_sha": "e71192abdc329446fbd28414cda14c31d2f310c4",
        "same_input_fixture": "tests/fixtures/week04_plan.json",
        "business_endpoint": "read-only study-plan preview",
        "baseline_preview": baseline,
        "offline_candidate": candidate,
        "mandatory_case_status": {
            "case_1_normal_live": "LIVE_NOT_RUN",
            "case_2_illegal_input": "PASS_OFFLINE",
            "case_3_provider_failure": "PASS_INJECTED",
            "case_4_chaining_gate_boundary": "PASS_OFFLINE",
        },
        "cases": {
            "case_2_illegal_input": empty_input,
            "case_3_provider_failure": provider_failure,
            "case_4_chaining_gate_boundary": gate_rejection,
        },
        "checks": checks,
        "offline_all_pass": all(checks.values()),
        "live_note": (
            "The lecture requires the normal main-flow case to use a real Gemini request. "
            "CI has no private Gemini key, so offline fixtures do not claim LIVE_PASS."
        ),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    if not artifact["offline_all_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
