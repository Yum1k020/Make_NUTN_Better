"""Write reproducible evidence only for tests that actually ran."""

import hashlib
import json
import platform
import sqlite3
import subprocess
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REPORT = {"tests": []}


def pytest_addoption(parser):
    parser.addoption("--evidence", help="Write test outcomes and actual HTTP exchanges as JSON")


def pytest_sessionstart(session):
    paths = sorted(path for folder in ("backend/app", "backend/tests", "scripts")
                   for path in (ROOT / folder).rglob("*") if path.suffix in (".py", ".sh"))
    paths += [ROOT / "backend/requirements-dev.lock.txt", ROOT / "backend/pytest.ini"]
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in paths}
    REPORT.update({
        "started_at": datetime.now().astimezone().isoformat(),
        "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip(),
        "version_note": "Uncommitted working tree; source hashes identify tested content, not HEAD alone.",
        "source_sha256": hashes,
        "source_fingerprint": hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(),
        "python": platform.python_version(), "sqlite": sqlite3.sqlite_version,
        "packages": {name: version(name) for name in ("Flask", "flask-smorest", "marshmallow", "pytest")},
        "command": "./scripts/test-backend.sh " + " ".join(session.config.invocation_params.args),
    })


@pytest.fixture
def evidence(request):
    records = []
    request.node.evidence_records = records
    return records


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    result = yield
    report = result.get_result()
    if report.when == "call" or report.failed or report.skipped:
        REPORT["tests"].append({
            "id": item.nodeid, "phase": report.when, "outcome": report.outcome,
            "duration_seconds": report.duration,
            "reason": str(report.longrepr) if report.failed or report.skipped else None,
            "records": getattr(item, "evidence_records", []),
        })


def pytest_sessionfinish(session, exitstatus):
    target = session.config.getoption("--evidence")
    if target:
        REPORT.update(finished_at=datetime.now().astimezone().isoformat(), exit_code=int(exitstatus))
        path = Path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(REPORT, ensure_ascii=False, indent=2) + "\n")
