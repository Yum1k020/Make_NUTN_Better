#!/bin/sh
# Isolated demo database and UI; uses the same reusable Flask API implementation.
set -eu
PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export ME_DATABASE=${ME_DATABASE:-"$PROJECT_ROOT/backend/instance/agent-lab.sqlite3"}
export PORT=${PORT:-5051}
"$PROJECT_ROOT/scripts/init-backend-db.sh"
exec "$PROJECT_ROOT/scripts/run-backend.sh"
