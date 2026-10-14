from __future__ import annotations

import json
import tempfile
from pathlib import Path

from backend.week04_tools import preview_study_plan, save_study_plan
from backend.week05_langgraph import StudyPlanLangGraphRuntime

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "week04_plan.json"
OUT = ROOT / "week05" / "evidence" / "week05_comparison.json"


def _read_store(path: Path) -> dict:
    if not path.exists():
        return {"study_sessions": [], "requests": {}, "audit": []}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    request = json.loads(FIXTURE.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory(prefix="week05-") as temp:
        root = Path(temp)
        baseline_store = root / "baseline.json"
        candidate_store = root / "candidate.json"
        checkpoint = root / "candidate.sqlite"

        baseline_preview = preview_study_plan(**request)
        baseline_reject = save_study_plan(
            preview=baseline_preview,
            confirmed=False,
            request_id="REQ-W05-BASE-REJECT",
            store_path=baseline_store,
        )
        baseline_confirm = save_study_plan(
            preview=baseline_preview,
            confirmed=True,
            request_id="REQ-W05-BASE-SAVE",
            store_path=baseline_store,
        )
        baseline_sessions = len(_read_store(baseline_store)["study_sessions"])

        runtime = StudyPlanLangGraphRuntime(
            checkpoint_path=checkpoint,
            store_path=candidate_store,
        )
        try:
            pending = runtime.start(
                request=request,
                request_id="REQ-W05-CANDIDATE",
                thread_id="week05-main",
            )
        finally:
            runtime.close()

        sessions_before_confirmation = len(_read_store(candidate_store)["study_sessions"])

        resumed = StudyPlanLangGraphRuntime(
            checkpoint_path=checkpoint,
            store_path=candidate_store,
        )
        try:
            confirmed = resumed.resume(thread_id="week05-main", decision="YES")

            resumed.start(
                request=request,
                request_id="REQ-W05-CANDIDATE",
                thread_id="week05-replay",
            )
            replayed = resumed.resume(thread_id="week05-replay", decision="YES")

            resumed.start(
                request=request,
                request_id="REQ-W05-LOWERCASE",
                thread_id="week05-lowercase",
            )
            lowercase = resumed.resume(thread_id="week05-lowercase", decision="yes")
        finally:
            resumed.close()

        candidate_sessions = len(_read_store(candidate_store)["study_sessions"])

        checks = {
            "same_preview": pending["preview"] == baseline_preview,
            "paused_before_write": (
                pending["status"] == "awaiting_confirmation"
                and sessions_before_confirmation == 0
            ),
            "cross_runtime_resume_saved": (
                confirmed["status"] == "saved"
                and confirmed["save_result"]["executed"] is True
            ),
            "idempotent_replay": replayed["save_result"]["replayed"] is True,
            "lowercase_yes_rejected": (
                lowercase["status"] == "rejected"
                and lowercase["save_result"]["executed"] is False
            ),
            "candidate_saved_exactly_three_sessions": candidate_sessions == 3,
        }

        artifact = {
            "framework": "LangGraph",
            "replacement_boundary": "human approval pause/resume orchestration",
            "model_calls": 0,
            "same_input_fixture": "tests/fixtures/week04_plan.json",
            "baseline": {
                "preview": baseline_preview,
                "reject": baseline_reject,
                "confirm": baseline_confirm,
                "saved_session_count": baseline_sessions,
            },
            "candidate": {
                "pending": pending,
                "confirmed_after_runtime_rebuild": confirmed,
                "replayed": replayed,
                "lowercase_yes": lowercase,
                "saved_session_count": candidate_sessions,
            },
            "checks": checks,
            "all_pass": all(checks.values()),
            "notes": [
                "LangGraph owns checkpointed pause/resume only.",
                "Week 04 scheduler and save_study_plan keep business rules and idempotency.",
                "No Gemini/API key is needed for this Week 05 replacement boundary.",
            ],
        }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    if not artifact["all_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
