from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.week05_langgraph import StudyPlanLangGraphRuntime

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "week04_plan.json"
RUNTIME = ROOT / "week05" / "runtime"
CHECKPOINT = RUNTIME / "langgraph.sqlite"
STORE = RUNTIME / "study_sessions.json"
DEFAULT_THREAD_ID = "W05-PLAN-001"
DEFAULT_REQUEST_ID = "W05-REQ-PLAN-001"


def _runtime() -> StudyPlanLangGraphRuntime:
    return StudyPlanLangGraphRuntime(
        checkpoint_path=CHECKPOINT,
        store_path=STORE,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Week 05 LangGraph pause/resume demo")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start")
    start.add_argument("--thread-id", default=DEFAULT_THREAD_ID)
    start.add_argument("--request-id", default=DEFAULT_REQUEST_ID)

    resume = sub.add_parser("resume")
    resume.add_argument("decision", help="Only exact YES is accepted")
    resume.add_argument("--thread-id", default=DEFAULT_THREAD_ID)

    args = parser.parse_args()

    with _runtime() as runtime:
        if args.command == "start":
            request = json.loads(FIXTURE.read_text(encoding="utf-8"))
            result = runtime.start(
                request=request,
                request_id=args.request_id,
                thread_id=args.thread_id,
            )
        else:
            result = runtime.resume(
                thread_id=args.thread_id,
                decision=args.decision,
            )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
