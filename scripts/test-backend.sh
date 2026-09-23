#!/bin/sh
set -eu
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_ROOT/backend"
export PYTHONDONTWRITEBYTECODE=1
exec "$PROJECT_ROOT/.venv/bin/python" -m pytest -c "$PROJECT_ROOT/backend/pytest.ini" "$@"
