#!/usr/bin/env bash
set -euo pipefail

RUNS=3
BASE_URL="http://localhost:8000"
FORMAT="all"
PARALLEL=1
JSON_ONLY=false
SORT_BY="avg"

_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --parallel) PARALLEL="$2"; shift 2 ;;
    --json) JSON_ONLY=true; shift ;;
    --sort) SORT_BY="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: $0 [runs=3] [url=http://localhost:8000] [format=all] [--parallel N] [--json] [--sort=avg|name|size]"
      exit 0 ;;
    -*) echo "error: unknown flag $1" >&2; exit 1 ;;
    *) _ARGS+=("$1"); shift ;;
  esac
done
[[ ${#_ARGS[@]} -ge 1 ]] && RUNS="${_ARGS[0]}"
[[ ${#_ARGS[@]} -ge 2 ]] && BASE_URL="${_ARGS[1]}"
[[ ${#_ARGS[@]} -ge 3 ]] && FORMAT="${_ARGS[2]}"

DATASET_DIR="app/datasets"
OUTDIR="tests/outputs/benchmarks_$(date +%Y%m%d_%H%M%S)"

if [ ! -d "$DATASET_DIR" ] || [ -z "$(ls -A "$DATASET_DIR" 2>/dev/null)" ]; then
  echo "Error: $DATASET_DIR missing or empty" >&2; exit 1
fi
if ! curl -sf --connect-timeout 2 "$BASE_URL/docs" > /dev/null 2>&1; then
  echo "Error: Server not running at $BASE_URL" >&2; exit 1
fi

mkdir -p "$OUTDIR/json" "$OUTDIR/markdown"
_BTMP=$(mktemp -d)
trap 'rm -rf "$_BTMP"' EXIT

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
get_category() {
  case "$1" in
    *.png|*.jpg|*.jpeg|*.bmp|*.tiff|*.webp) echo "image" ;;
    *.docx|*.ppt|*.pptx|*.rtf) echo "office" ;;
    *.csv|*.xls|*.xlsx) echo "spreadsheet" ;;
    *) echo "other" ;;
  esac
}
resolve_name() { local rel="${1#$DATASET_DIR/}"; echo "$rel"; }
fmt_size() {
  local bytes=$(stat --printf="%s" "$1" 2>/dev/null || echo 0)
  if [ "$bytes" -lt 1024 ]; then echo "${bytes}B"
  elif [ "$bytes" -lt 1048576 ]; then echo "$(echo "scale=1; $bytes/1024" | bc)KB"
  else echo "$(echo "scale=1; $bytes/1048576" | bc)MB"
  fi
}
collect_files() {
  case "$FORMAT" in
    images)
      find "$DATASET_DIR/images" -type f \( -iname "*.png" -o -iname "*.jpg" -o -iname "*.jpeg" \
        -o -iname "*.bmp" -o -iname "*.tiff" -o -iname "*.webp" \) -print0 ;;
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
           -o -name "*.rtf" -o -name "*.csv" -o -name "*.xls" -o -name "*.xlsx" \) -print0 ;;
  esac
}

compute_stats() {
  local -n arr=$1
  local count=$2 ok=$3 fail=$4
  if [ "$count" -eq 0 ]; then
    echo '{"min":0,"max":0,"avg":0,"median":0,"p90":0,"p95":0,"p99":0,"stddev":0,"ok":0,"fail":0}'; return
  fi
  local min="${arr[0]}" max="${arr[$((count-1))]}" sum=0
  for t in "${arr[@]}"; do sum=$(echo "$sum + $t" | bc); done
  local avg=$(echo "scale=2; $sum / $count" | bc)
  local mid=$((count/2))
  local median
  if ((count % 2 == 1)); then median="${arr[$mid]}"
  else median=$(echo "scale=2; (${arr[$((mid-1))]} + ${arr[$mid]}) / 2" | bc); fi
  local p90_idx=$(( (90 * count + 99) / 100 - 1 )); [ "$p90_idx" -lt 0 ] && p90_idx=0
  local p95_idx=$(( (95 * count + 99) / 100 - 1 )); [ "$p95_idx" -lt 0 ] && p95_idx=0
  local p99_idx=$(( (99 * count + 99) / 100 - 1 )); [ "$p99_idx" -lt 0 ] && p99_idx=0
  local p90="${arr[$p90_idx]}" p95="${arr[$p95_idx]}" p99="${arr[$p99_idx]}"
  local sum_sq=0
  for t in "${arr[@]}"; do sum_sq=$(echo "scale=6; $sum_sq + ($t - $avg)^2" | bc -l 2>/dev/null || echo "$sum_sq"); done
  local stddev=$(echo "scale=2; sqrt($sum_sq / $count)" | bc -l 2>/dev/null || echo "0")
  printf '{"min":%s,"max":%s,"avg":%s,"median":%s,"p90":%s,"p95":%s,"p99":%s,"stddev":%s,"ok":%d,"fail":%d}' \
    "$min" "$max" "$avg" "$median" "$p90" "$p95" "$p99" "$stddev" "$ok" "$fail"
}

process_file() {
  local filepath="$1" display="$2" mime="$3" category="$4" size_str="$5" safe_name="$6"
  local times_json=() times_md=()
  local json_resp="" md_resp=""
  local json_ok=0 json_fail=0 md_ok=0 md_fail=0

  for ((i=1; i<=RUNS; i++)); do
    if [ -n "$mime" ]; then
      resp=$(curl -sf --connect-timeout 30 --max-time 300 -X POST "$BASE_URL/ocr/parse?format=json" \
        -F "file=@$filepath;type=$mime" 2>/dev/null || true)
    else
      resp=$(curl -sf --connect-timeout 30 --max-time 300 -X POST "$BASE_URL/ocr/parse?format=json" \
        -F "file=@$filepath" 2>/dev/null || true)
    fi
    ms=$(echo "$resp" | jq -r '.metadata.processing_time_ms // empty' 2>/dev/null || true)
    if [ -n "$ms" ] && [ "$ms" != "null" ]; then
      times_json+=("$ms"); ((json_ok++))
      json_resp="$resp"
    else
      ((json_fail++))
    fi
  done

  for ((i=1; i<=RUNS; i++)); do
    if [ -n "$mime" ]; then
      resp=$(curl -sf --connect-timeout 30 --max-time 300 -X POST "$BASE_URL/ocr/parse?format=markdown" \
        -F "file=@$filepath;type=$mime" 2>/dev/null || true)
    else
      resp=$(curl -sf --connect-timeout 30 --max-time 300 -X POST "$BASE_URL/ocr/parse?format=markdown" \
        -F "file=@$filepath" 2>/dev/null || true)
    fi
    ms=$(echo "$resp" | jq -r '.metadata.processing_time_ms // empty' 2>/dev/null || true)
    if [ -n "$ms" ] && [ "$ms" != "null" ]; then
      times_md+=("$ms"); ((md_ok++))
      md_resp="$resp"
    else
      ((md_fail++))
    fi
  done

  IFS=$'\n' sorted_json=($(sort -n <<< "${times_json[*]}")); unset IFS
  IFS=$'\n' sorted_md=($(sort -n <<< "${times_md[*]}")); unset IFS

  local json_stats md_stats
  json_stats=$(compute_stats sorted_json "${#sorted_json[@]}" "$json_ok" "$json_fail")
  md_stats=$(compute_stats sorted_md "${#sorted_md[@]}" "$md_ok" "$md_fail")

  if [ -n "$json_resp" ]; then echo "$json_resp" | jq . > "$OUTDIR/json/${safe_name}.json" 2>/dev/null || true; fi
  if [ -n "$md_resp" ]; then echo "$md_resp" | jq . > "$OUTDIR/markdown/${safe_name}.json" 2>/dev/null || true; fi

  printf '{"file":"%s","display":"%s","category":"%s","size":"%s","size_bytes":%d,"json":%s,"markdown":%s}' \
    "$safe_name" "$display" "$category" "$size_str" "$(stat --printf="%s" "$filepath" 2>/dev/null || echo 0)" \
    "$json_stats" "$md_stats"
}

# === collect files ===
FILES=()
while IFS= read -r -d '' f; do
  [ -f "$f" ] && FILES+=("$f")
done < <(collect_files)
[ ${#FILES[@]} -eq 0 ] && echo "Error: no files found" >&2 && exit 1

total_files=${#FILES[@]}
all_results=()
wave_records=()
overall_start=$(date +%s%3N)

if ((PARALLEL > 1)); then
  for ((start=0; start<total_files; start+=PARALLEL)); do
    end=$((start + PARALLEL)); [ "$end" -gt "$total_files" ] && end=$total_files
    nfiles=$((end - start))
    wave_start=$(date +%s%3N)

    for ((i=start; i<end; i++)); do
      (
        f="${FILES[$i]}"
        disp=$(resolve_name "$f")
        safe=$(echo "$disp" | tr / _)
        mime=$(get_mime "$f")
        cat=$(get_category "$f")
        sz=$(fmt_size "$f")
        result=$(process_file "$f" "$disp" "$mime" "$cat" "$sz" "$safe")
        echo "$result" > "$_BTMP/result_${i}.json"
      ) &
    done
    wait

    wave_end=$(date +%s%3N)
    wave_elapsed=$((wave_end - wave_start))
    wave_throughput=$(echo "scale=2; $nfiles / ($wave_elapsed / 1000)" | bc -l 2>/dev/null || echo "0")
    wave_records+=("$((start/PARALLEL+1))" "$nfiles" "$wave_elapsed" "$wave_throughput")

    for ((i=start; i<end; i++)); do
      r=$(cat "$_BTMP/result_${i}.json" 2>/dev/null || true)
      [ -n "$r" ] && all_results+=("$r")
    done
  done
else
  for ((i=0; i<total_files; i++)); do
    f="${FILES[$i]}"
    disp=$(resolve_name "$f")
    safe=$(echo "$disp" | tr / _)
    mime=$(get_mime "$f")
    cat=$(get_category "$f")
    sz=$(fmt_size "$f")
    result=$(process_file "$f" "$disp" "$mime" "$cat" "$sz" "$safe")
    all_results+=("$result")
  done
fi

overall_end=$(date +%s%3N)
overall_elapsed=$((overall_end - overall_start))

# sort results
SortedResults=("${all_results[@]}")
if command -v jq &>/dev/null && [ ${#all_results[@]} -gt 0 ]; then
  case "$SORT_BY" in
    avg)  SortedResults=($(printf '%s\n' "${all_results[@]}" | jq -s 'sort_by(.json.avg) | reverse | .[]' -c 2>/dev/null || true)) ;;
    name) SortedResults=($(printf '%s\n' "${all_results[@]}" | jq -s 'sort_by(.display) | .[]' -c 2>/dev/null || true)) ;;
    size) SortedResults=($(printf '%s\n' "${all_results[@]}" | jq -s 'sort_by(.size_bytes) | reverse | .[]' -c 2>/dev/null || true)) ;;
  esac
  [ ${#SortedResults[@]} -eq 0 ] && SortedResults=("${all_results[@]}")
fi

# JSON summary
printf '%s\n' "${all_results[@]}" > "$_BTMP/all_results.jsonl"
WAVES_JSON="[]"
if ((PARALLEL > 1 && ${#wave_records[@]} > 0)); then
  WAVES_JSON="["
  for ((w=0; w<${#wave_records[@]}; w+=4)); do
    [ "$w" -gt 0 ] && WAVES_JSON+=","
    WAVES_JSON+='{"num":'"${wave_records[$w]}"',"files":'"${wave_records[$((w+1))]}"',"elapsed_ms":'"${wave_records[$((w+2))]}"',"throughput_fps":'"${wave_records[$((w+3))]}"'}'
  done
  WAVES_JSON+="]"
fi

jq -s --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
     --argjson runs "$RUNS" \
     --arg format "$FORMAT" \
     --arg target "$BASE_URL" \
     --argjson parallel "$PARALLEL" \
     --arg sort_by "$SORT_BY" \
     --argjson elapsed "$overall_elapsed" \
     --argjson waves "$WAVES_JSON" \
  '{
    timestamp: $ts,
    runs: $runs,
    format: $format,
    target: $target,
    parallel: $parallel,
    sort_by: $sort_by,
    total_files: length,
    total_elapsed_ms: $elapsed,
    total_elapsed_s: ($elapsed / 1000),
    throughput_files_per_min: (length / ($elapsed / 60000)),
    waves: $waves,
    files: [.[] | {file: .display, category: .category, size: .size, size_bytes: .size_bytes, json: .json, markdown: .markdown}]
  }' "$_BTMP/all_results.jsonl" > "$OUTDIR/summary.json" 2>/dev/null || true

total_ok=$(jq '[.[].json.ok, .[].markdown.ok] | add' "$_BTMP/all_results.jsonl" 2>/dev/null || echo 0)
total_fail=$(jq '[.[].json.fail, .[].markdown.fail] | add' "$_BTMP/all_results.jsonl" 2>/dev/null || echo 0)

# === output ===
if [ "$JSON_ONLY" = true ]; then
  jq . "$OUTDIR/summary.json"
  exit 0
fi

{
  desc="$FORMAT"; [ "$FORMAT" = "all" ] && desc="all"
  echo "Benchmark: $RUNS runs per file (json + markdown), format=$desc, target=$BASE_URL"
  echo "Parallel: ${PARALLEL} concurrent | Files: ${total_files} | Elapsed: $(echo "scale=1; $overall_elapsed/1000" | bc -l)s"
  echo ""

  if ((PARALLEL > 1 && ${#wave_records[@]} > 0)); then
    printf '=== Waves ===\n'
    printf '%-6s %-6s %-10s %-10s\n' 'WAVE' 'FILES' 'WALL(s)' 'FILES/s'
    printf '%-6s %-6s %-10s %-10s\n' '─────' '─────' '───────' '───────'
    for ((w=0; w<${#wave_records[@]}; w+=4)); do
      printf '%-6d %-6d %-10.1f %-10.2f\n' \
        "${wave_records[$w]}" "${wave_records[$((w+1))]}" \
        "$(echo "scale=1; ${wave_records[$((w+2))]}/1000" | bc -l)" \
        "${wave_records[$((w+3))]}"
    done
    echo ""
  fi

  printf '%-36s %-10s %7s %8s %8s %7s %8s %8s %7s\n' \
    'FILE' 'CAT' 'SIZE' 'J_AVG' 'J_P95' 'J_OK' 'M_AVG' 'M_P95' 'M_OK'
  printf '%-36s %-10s %7s %8s %8s %7s %8s %8s %7s\n' \
    '────────────────────────────────────' '──────────' '──────' '───────' '───────' '─────' '───────' '───────' '─────'

  for result in "${SortedResults[@]}"; do
    file=$(echo "$result" | jq -r '.display // "?"')
    cat=$(echo "$result" | jq -r '.category // "?"')
    size=$(echo "$result" | jq -r '.size // "?"')
    j_avg=$(echo "$result" | jq -r '.json.avg // "?"')
    j_p95=$(echo "$result" | jq -r '.json.p95 // "?"')
    j_ok=$(echo "$result" | jq -r '"\(.json.ok)/\(.json.fail)" // "?"')
    m_avg=$(echo "$result" | jq -r '.markdown.avg // "?"')
    m_p95=$(echo "$result" | jq -r '.markdown.p95 // "?"')
    m_ok=$(echo "$result" | jq -r '"\(.markdown.ok)/\(.markdown.fail)" // "?"')

    printf '%-36s %-10s %7s %8s %8s %7s %8s %8s %7s\n' \
      "$file" "$cat" "$size" "$j_avg" "$j_p95" "$j_ok" "$m_avg" "$m_p95" "$m_ok"
  done

  echo ""
  printf 'TOTALS: %d files, %d/%d OK (%d failed)\n' "$total_files" "$total_ok" "$((total_ok+total_fail))" "$total_fail"
  printf 'Throughput: %.2f files/min | Elapsed: %.1fs\n' \
    "$(echo "scale=2; $total_files / ($overall_elapsed / 60000)" | bc -l 2>/dev/null || echo "0")" \
    "$(echo "scale=1; $overall_elapsed/1000" | bc -l)"

  echo ""
  echo "Report:      $OUTDIR/benchmark_report.txt"
  echo "JSON:        $OUTDIR/summary.json"
  echo "Per-file:    $OUTDIR/json/ + $OUTDIR/markdown/"
} | tee "$OUTDIR/benchmark_report.txt"
