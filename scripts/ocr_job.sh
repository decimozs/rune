#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
POLL_INTERVAL="${2:-2}"
FORMAT="${3:-json}"
FILE="${4:-}"

if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
  echo "Usage: $0 [url] [poll_interval] [format] <file>"
  echo ""
  echo "Examples:"
  echo "  $0 http://localhost:8000 2 json app/datasets/images/sample1.png"
  echo "  $0 http://localhost:8000 2 markdown app/datasets/images/sample1.png"
  echo ""
  exit 1
fi

if ! curl -sf --connect-timeout 3 "$BASE_URL/docs" > /dev/null 2>&1; then
  echo "Error: OCR API not reachable at $BASE_URL" >&2
  exit 1
fi

# ── Detect MIME ─────────────────────────────────────────────────────────
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
mime=$(get_mime "$FILE")

# ── Submit single file ──────────────────────────────────────────────────
echo "Submitting $FILE (format=$FORMAT)..."
resp=$(curl -sf -X POST "$BASE_URL/ocr/parse/jobs?format=$FORMAT" -F "file=@$FILE;type=$mime")
job_id=$(echo "$resp" | jq -r '.data.job_id')
echo "Job ID: $job_id"
echo ""

# ── Poll until done ─────────────────────────────────────────────────────
while true; do
  sleep "$POLL_INTERVAL"
  resp=$(curl -sf "$BASE_URL/ocr/parse/jobs/$job_id")
  status=$(echo "$resp" | jq -r '.data.status')
  ms=$(echo "$resp" | jq -r '.data.processing_time_ms // "?"')

  printf "\r  Status: %-10s  Time: %sms" "$status" "$ms"

  if [ "$status" = "completed" ]; then
    echo ""
    echo ""
    echo "=== Result ==="
    outdir="tests/outputs/job_${job_id}"
    mkdir -p "$outdir"
    echo "$resp" | jq . > "$outdir/response.json"

    if [ "$FORMAT" = "markdown" ]; then
      echo "$resp" | jq -r '.data.data' > "$outdir/output.md"
    else
      echo "$resp" | jq '.data.data' > "$outdir/output.json"
    fi

    echo "Outputs: $outdir/"
    exit 0

  elif [ "$status" = "failed" ]; then
    echo ""
    echo ""
    echo "=== Failed ==="
    echo "$resp" | jq '.data.error'
    exit 1
  fi
done
