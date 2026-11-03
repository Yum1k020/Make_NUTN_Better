#!/bin/sh
set -eu

API_BASE=${API_BASE:-http://127.0.0.1:5050/api/v1}

curl --fail --silent --show-error \
  -X PATCH "$API_BASE/me" \
  -H 'Content-Type: application/json' \
  --data '{"department_id":"dept-nutn-csie","admission_year":115,"current_semester_id":"semester-115-1"}'
printf '\n'
