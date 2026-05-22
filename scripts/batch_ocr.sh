#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
POLL_INTERVAL="${2:-2}"
FORMAT="${3:-json}"
FORMAT_EXT="${FORMAT/markdown/md}"

if ! curl -sf --connect-timeout 3 "$BASE_URL/docs" > /dev/null 2>&1; then
  echo "Error: OCR API not reachable at $BASE_URL" >&2
  exit 1
fi

# ── Collect all files with MIME types ─────────────────────────────────
FILES=()
get_mime() {
  case "$1" in
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

for arg in "${@:4}"; do
  [ -f "$arg" ] || { echo "Warning: not a file, skipping: $arg" >&2; continue; }
  mime=$(get_mime "$arg")
  if [ -n "$mime" ]; then
    FILES+=(-F "file=@$arg;type=$mime")
  else
    FILES+=(-F "file=@$arg")
  fi
done

if [ ${#FILES[@]} -eq 0 ]; then
  echo "Usage: $0 [url] [poll_interval] [format] <file1> [file2 ...]"
  echo ""
  echo "Examples:"
  echo "  $0 http://localhost:8000 2 json app/datasets/images/*.png"
  echo "  $0 http://localhost:8000 2 markdown app/datasets/images/*.png"
  echo "  $0 \"\" 5 json app/datasets/docx/* app/datasets/spreadsheets/sample1.csv"
  echo ""
  echo "Supported formats: png, jpg, pdf, docx, ppt, pptx, rtf, csv, xls, xlsx"
  exit 1
fi

# ── Submit batch ──────────────────────────────────────────────────────
echo "Submitting ${#FILES[@]} files (format=$FORMAT)..."
resp=$(curl -sf -X POST "$BASE_URL/ocr/parse/batch?format=$FORMAT" "${FILES[@]}")
batch_id=$(echo "$resp" | jq -r '.data.batch_id')
total=$(echo "$resp" | jq -r '.data.total_files')
echo "Batch ID: $batch_id  Files: $total"
echo ""

# ── Poll until done ───────────────────────────────────────────────────
while true; do
  sleep "$POLL_INTERVAL"
  resp=$(curl -sf "$BASE_URL/ocr/parse/batch/$batch_id")
  status=$(echo "$resp" | jq -r '.data.status')
  done_count=$(echo "$resp" | jq -r '.data.completed // 0')
  fail_count=$(echo "$resp" | jq -r '.data.failed // 0')
  ms=$(echo "$resp" | jq -r '.data.processing_time_ms // "?"')

  printf "\r  Status: %-10s  OK: %d  Fail: %d  Time: %sms" "$status" "$done_count" "$fail_count" "$ms"

  if [ "$status" = "completed" ]; then
    echo ""
    echo ""
    echo "=== Results ==="
    echo "$resp" | jq -r '
      .data.items[]
      | select(. != null)
      | "  " + .file_name + "  " + (if .success then "OK" else "FAIL" end) + "  " + (.processing_time_ms | tostring) + "ms"
    '
    echo ""
    outdir="tests/outputs/batch_${batch_id}"
    mkdir -p "$outdir"
    echo "$resp" | jq . > "$outdir/response.json"

    failed_list=""
    echo "$resp" | jq -c '.data.items[] | select(. != null)' | while read -r item; do
      name=$(echo "$item" | jq -r '.file_name')
      success=$(echo "$item" | jq -r '.success')
      if [ "$success" = "true" ]; then
        if [ "$FORMAT" = "markdown" ]; then
          echo "$item" | jq -r '.data' > "$outdir/${name}.md"
        else
          echo "$item" | jq '.data' > "$outdir/${name}.json"
        fi
      else
        echo "$item" | jq '.error' > "$outdir/${name}.error.json"
        failed_list+="  $name"$'\n'
      fi
    done

    echo "Outputs: $outdir/"
    if [ -n "$failed_list" ]; then
      echo "Failed files:"
      echo "$failed_list"
    fi
    exit 0
  fi
done
