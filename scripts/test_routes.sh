#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
POLL_TIMEOUT="${2:-60}"
POLL_INTERVAL=2

PASS=0
FAIL=0

API_KEY="${OCR_API_KEY:-sk-local-dev}"
AUTH=(-H "X-API-Key: $API_KEY")
OUTDIR="tests/outputs/test_routes_$(date +%Y%m%d_%H%M%S)"

pass() {
  PASS=$((PASS + 1))
  printf "  PASS  [%d] %s\n" "$PASS" "$1"
}

fail() {
  FAIL=$((FAIL + 1))
  printf "  FAIL  [*] %s\n" "  $1  $2" >&2
}

die() {
  echo "Error: $*" >&2
  exit 1
}

get_mime() {
  case "$1" in
    *.png)  echo "image/png" ;;
    *.jpg|*.jpeg) echo "image/jpeg" ;;
    *.pdf)  echo "application/pdf" ;;
    *.docx) echo "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ;;
    *.ppt)  echo "application/vnd.ms-powerpoint" ;;
    *.pptx) echo "application/vnd.openxmlformats-officedocument.presentationml.presentation" ;;
    *.rtf)  echo "text/rtf" ;;
    *.csv)  echo "text/csv" ;;
    *.xls)  echo "application/vnd.ms-excel" ;;
    *.xlsx) echo "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" ;;
    *)      echo "" ;;
  esac
}

if ! curl -sf --connect-timeout 3 "$BASE_URL/docs" > /dev/null 2>&1; then
  die "OCR API not reachable at $BASE_URL"
fi

mkdir -p "$OUTDIR"
echo "Route tests against $BASE_URL  (async timeout: ${POLL_TIMEOUT}s)"
echo ""

# ── Helper: poll a single job until completed/failed/timeout ─────────
poll_job() {
  local job_id="$1" label="$2" expected_type="$3"
  local waited=0

  while [ "$waited" -lt "$POLL_TIMEOUT" ]; do
    sleep "$POLL_INTERVAL"
    waited=$((waited + POLL_INTERVAL))

    local resp
    resp=$(curl -sf "${AUTH[@]}" "$BASE_URL/ocr/parse/jobs/$job_id") || continue
    echo "$resp" | jq . > "$OUTDIR/${label}/status.json" 2>/dev/null

    local st
    st=$(echo "$resp" | jq -r '.data.status // empty')

    if [ "$st" = "completed" ]; then
      local ms
      ms=$(echo "$resp" | jq -r '.data.processing_time_ms // "?"')
      if [ "$expected_type" = "markdown" ]; then
        local data_len
        data_len=$(echo "$resp" | jq -r '.data.data // ""' | wc -c)
        if [ "$data_len" -gt 10 ]; then
          pass "$label  ${ms}ms"
          return 0
        fi
        fail "$label" "empty markdown data"
        return 1
      else
        if echo "$resp" | jq -e '.data.data != null' > /dev/null 2>&1; then
          pass "$label  ${ms}ms"
          return 0
        fi
        fail "$label" "missing data in completed response"
        return 1
      fi
    elif [ "$st" = "failed" ]; then
      local err
      err=$(echo "$resp" | jq -c '.data.error // {message: "unknown"}')
      fail "$label" "failed: $err"
      return 1
    fi
  done

  fail "$label" "TIMEOUT after ${POLL_TIMEOUT}s"
  return 1
}

# ── Helper: poll a batch until completed ─────────────────────────────
poll_batch() {
  local batch_id="$1" label="$2" expected_count="$3"
  local waited=0

  while [ "$waited" -lt "$POLL_TIMEOUT" ]; do
    sleep "$POLL_INTERVAL"
    waited=$((waited + POLL_INTERVAL))

    local resp
    resp=$(curl -sf "${AUTH[@]}" "$BASE_URL/ocr/parse/batch/$batch_id") || continue
    echo "$resp" | jq . > "$OUTDIR/06-batch/status.json" 2>/dev/null

    local st
    st=$(echo "$resp" | jq -r '.data.status // empty')

    if [ "$st" = "completed" ]; then
      local all_ok
      all_ok=$(echo "$resp" | jq -e \
        ".data.items | length == $expected_count and ([.[] | select(.success == true)] | length) == $expected_count" \
        > /dev/null 2>&1 && echo 1 || echo 0)
      if [ "$all_ok" -eq 1 ]; then
        local ms
        ms=$(echo "$resp" | jq -r '.data.processing_time_ms // "?"')
        pass "$label  ${ms}ms"
        return 0
      fi
      fail "$label" "not all items succeeded"
      echo "$resp" | jq -c '.data.items[] | {file_name, success, error}' >&2
      return 1
    elif [ "$st" = "failed" ]; then
      fail "$label" "batch status=failed"
      return 1
    fi
  done

  fail "$label" "TIMEOUT after ${POLL_TIMEOUT}s"
  return 1
}

# ══════════════════════════════════════════════════════════════════════
# Test 1: sync json image
# ══════════════════════════════════════════════════════════════════════
mkdirok() { mkdir -p "$OUTDIR/$1"; }

mkdirok "01-sync-json"
resp=$(curl -sf "${AUTH[@]}" -X POST "$BASE_URL/ocr/parse?format=json" \
  -F "file=@app/datasets/images/sample1.png" 2>&1) && rc=0 || rc=$?
echo "$resp" | jq . > "$OUTDIR/01-sync-json/response.json" 2>/dev/null

if [ "$rc" -eq 0 ] && echo "$resp" | jq -e '.success == true and (.data.pages | length > 0)' > /dev/null 2>&1; then
  ms=$(echo "$resp" | jq -r '.metadata.processing_time_ms')
  pass "sync json  ${ms}ms"
else
  fail "sync json" "$(echo "$resp" | jq -c '.error // {message: "unexpected response"}' 2>/dev/null)"
fi

# ══════════════════════════════════════════════════════════════════════
# Test 2: sync md image
# ══════════════════════════════════════════════════════════════════════
mkdirok "02-sync-md"
resp=$(curl -sf "${AUTH[@]}" -X POST "$BASE_URL/ocr/parse?format=markdown" \
  -F "file=@app/datasets/images/sample1.png" 2>&1) && rc=0 || rc=$?
echo "$resp" | jq . > "$OUTDIR/02-sync-md/response.json" 2>/dev/null

if [ "$rc" -eq 0 ] && echo "$resp" | jq -e '.success == true and (.data | length > 0)' > /dev/null 2>&1; then
  ms=$(echo "$resp" | jq -r '.metadata.processing_time_ms')
  pass "sync md    ${ms}ms"
else
  fail "sync md" "$(echo "$resp" | jq -c '.error // {message: "unexpected response"}' 2>/dev/null)"
fi

# ══════════════════════════════════════════════════════════════════════
# Test 3: sync docx (office conversion)
# ══════════════════════════════════════════════════════════════════════
mkdirok "03-sync-docx"
mime=$(get_mime "app/datasets/docx/sample1.docx")
resp=$(curl -sf "${AUTH[@]}" -X POST "$BASE_URL/ocr/parse?format=json" \
  -F "file=@app/datasets/docx/sample1.docx;type=$mime" 2>&1) && rc=0 || rc=$?
echo "$resp" | jq . > "$OUTDIR/03-sync-docx/response.json" 2>/dev/null

if [ "$rc" -eq 0 ] && echo "$resp" | jq -e '.success == true and (.data.pages | length > 0)' > /dev/null 2>&1; then
  ms=$(echo "$resp" | jq -r '.metadata.processing_time_ms')
  pass "sync docx  ${ms}ms"
else
  fail "sync docx" "$(echo "$resp" | jq -c '.error // {message: "unexpected response"}' 2>/dev/null)"
fi

# ══════════════════════════════════════════════════════════════════════
# Test 4: background job json
# ══════════════════════════════════════════════════════════════════════
mkdirok "04-job-json"
mime=$(get_mime "app/datasets/images/sample2.png")
submit_resp=$(curl -sf "${AUTH[@]}" -X POST "$BASE_URL/ocr/parse/jobs?format=json" \
  -F "file=@app/datasets/images/sample2.png;type=$mime") && rc=0 || rc=$?
echo "$submit_resp" | jq . > "$OUTDIR/04-job-json/submit.json" 2>/dev/null

job_id=$(echo "$submit_resp" | jq -r '.data.job_id // empty')
if [ -z "$job_id" ]; then
  fail "job json" "no job_id (rc=$rc)"
else
  poll_job "$job_id" "04-job-json" "json"
fi

# ══════════════════════════════════════════════════════════════════════
# Test 5: background job markdown
# ══════════════════════════════════════════════════════════════════════
mkdirok "05-job-md"
mime=$(get_mime "app/datasets/rtf/sample1.rtf")
submit_resp=$(curl -sf "${AUTH[@]}" -X POST "$BASE_URL/ocr/parse/jobs?format=markdown" \
  -F "file=@app/datasets/rtf/sample1.rtf;type=$mime") && rc=0 || rc=$?
echo "$submit_resp" | jq . > "$OUTDIR/05-job-md/submit.json" 2>/dev/null

job_id=$(echo "$submit_resp" | jq -r '.data.job_id // empty')
if [ -z "$job_id" ]; then
  fail "job md" "no job_id (rc=$rc)"
else
  poll_job "$job_id" "05-job-md" "markdown"
fi

# ══════════════════════════════════════════════════════════════════════
# Test 6: batch 3 files
# ══════════════════════════════════════════════════════════════════════
mkdirok "06-batch"
mime_png=$(get_mime "app/datasets/images/sample3.png")
mime_docx=$(get_mime "app/datasets/docx/sample2.docx")
mime_csv=$(get_mime "app/datasets/spreadsheets/sample1.csv")

batch_resp=$(curl -sf "${AUTH[@]}" -X POST "$BASE_URL/ocr/parse/batch?format=json" \
  -F "file=@app/datasets/images/sample3.png;type=$mime_png" \
  -F "file=@app/datasets/docx/sample2.docx;type=$mime_docx" \
  -F "file=@app/datasets/spreadsheets/sample1.csv;type=$mime_csv") && rc=0 || rc=$?

if [ "$rc" -ne 0 ]; then
  fail "batch 3files" "submit failed (rc=$rc)"
else
  echo "$batch_resp" | jq . > "$OUTDIR/06-batch/submit.json"
  batch_id=$(echo "$batch_resp" | jq -r '.data.batch_id // empty')
  if [ -z "$batch_id" ]; then
    fail "batch 3files" "no batch_id in submit response"
  else
    poll_batch "$batch_id" "batch 3files" 3
  fi
fi

# ══════════════════════════════════════════════════════════════════════
# Test 7: invalid batch ID → 404
# ══════════════════════════════════════════════════════════════════════
code=$(curl -s "${AUTH[@]}" -o /dev/null -w "%{http_code}" "$BASE_URL/ocr/parse/batch/doesnotexist")
if [ "$code" = "404" ]; then
  pass "invalid batch  404"
else
  fail "invalid batch" "got $code, expected 404"
fi

# ══════════════════════════════════════════════════════════════════════
# Test 8: invalid job ID → 404
# ══════════════════════════════════════════════════════════════════════
code=$(curl -s "${AUTH[@]}" -o /dev/null -w "%{http_code}" "$BASE_URL/ocr/parse/jobs/doesnotexist")
if [ "$code" = "404" ]; then
  pass "invalid job    404"
else
  fail "invalid job" "got $code, expected 404"
fi

# ══════════════════════════════════════════════════════════════════════
# Test 9: POST without file → 422
# ══════════════════════════════════════════════════════════════════════
code=$(curl -s "${AUTH[@]}" -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/ocr/parse")
if [ "$code" = "422" ]; then
  pass "no file       422"
else
  fail "no file" "got $code, expected 422"
fi

# ══════════════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════════════
TOTAL=$((PASS + FAIL))
echo ""
echo "──────────────────────────"
echo "  Result: ${PASS}/${TOTAL} passed"
echo "  Outputs: $OUTDIR/"
if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
