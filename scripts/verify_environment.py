#!/usr/bin/env python3
"""Verify the local runtime needed by the integrated course project."""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_MODULES = (
    "flask",
    "fastapi",
    "google.auth",
    "langgraph",
    "langgraph.checkpoint.sqlite",
)
REQUIRED_PATHS = (
    PROJECT_ROOT / "backend" / "app",
    PROJECT_ROOT / "frontend" / "package.json",
    PROJECT_ROOT / "nutn_csie_115_graduation_rules.json",
)


def main() -> int:
    problems: list[str] = []
    if sys.version_info < (3, 12):
        problems.append(
            f"Python 3.12+ required; current version is {sys.version.split()[0]}."
        )

    for module in REQUIRED_MODULES:
        try:
            available = importlib.util.find_spec(module) is not None
        except (ImportError, ModuleNotFoundError):
            available = False
        if not available:
            problems.append(f"Missing Python module: {module}")

    for path in REQUIRED_PATHS:
        if not path.exists():
            problems.append(f"Missing project path: {path.relative_to(PROJECT_ROOT)}")

    try:
        with sqlite3.connect(":memory:") as connection:
            connection.execute("SELECT 1").fetchone()
    except sqlite3.Error as error:
        problems.append(f"SQLite unavailable: {type(error).__name__}")

    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        return 1

    print("整合環境已就緒：Python 3.12、Flask、FastAPI、LangGraph、ADC 套件與 SQLite 可用。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
