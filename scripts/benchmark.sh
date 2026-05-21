#!/usr/bin/env bash
set -euo pipefail

RUNS="${1:-3}"
BASE_URL="${2:-http://localhost:8000}"
DATASET_DIR="app/datasets"
OUTDIR="tests/outputs/benchmarks_$(date +%Y%m%d_%H%M%S)"

if [ ! -d "$DATASET_DIR" ] || [ -z "$(ls -A "$DATASET_DIR" 2>/dev/null)" ]; then
  echo "Error: $DATASET_DIR missing or empty" >&2
  exit 1
fi

if ! curl -sf --connect-timeout 2 "$BASE_URL/docs" > /dev/null 2>&1; then
  echo "Error: Server not running at $BASE_URL" >&2
  exit 1
fi

mkdir -p "$OUTDIR"

echo "Benchmark: $RUNS runs per file against $BASE_URL"
echo ""

table_data="FILE\tMIN\tMAX\tAVG\tMEDIAN\tSTATUS"

for filepath in "$DATASET_DIR"/*; do
  [ -f "$filepath" ] || continue
  filename=$(basename "$filepath")
  times=()

  for ((i=1; i<=RUNS; i++)); do
    resp=$(curl -sf -X POST "$BASE_URL/ocr/parse" -F "file=@$filepath" 2>/dev/null)
    ms=$(echo "$resp" | jq -r '.metadata.processing_time_ms // empty')
    if [ -n "$ms" ]; then
      times+=("$ms")
    fi
  done

  if [ ${#times[@]} -eq 0 ]; then
    table_data+="\n${filename}\t-\t-\t-\t-\tFAILED"
    continue
  fi

  IFS=$'\n' sorted=($(sort -n <<< "${times[*]}")); unset IFS
  count=${#sorted[@]}
  sum=0
  for t in "${sorted[@]}"; do sum=$(echo "$sum + $t" | bc); done
  avg=$(echo "scale=2; $sum / $count" | bc)
  min=${sorted[0]}
  max=${sorted[$((count-1))]}

  if ((count % 2 == 1)); then
    median="${sorted[$((count/2))]}"
  else
    mid=$((count/2))
    median=$(echo "scale=2; (${sorted[$((mid-1))]} + ${sorted[$mid]}) / 2" | bc)
  fi

  table_data+="\n${filename}\t${min}ms\t${max}ms\t${avg}ms\t${median}ms\t${count}/${RUNS}_OK"
done

# Format and pipe using tee to show live AND save to file
echo -e "$table_data" | column -ts $'\t' | tee "$OUTDIR/benchmark_report.txt"

echo -e "\nReport saved to: $OUTDIR/benchmark_report.txt"
