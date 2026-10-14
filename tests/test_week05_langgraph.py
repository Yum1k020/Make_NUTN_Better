from __future__ import annotations

import json
from pathlib import Path

from backend.week04_tools import preview_study_plan
from backend.week05_langgraph import StudyPlanLangGraphRuntime

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "week04_plan.json"


def _request() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _runtime(tmp_path: Path) -> StudyPlanLangGraphRuntime:
    return StudyPlanLangGraphRuntime(
        checkpoint_path=tmp_path / "checkpoints.sqlite",
        store_path=tmp_path / "study_sessions.json",
    )


def test_candidate_matches_week04_preview_and_pauses_without_write(tmp_path: Path):
    request = _request()
    baseline = preview_study_plan(**request)

    with _runtime(tmp_path) as runtime:
        candidate = runtime.start(
            request=request,
            request_id="REQ-W05-A",
            thread_id="thread-a",
        )

    assert candidate["preview"] == baseline
    assert candidate["status"] == "awaiting_confirmation"
    assert candidate["interrupts"][0]["value"]["action"] == "save_study_plan"
    assert not (tmp_path / "study_sessions.json").exists()


def test_reject_does_not_write(tmp_path: Path):
    with _runtime(tmp_path) as runtime:
        runtime.start(
            request=_request(),
            request_id="REQ-W05-B",
            thread_id="thread-b",
        )
        result = runtime.resume(thread_id="thread-b", decision="NO")

    assert result["status"] == "rejected"
    assert result["save_result"]["accepted"] is False
    assert result["save_result"]["executed"] is False
    assert not (tmp_path / "study_sessions.json").exists()


def test_exact_yes_writes_once(tmp_path: Path):
    with _runtime(tmp_path) as runtime:
        runtime.start(
            request=_request(),
            request_id="REQ-W05-C",
            thread_id="thread-c",
        )
        result = runtime.resume(thread_id="thread-c", decision="YES")

    assert result["status"] == "saved"
    assert result["save_result"]["accepted"] is True
    assert result["save_result"]["executed"] is True

    data = json.loads((tmp_path / "study_sessions.json").read_text(encoding="utf-8"))
    assert len(data["study_sessions"]) == 3


def test_sqlite_checkpoint_resumes_after_runtime_rebuild(tmp_path: Path):
    request = _request()
    first = _runtime(tmp_path)
    try:
        pending = first.start(
            request=request,
            request_id="REQ-W05-D",
            thread_id="thread-d",
        )
        assert pending["status"] == "awaiting_confirmation"
    finally:
        first.close()

    second = _runtime(tmp_path)
    try:
        result = second.resume(thread_id="thread-d", decision="YES")
    finally:
        second.close()

    assert result["status"] == "saved"
    assert result["save_result"]["request_id"] == "REQ-W05-D"


def test_same_request_id_on_new_thread_is_idempotent(tmp_path: Path):
    request = _request()

    with _runtime(tmp_path) as runtime:
        runtime.start(
            request=request,
            request_id="REQ-W05-E",
            thread_id="thread-e1",
        )
        first = runtime.resume(thread_id="thread-e1", decision="YES")

        runtime.start(
            request=request,
            request_id="REQ-W05-E",
            thread_id="thread-e2",
        )
        replay = runtime.resume(thread_id="thread-e2", decision="YES")

    data = json.loads((tmp_path / "study_sessions.json").read_text(encoding="utf-8"))
    assert first["save_result"]["replayed"] is False
    assert replay["save_result"]["replayed"] is True
    assert len(data["study_sessions"]) == 3


def test_lowercase_yes_is_rejected_to_preserve_week04_rule(tmp_path: Path):
    with _runtime(tmp_path) as runtime:
        runtime.start(
            request=_request(),
            request_id="REQ-W05-F",
            thread_id="thread-f",
        )
        result = runtime.resume(thread_id="thread-f", decision="yes")

    assert result["status"] == "rejected"
    assert result["save_result"]["executed"] is False
    assert not (tmp_path / "study_sessions.json").exists()
