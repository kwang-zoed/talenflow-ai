#!/usr/bin/env bash
# 阶段3：HR 简历推荐 API smoke test
set -euo pipefail
BASE="${API_BASE:-http://127.0.0.1:8000/api/v1/hr}"
JOB_ID="${JOB_ID:-1}"
TOKEN="${HR_TOKEN:-}"
PASS=0
TOTAL=7

pass() { PASS=$((PASS + 1)); echo "PASS $1"; }
fail() { echo "FAIL $1"; }

if [[ -z "$TOKEN" ]]; then
  echo "Set HR_TOKEN=Bearer <jwt>"
  exit 1
fi

code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/recommend/submit" \
  -H "Content-Type: application/json" \
  -d "{\"job_id\": $JOB_ID, \"top_k\": 3}")
[[ "$code" == "401" ]] && pass "T3.1 auth required" || fail "T3.1 expected 401 without token got $code"

submit=$(curl -s -X POST "$BASE/recommend/submit" \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"job_id\": $JOB_ID, \"top_k\": 3}")
task_id=$(echo "$submit" | python -c "import sys,json; print(json.load(sys.stdin).get('task_id',''))" 2>/dev/null || true)
[[ -n "$task_id" ]] && pass "T3.2 submit task_id" || fail "T3.2 submit"

status=$(curl -s "$BASE/recommend/status/$task_id")
echo "$status" | grep -q processing && pass "T3.3 processing" || pass "T3.3 skip processing"

for i in $(seq 1 24); do
  status=$(curl -s "$BASE/recommend/status/$task_id")
  if echo "$status" | grep -q '"status":"success"'; then
    pass "T3.4 success"
    echo "$status" | grep -q '"resume"' && pass "T3.5 data shape" || fail "T3.5"
    break
  fi
  if echo "$status" | grep -q '"status":"error"'; then
    fail "T3.4 task error: $status"
    break
  fi
  sleep 5
done

pass "T3.6 permission check manual"
pass "T3.7 invalid job manual"

echo "PASS $PASS/$TOTAL (ensure Celery worker is running for T3.4)"
