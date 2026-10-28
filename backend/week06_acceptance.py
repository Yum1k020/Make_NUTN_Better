"""Reproducible synthetic acceptance; live never silently substitutes a fixture.

Run from repo: python -X utf8 backend/week06_acceptance.py [--live | --serve-fixture]
"""

import argparse
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import subprocess
from time import perf_counter
from uuid import uuid4

from app import create_app
from app.db import init_db
from app.planner_core import timestamp

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "13be93782ef44e08886f86afffedd7f8fc72333d"


def prepare(path):
    app = create_app({"TESTING": True, "DATABASE": str(path), "GRADUATION_ENGINE": "langgraph"})
    with app.app_context():
        init_db()
    client = app.test_client()
    calls = [
        ("PATCH", "me", {"department_id": "dept-nutn-csie", "admission_year": 115, "current_semester_id": "semester-115-1"}),
        ("POST", "enrollments", {"course_id": "course-demo-001", "semester_id": "semester-115-1", "enrollment_status": "finished", "passed": True, "grade": 80}),
        ("POST", "enrollments", {"course_id": "course-demo-002", "semester_id": "semester-115-1", "enrollment_status": "in_progress", "passed": None, "grade": None}),
        ("POST", "planned-courses", {"course_id": "course-demo-003", "target_semester_id": "semester-115-2"}),
        ("PUT", "lecture-progress", {"professional_count": 10, "general_count": None}),
    ]
    for method, route, payload in calls:
        response = client.open("/api/v1/" + route, method=method, json=payload)
        assert response.status_code in (200, 201), response.json
    return app, calls


def snapshot(app):
    with sqlite3.connect(app.config["DATABASE"]) as db:
        return sha256("\n".join(db.iterdump()).encode()).hexdigest()


def fixture(context, previous, feedback):
    from app.graduation_explanation_core import valid_draft
    draft = valid_draft(context)
    if previous is None:
        draft["items"][0]["source_ids"] = []
        draft["earned_credits"] = 999
    return draft, {"provider": "fixture", "latency_ms": 0, "usage": {}}


def measured(client, method, route, **kwargs):
    start = perf_counter()
    response = client.open("/api/v1/" + route, method=method, **kwargs)
    return {"http_status": response.status_code, "latency_ms": round((perf_counter() - start) * 1000),
            "response": response.json}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--serve-fixture", action="store_true")
    args = parser.parse_args()
    folder = ROOT / ".cache" / "week06"
    folder.mkdir(parents=True, exist_ok=True)
    app, inputs = prepare(folder / (str(uuid4()) + ".sqlite3"))
    if args.serve_fixture:
        os.environ["GRADUATION_ALLOWED_ORIGINS"] = "http://127.0.0.1:5173,http://localhost:5173"
        app.config["GRADUATION_EXPLANATION_PROVIDER"] = fixture
        print("SYNTHETIC FIXTURE ONLY: not Gemini live evidence", flush=True)
        app.run(host="127.0.0.1", port=5000, debug=False)
        return
    client = app.test_client()
    digest = snapshot(app)
    baseline = measured(client, "GET", "graduation-progress")
    configured = bool(os.environ.get("GEMINI_API_KEY") and os.environ.get("GEMINI_MODEL"))
    if args.live and configured:
        candidate = measured(client, "POST", "graduation-explanation")
        workflow = candidate["response"].get("data", {}).get("workflow", {})
        live_status = "LIVE_PASS" if workflow.get("status") == "verified" else "LIVE_FAIL"
    elif args.live:
        candidate = None
        live_status = "LIVE_NOT_RUN"
    else:
        app.config["GRADUATION_EXPLANATION_PROVIDER"] = fixture
        candidate = measured(client, "POST", "graduation-explanation")
        live_status = "LIVE_NOT_RUN"
    observed = 0
    def forbidden(*arguments):
        nonlocal observed
        observed += 1
        raise AssertionError("invalid input reached provider")
    app.config["GRADUATION_EXPLANATION_PROVIDER"] = forbidden
    invalid = measured(client, "POST", "graduation-explanation", json={"user_id": "other"})
    assert invalid["http_status"] == 422 and observed == 0
    def failure(*arguments):
        from app.graduation_explanation_core import ProviderFailure
        raise ProviderFailure("PROVIDER_UNAVAILABLE", attempted=True)
    app.config["GRADUATION_EXPLANATION_PROVIDER"] = failure
    failed = measured(client, "POST", "graduation-explanation")
    assert failed["response"]["data"]["workflow"]["stop_reason"] == "PROVIDER_UNAVAILABLE"
    assert snapshot(app) == digest
    if candidate:
        original = deepcopy(baseline["response"]["data"])
        after = deepcopy(candidate["response"]["data"]["progress"])
        original.pop("evaluated_at"); after.pop("evaluated_at")
        assert original == after
        assert after["earned_credits"] == 3
    paths = list((ROOT / "backend/app").glob("graduation_*.py")) + [Path(__file__)]
    report = {"timestamp": timestamp(), "baseline_sha": BASELINE,
              "candidate_source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "source_hashes": {p.relative_to(ROOT).as_posix(): sha256(p.read_bytes()).hexdigest() for p in paths},
              "dataset": "synthetic only; no student records", "inputs": inputs,
              "live_status": live_status, "normal_kind": "gemini" if args.live else "injected_fixture",
              "normal_not_run_reason": "GEMINI_API_KEY and GEMINI_MODEL are required" if args.live and not configured else None,
              "baseline": baseline, "candidate": candidate,
              "invalid_input": {"expected": "422, zero provider calls", "actual": invalid, "provider_calls": observed},
              "provider_failure": {"kind": "injected", "expected": "one call, bounded fallback", "actual": failed},
              "database_unchanged": True,
              "comparison_scope": "Same data/rules/tools/endpoint: existing GET facts versus added POST explanation. Baseline facts calculated by unchanged week05 progress helpers.",
              "baseline_model_calls": 0, "baseline_tool_calls": 1,
              "cost_note": "No cost savings claimed. Token fields absent from provider response are unavailable, not zero."}
    out = ROOT / "docs/week06/evidence" / ("live.json" if args.live else "acceptance.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": out.relative_to(ROOT).as_posix(), "live_status": live_status,
                      "normal_executed": candidate is not None, "database_unchanged": True}))


if __name__ == "__main__":
    main()
