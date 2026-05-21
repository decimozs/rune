#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
DATASET_DIR="app/datasets"
RUN1="tests/compare_run1_$$"
RUN2="tests/compare_run2_$$"
OUTDIR="tests/outputs/comparisons_$(date +%Y%m%d_%H%M%S)"
exit_code=0

cleanup() {
  rm -rf "$RUN1" "$RUN2"
}
trap cleanup EXIT

if [ ! -d "$DATASET_DIR" ] || [ -z "$(ls -A "$DATASET_DIR" 2>/dev/null)" ]; then
  echo "Error: $DATASET_DIR missing or empty" >&2
  exit 1
fi

if ! curl -sf --connect-timeout 2 "$BASE_URL/docs" > /dev/null 2>&1; then
  echo "Error: Server not running at $BASE_URL" >&2
  exit 1
fi

mkdir -p "$OUTDIR"

run_ocr() {
  local outdir="$1"
  mkdir -p "$outdir"
  for filepath in "$DATASET_DIR"/*; do
    [ -f "$filepath" ] || continue
    local filename=$(basename "$filepath")
    curl -sf -X POST "$BASE_URL/ocr/parse" -F "file=@$filepath" > "$outdir/${filename}.json" 2>/dev/null
    curl -sf -X POST "$BASE_URL/ocr/parse?format=markdown" -F "file=@$filepath" > "$outdir/${filename}.md" 2>/dev/null
  done
}

echo "Executing comparison pipelines..."
run_ocr "$RUN1"
run_ocr "$RUN2"

table_data="OUTPUT_FILE\tCOMPARISON_RESULT"

for f1 in "$RUN1"/*; do
  fname=$(basename "$f1")
  f2="$RUN2/$fname"
  if [ ! -f "$f2" ]; then
    table_data+="\n${fname}\tMISSING (Run 2)"
    exit_code=1
    continue
  fi

  if [[ "$fname" == *.json ]]; then
    if ! diff <(jq --sort-keys 'del(.metadata.timestamp, .metadata.processing_time_ms)' "$f1") \
              <(jq --sort-keys 'del(.metadata.timestamp, .metadata.processing_time_ms)' "$f2") > /dev/null; then
      table_data+="\n${fname}\tMISMATCH (JSON structure diff)"
      exit_code=1
    else
      table_data+="\n${fname}\tMATCH"
    fi
  else
    if ! diff -q "$f1" "$f2" > /dev/null; then
      table_data+="\n${fname}\tMISMATCH (Text content diff)"
      exit_code=1
    else
      table_data+="\n${fname}\tMATCH"
    fi
  fi
done

for f2 in "$RUN2"/*; do
  fname=$(basename "$f2")
  f1="$RUN1/$fname"
  if [ ! -f "$f1" ]; then
    table_data+="\n${fname}\tMISSING (Run 1)"
    exit_code=1
  fi
done

{
  echo "Comparison Summary"
  echo -e "$table_data" | column -ts $'\t'
  if [ "$exit_code" -eq 0 ]; then
    echo "Result: SUCCESS - All outputs match perfectly."
  else
    echo "Result: FAILURE - Discrepancies detected."
  fi
} | tee "$OUTDIR/comparison_report.txt"

echo -e "\nReport saved to: $OUTDIR/comparison_report.txt"
exit "$exit_code"
