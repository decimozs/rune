#!/usr/bin/env bash
set -euo pipefail

RUNS="${1:-3}"
BASE_URL="${2:-http://localhost:8000}"
FORMAT="${3:-all}"

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

collect_files() {
  case "$FORMAT" in
    images)
      find "$DATASET_DIR/images" -type f \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.jpeg" \
        -o -iname "*.bmp" -o -iname "*.tiff" -o -iname "*.webp" \) -print0
      ;;
    docx) find "$DATASET_DIR/docx" -type f -name "*.docx" -print0 ;;
    ppt)  find "$DATASET_DIR/ppt"  -type f \( -name "*.ppt" -o -name "*.pptx" \) -print0 ;;
    rtf)  find "$DATASET_DIR/rtf"  -type f -name "*.rtf" -print0 ;;
    csv)  find "$DATASET_DIR/spreadsheets" -type f -name "*.csv" -print0 ;;
    xls)  find "$DATASET_DIR/spreadsheets" -type f -name "*.xls" -print0 ;;
    xlsx) find "$DATASET_DIR/spreadsheets" -type f -name "*.xlsx" -print0 ;;
    all|*)
      find "$DATASET_DIR" -type f \
        \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.jpeg" \
           -o -iname "*.bmp" -o -iname "*.tiff" -o -iname "*.webp" \
           -o -name "*.docx" -o -name "*.ppt" -o -name "*.pptx" \
           -o -name "*.rtf" -o -name "*.csv" -o -name "*.xls" -o -name "*.xlsx" \) -print0
      ;;
  esac
}

resolve_name() {
  local rel="${1#$DATASET_DIR/}"
  echo "$rel"
}

mkdirok() {
  mkdir -p "$OUTDIR/$1"
}

mkdirok "json"
mkdirok "markdown"

desc="$FORMAT"
[ "$FORMAT" = "all" ] && desc="all"
echo "Benchmark: $RUNS runs per file (json + markdown), format=$desc, target=$BASE_URL"
echo ""

table_data="FILE\tFORMAT\tMIN\tMAX\tAVG(ms)\tAVG(s)\tMEDIAN\tSTATUS"

while IFS= read -r -d '' filepath; do
  [ -f "$filepath" ] || continue
  display=$(resolve_name "$filepath")
  mime=$(get_mime "$filepath")

  for fmt in json markdown; do
    times=()
    for ((i=1; i<=RUNS; i++)); do
      if [ -n "$mime" ]; then
        resp=$(curl -sf -X POST "$BASE_URL/ocr/parse?format=$fmt" \
          -F "file=@$filepath;type=$mime" 2>/dev/null)
      else
        resp=$(curl -sf -X POST "$BASE_URL/ocr/parse?format=$fmt" \
          -F "file=@$filepath" 2>/dev/null)
      fi
      ms=$(echo "$resp" | jq -r '.metadata.processing_time_ms // empty')
      if [ -n "$ms" ]; then
        times+=("$ms")
      fi
    done

    # Save best run output
    if [ -n "$resp" ]; then
      echo "$resp" | jq . > "$OUTDIR/$fmt/${display//\//_}.json"
    fi

    if [ ${#times[@]} -eq 0 ]; then
      table_data+="\n${display}\t${fmt}\t-\t-\t-\t-\t-\tFAILED"
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

    avg_s=$(echo "scale=2; $avg / 1000" | bc)
    table_data+="\n${display}\t${fmt}\t${min}ms\t${max}ms\t${avg}ms\t${avg_s}s\t${median}ms\t${count}/${RUNS}_OK"
  done
done < <(collect_files)

echo -e "$table_data" | column -ts $'\t' | tee "$OUTDIR/benchmark_report.txt"
echo -e "\nReport saved to: $OUTDIR/benchmark_report.txt"
