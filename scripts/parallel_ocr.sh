#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
POLL_INTERVAL="${2:-2}"
FORMAT="${3:-json}"

FORMAT_EXT="$FORMAT"
[ "$FORMAT_EXT" = "markdown" ] && FORMAT_EXT="md"

OUTDIR="tests/outputs/parallel_$(date +%Y%m%d_%H%M%S)"

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
    *)      echo "application/octet-stream" ;;
  esac
}

if ! curl -sf --connect-timeout 3 "$BASE_URL/docs" > /dev/null 2>&1; then
  echo "Error: OCR API not reachable at $BASE_URL" >&2
  exit 1
fi

# ── Collect args ─────────────────────────────────────────────────────
FILES=()
for arg in "${@:4}"; do
  [ -f "$arg" ] || { echo "Warning: not a file, skipping: $arg" >&2; continue; }
  FILES+=("$arg")
done

if [ ${#FILES[@]} -eq 0 ]; then
  echo "Usage: $0 [url] [poll_interval] [format] <file1> [file2 ...]"
  echo ""
  exit 1
fi

mkdir -p "$OUTDIR"

# ── Phase 1: Submit all files ────────────────────────────────────────
echo "Submitting ${#FILES[@]} files  (format=$FORMAT, poll=${POLL_INTERVAL}s)"
echo ""

declare -a JOB_IDS
declare -A FILE_MAP
SUBMIT_OK=0
SUBMIT_FAIL=0
I=0

for f in "${FILES[@]}"; do
  mime=$(get_mime "$f")
  name=$(basename "$f")

  printf "  [submit] %s ... " "$name"
  if [ -n "$mime" ]; then
    resp=$(curl -sf -X POST "$BASE_URL/ocr/parse/jobs?format=$FORMAT" \
      -F "file=@$f;type=$mime" 2>/dev/null) && rc=0 || rc=$?
  else
    resp=$(curl -sf -X POST "$BASE_URL/ocr/parse/jobs?format=$FORMAT" \
      -F "file=@$f" 2>/dev/null) && rc=0 || rc=$?
  fi

  if [ "$rc" -ne 0 ]; then
    echo "FAIL (rc=$rc)"
    SUBMIT_FAIL=$((SUBMIT_FAIL + 1))
    continue
  fi

  jid=$(echo "$resp" | jq -r '.data.job_id // empty')
  if [ -z "$jid" ]; then
    echo "FAIL (no job_id)"
    SUBMIT_FAIL=$((SUBMIT_FAIL + 1))
    continue
  fi

  echo "OK  job_id=$jid"
  JOB_IDS+=("$jid")
  FILE_MAP["$jid"]="$name"
  echo "$resp" | jq . > "$OUTDIR/${jid}_submit.json" 2>/dev/null
  SUBMIT_OK=$((SUBMIT_OK + 1))
done

echo ""
echo "Submitted: ${SUBMIT_OK} OK, ${SUBMIT_FAIL} failed"
echo ""

if [ "$SUBMIT_OK" -eq 0 ]; then
  echo "No jobs submitted successfully — exiting"
  exit 1
fi

# ── Phase 2: Poll until all done ─────────────────────────────────────
TOTAL=$SUBMIT_OK
declare -A STATUS
declare -A DATA
declare -A ERROR
declare -A ELAPSED
PENDING=("${JOB_IDS[@]}")
DONE=0
DONE_OK=0
DONE_FAIL=0

while [ ${#PENDING[@]} -gt 0 ]; do
  sleep "$POLL_INTERVAL"
  NEW_PENDING=()

  for jid in "${PENDING[@]}"; do
    resp=$(curl -sf "$BASE_URL/ocr/parse/jobs/$jid" 2>/dev/null) || {
      NEW_PENDING+=("$jid")
      continue
    }
    st=$(echo "$resp" | jq -r '.data.status // empty')

    if [ "$st" = "completed" ] || [ "$st" = "failed" ]; then
      name="${FILE_MAP[$jid]}"
      ms=$(echo "$resp" | jq -r '.data.processing_time_ms // "?"')
      STATUS["$jid"]="$st"
      ELAPSED["$jid"]="$ms"

      if [ "$st" = "completed" ]; then
        DONE_OK=$((DONE_OK + 1))
        DATA["$jid"]=$(echo "$resp" | jq '.data.data')
        echo "$resp" | jq . > "$OUTDIR/${jid}_done.json"
        echo "${DATA[$jid]}" > "$OUTDIR/${jid}_output.${FORMAT_EXT}"
        printf "\r  OK: %d  Fail: %d  Remaining: %d  Last: %s  %sms" \
          "$DONE_OK" "$DONE_FAIL" "$((TOTAL - DONE_OK - DONE_FAIL))" "$name" "$ms"
      else
        DONE_FAIL=$((DONE_FAIL + 1))
        ERROR["$jid"]=$(echo "$resp" | jq -c '.data.error')
        echo "$resp" | jq . > "$OUTDIR/${jid}_failed.json"
        printf "\r  OK: %d  Fail: %d  Remaining: %d  LAST_FAIL: %s  %s" \
          "$DONE_OK" "$DONE_FAIL" "$((TOTAL - DONE_OK - DONE_FAIL))" "$name" "$ms"
      fi
    else
      NEW_PENDING+=("$jid")
    fi
  done

  PENDING=("${NEW_PENDING[@]}")
done

echo ""
echo ""
echo "=== Results ==="
echo "=== Results ==="
for jid in "${JOB_IDS[@]}"; do
  st="${STATUS[$jid]}"
  name="${FILE_MAP[$jid]}"
  if [ "$st" = "completed" ]; then
    echo "  $name  OK  ${ELAPSED[$jid]}ms"
  else
    echo "  $name  FAIL  ${ERROR[$jid]}"
  fi
done

echo ""
echo "Summary: ${DONE_OK} OK, ${DONE_FAIL} failed"
echo "Outputs: $OUTDIR/"

if [ "$DONE_FAIL" -gt 0 ]; then
  exit 1
fi
