from __future__ import annotations

import json
from pathlib import Path

from backend.week04_tools import preview_study_plan
from backend.week06_chaining import run_study_plan_chaining

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "week04_plan.json"


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _summary(preview: dict) -> str:
    return (
        f"已安排 {preview['scheduled_minutes']} 分鐘，"
        f"剩餘 {preview['remaining_minutes']} 分鐘；這是預覽，尚未寫入。"
    )


def test_offline_candidate_preserves_original_preview_endpoint():
    request = _fixture()
    baseline = preview_study_plan(**request)

    result = run_study_plan_chaining(
        user_text="offline fixed case",
        extractor=lambda _text: request,
        summarizer=_summary,
    )

    assert result["status"] == "answer_ready"
    assert result["stop_reason"] == "completed"
    assert result["preview"] == baseline
    assert result["counts"] == {
        "extractor_calls": 1,
        "preview_tool_calls": 1,
        "summarizer_calls": 1,
    }


def test_case2_empty_input_rejects_before_model_and_tool():
    def should_not_run(_value):
        raise AssertionError("downstream stage must not run")

    result = run_study_plan_chaining(
        user_text="   ",
        extractor=should_not_run,
        summarizer=should_not_run,
    )

    assert result["status"] == "rejected"
    assert result["stop_reason"] == "invalid_input"
    assert result["counts"] == {
        "extractor_calls": 0,
        "preview_tool_calls": 0,
        "summarizer_calls": 0,
    }


def test_case3_provider_failure_stops_without_fabricating_result():
    def provider_down(_text: str) -> dict:
        raise RuntimeError("injected provider unavailable")

    result = run_study_plan_chaining(
        user_text="valid-looking request",
        extractor=provider_down,
        summarizer=_summary,
    )

    assert result["status"] == "failed"
    assert result["stop_reason"] == "provider_failure"
    assert result["preview"] is None
    assert result["answer"] is None
    assert result["counts"]["extractor_calls"] == 1
    assert result["counts"]["preview_tool_calls"] == 0
    assert result["counts"]["summarizer_calls"] == 0


def test_case4_gate_rejection_keeps_downstream_stages_at_zero():
    request = _fixture()
    request["session_minutes"] = 0

    def should_not_summarize(_preview):
        raise AssertionError("summarizer must not run after Gate rejection")

    result = run_study_plan_chaining(
        user_text="extractable but invalid case",
        extractor=lambda _text: request,
        summarizer=should_not_summarize,
    )

    assert result["status"] == "rejected"
    assert result["stop_reason"] == "gate_rejected"
    assert any("session_minutes" in item for item in result["errors"])
    assert result["counts"]["extractor_calls"] == 1
    assert result["counts"]["preview_tool_calls"] == 0
    assert result["counts"]["summarizer_calls"] == 0
