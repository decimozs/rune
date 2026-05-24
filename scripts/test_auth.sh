#!/usr/bin/env bash
# Test API key auth flow with DB-backed keys.
# Usage: ./scripts/test_auth.sh [base_url] [key]
set -euo pipefail

BASE="${1:-http://localhost:8000}"
KEY="${2:-${OCR_TEST_KEY:-}}"
FILE="app/datasets/images/sample1.png"

if [[ ! -f "$FILE" ]]; then
  echo "Error: test file $FILE not found" >&2
  exit 1
fi

red()   { printf "\033[31m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }

# ── 1. Probe auth mode ──
echo "=== 1. Auth mode probe ==="
PROBE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/ocr/parse" -F "file=@$FILE")
if [[ "$PROBE" == "200" ]]; then
  green "  Auth disabled — no key required"
  NO_AUTH=1
elif [[ "$PROBE" == "401" ]]; then
  echo "  Auth enabled — key required"
  NO_AUTH=0
else
  echo "  Server returned $PROBE — may be down"
  NO_AUTH=-1
fi

# ── 2. Missing key ──
echo "=== 2. Missing key ==="
if [[ "$NO_AUTH" == "1" ]]; then
  echo "  SKIP: auth disabled"
elif [[ "$NO_AUTH" == "-1" ]]; then
  echo "  SKIP: server unreachable"
elif curl -s -X POST "$BASE/ocr/parse" -F "file=@$FILE" \
  | grep -q '"Missing API key"'; then
  green "  PASS: returns 401"
else
  red "  FAIL: expected 401"
fi

# ── 3. Wrong key ──
echo "=== 3. Wrong key ==="
if [[ "$NO_AUTH" == "1" ]]; then
  echo "  SKIP: auth disabled"
elif [[ "$NO_AUTH" == "-1" ]]; then
  echo "  SKIP: server unreachable"
elif curl -s -X POST "$BASE/ocr/parse" \
  -H "X-API-Key: sk_live_wrongkey" -F "file=@$FILE" \
  | grep -q '"Invalid API key"'; then
  green "  PASS: returns 401"
else
  red "  FAIL: expected 401"
fi

# ── 4. Valid key ──
echo "=== 4. Valid key ==="
if [[ -z "$KEY" ]]; then
  echo "  SKIP: set OCR_TEST_KEY env or pass as 2nd arg"
elif [[ "$NO_AUTH" == "-1" ]]; then
  echo "  SKIP: server unreachable"
else
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/ocr/parse" \
    -H "X-API-Key: $KEY" -F "file=@$FILE")
  [[ "$STATUS" == "200" ]] && green "  PASS: returns 200" || red "  FAIL: expected 200 got $STATUS"
fi

# ── 5. GET job status requires auth ──
echo "=== 5. GET jobs/{id} ==="
if [[ "$NO_AUTH" == "1" ]]; then
  echo "  SKIP: auth disabled"
elif [[ "$NO_AUTH" == "-1" ]]; then
  echo "  SKIP: server unreachable"
elif curl -s -o /dev/null -w "%{http_code}" "$BASE/ocr/parse/jobs/fake" \
  | grep -q "401"; then
  green "  PASS: returns 401"
else
  red "  FAIL: expected 401"
fi

# ── 6. GET batch status requires auth ──
echo "=== 6. GET batch/{id} ==="
if [[ "$NO_AUTH" == "1" ]]; then
  echo "  SKIP: auth disabled"
elif [[ "$NO_AUTH" == "-1" ]]; then
  echo "  SKIP: server unreachable"
elif curl -s -o /dev/null -w "%{http_code}" "$BASE/ocr/parse/batch/fake" \
  | grep -q "401"; then
  green "  PASS: returns 401"
else
  red "  FAIL: expected 401"
fi

# ── 7. Health endpoints open ──
echo "=== 7. Health endpoints open ==="
if curl -sf "$BASE/health" -o /dev/null && curl -sf "$BASE/health/ready" -o /dev/null; then
  green "  PASS"
else
  red "  FAIL: health should be accessible"
fi

echo ""
echo "Done."
