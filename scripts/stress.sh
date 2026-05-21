#!/usr/bin/env bash
set -euo pipefail

CONCURRENCY="${1:-5}"
BASE_URL="${2:-http://localhost:8000}"
DATASET_DIR="app/datasets"
OUTDIR="tests/outputs/stress_$(date +%Y%m%d_%H%M%S)"

if [ ! -d "$DATASET_DIR" ] || [ -z "$(ls -A "$DATASET_DIR" 2>/dev/null)" ]; then
  echo "Error: $DATASET_DIR missing or empty" >&2
  exit 1
fi

if ! curl -sf --connect-timeout 2 "$BASE_URL/docs" > /dev/null 2>&1; then
  echo "Error: Server not running at $BASE_URL" >&2
  exit 1
fi

mkdir -p "$OUTDIR"

echo "Stress test execution: concurrency=$CONCURRENCY targeting $BASE_URL"
echo ""

table_data="FILE\tSUCCESS\tFAILED\tTOTAL_TIME\tRPS"

for filepath in "$DATASET_DIR"/*; do
  [ -f "$filepath" ] || continue
  filename=$(basename "$filepath")

  passes=0
  fails=0
  start=$(date +%s%3N)

  pids=()

  for ((i=1; i<=CONCURRENCY; i++)); do
    (
      resp=$(curl -sf -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/ocr/parse" -F "file=@$filepath" 2>/dev/null)
      [ "$resp" = "200" ] && exit 0 || exit 1
    ) &
    pids+=($!) 
   pid_list=""
  done

  for pid in "${pids[@]}"; do
    if wait "$pid"; then
      ((passes++))
    else
      ((fails++))
    fi
  done

  end=$(date +%s%3N)
  elapsed=$((end - start))
  
  if [ "$elapsed" -eq 0 ]; then elapsed=1; fi
  rps=$(echo "scale=2; $CONCURRENCY / ($elapsed / 1000)" | bc)

  table_data+="\n${filename}\t${passes}\t${fails}\t${elapsed}ms\t${rps}"
done

# Format and write out
echo -e "$table_data" | column -ts $'\t' | tee "$OUTDIR/stress_report.txt"

echo -e "\nReport saved to: $OUTDIR/stress_report.txt"
