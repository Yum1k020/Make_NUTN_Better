#!/bin/sh
set -eu
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ -z "${PYTHON_BIN:-}" ]; then
  if [ -x "$PROJECT_ROOT/../.venv/bin/python" ]; then
    PYTHON_BIN="$PROJECT_ROOT/../.venv/bin/python"
  elif command -v python3.12 >/dev/null 2>&1; then
    PYTHON_BIN=$(command -v python3.12)
  else
    PYTHON_BIN=python3
  fi
fi
cd "$PROJECT_ROOT"
"$PYTHON_BIN" -c 'import sys, xml.parsers.expat; assert sys.version_info >= (3, 12), "Python 3.12+ is required; set PYTHON_BIN to its path."'
if [ ! -d .venv ]; then
  "$PYTHON_BIN" -m venv .venv
fi
if ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
  echo 'Existing .venv is incomplete (pip is unavailable). Move it aside, then rerun this script.' >&2
  exit 1
fi
.venv/bin/python -c 'import sys, xml.parsers.expat; assert sys.prefix != sys.base_prefix; assert sys.version_info >= (3, 12)'
mkdir -p .cache/tmp
export TMPDIR="$PROJECT_ROOT/.cache/tmp"
export PYTHONDONTWRITEBYTECODE=1
.venv/bin/python -m pip --isolated --disable-pip-version-check --no-cache-dir install \
  -r requirements-integrated.txt
.venv/bin/python -m pip --isolated --disable-pip-version-check --no-cache-dir check
.venv/bin/python scripts/verify_environment.py
