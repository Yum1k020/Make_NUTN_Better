#!/bin/sh
set -eu
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ -f "$PROJECT_ROOT/.env.local" ]; then
  set -a
  # This file is local-only and ignored by Git. Do not put shell commands in it.
  . "$PROJECT_ROOT/.env.local"
  set +a
fi
if [ ! -x "$PROJECT_ROOT/.venv/bin/python" ]; then
  echo 'Missing .venv. Run scripts/setup-backend.sh first.' >&2
  exit 1
fi
cd "$PROJECT_ROOT/backend"
export PYTHONDONTWRITEBYTECODE=1
exec "$PROJECT_ROOT/.venv/bin/python" -m flask --app app:create_app run --host 127.0.0.1 --port "${PORT:-5050}"
