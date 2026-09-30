#!/bin/sh
set -eu
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON_BIN=${PYTHON_BIN:-python3}
cd "$PROJECT_ROOT"
"$PYTHON_BIN" -c 'import sys; assert sys.version_info >= (3, 12), "Python 3.12+ is required; set PYTHON_BIN to its path."'
if [ ! -d .venv ]; then
  "$PYTHON_BIN" -m venv .venv
fi
.venv/bin/python -c 'import sys; assert sys.prefix != sys.base_prefix; assert sys.version_info >= (3, 12)'
mkdir -p .cache/tmp
export TMPDIR="$PROJECT_ROOT/.cache/tmp"
export PYTHONDONTWRITEBYTECODE=1
.venv/bin/python -m pip --isolated --disable-pip-version-check --no-cache-dir install -r backend/requirements-dev.lock.txt
.venv/bin/python -m pip --isolated --disable-pip-version-check --no-cache-dir check
