#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
OUTDIR="tests/outputs/format-test/$(date +%Y-%m-%d_%H%M%S)"
mkdir -p "$OUTDIR"

API_KEY="${OCR_API_KEY:-sk-local-dev}"
AUTH=(-H "X-API-Key: $API_KEY")

if ! curl -sf --connect-timeout 3 "$BASE_URL/docs" > /dev/null 2>&1; then
  echo "Error: OCR API not reachable at $BASE_URL" >&2
  exit 1
fi

TESTS=(
  "png:app/datasets/images/sample1.png:image/png"
  "png2:app/datasets/images/sample2.png:image/png"
  "png3:app/datasets/images/sample3.png:image/png"
  "doc:app/datasets/docx/sample1.doc:application/msword"
  "docx:app/datasets/docx/sample1.docx:application/vnd.openxmlformats-officedocument.wordprocessingml.document"
  "ppt:app/datasets/ppt/sample1.ppt:application/vnd.ms-powerpoint"
  "rtf:app/datasets/rtf/sample1.rtf:text/rtf"
  "csv:app/datasets/spreadsheets/sample1.csv:text/csv"
  "xls:app/datasets/spreadsheets/sample1.xls:application/vnd.ms-excel"
  "xlsx:app/datasets/spreadsheets/sample1.xlsx:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

pass=0
fail=0

run_test() {
  local name="$1"
  local path="$2"
  local mime="$3"
  local fmt="$4"   # "json" or "markdown"

  printf "%-6s %-8s " "$name" "$fmt"

  resp=$(curl -sf "${AUTH[@]}" -X POST "$BASE_URL/ocr/parse?format=$fmt" \
    -F "file=@$path;type=$mime" 2>&1) && rc=$? || rc=$?

  if [ $rc -ne 0 ] || [ -z "$resp" ]; then
    echo "FAIL (curl exit $rc)"
    fail=$((fail + 1))
    return
  fi

  success=$(echo "$resp" | jq -r '.success')
  ms=$(echo "$resp" | jq -r '.metadata.processing_time_ms // "?"')

  if [ "$success" != "true" ]; then
    echo "FAIL (api error: $(echo "$resp" | jq -r '.error.message // "unknown"'))"
    fail=$((fail + 1))
    return
  fi

  if [ "$fmt" = "markdown" ]; then
    # Extract only the data field and write as .md file
    echo "$resp" | jq -r '.data' > "$OUTDIR/${name}.md"
    # Also save the full response envelope as JSON for reference
    echo "$resp" | jq . > "$OUTDIR/${name}_markdown_response.json"
  else
    # Save full JSON response
    echo "$resp" | jq . > "$OUTDIR/${name}.json"
  fi

  echo "OK  ${ms}ms"
  pass=$((pass + 1))
}

echo "=== JSON format ==="
for entry in "${TESTS[@]}"; do
  IFS=: read -r name path mime <<< "$entry"
  run_test "$name" "$path" "$mime" "json"
done

echo ""
echo "=== Markdown format ==="
for entry in "${TESTS[@]}"; do
  IFS=: read -r name path mime <<< "$entry"
  run_test "$name" "$path" "$mime" "markdown"
done

echo ""
echo "---"
echo "Pass: $pass  Fail: $fail  Total: $((pass + fail))"
echo "Outputs: $OUTDIR"
