#!/usr/bin/env bash
set -euo pipefail

VALID_FORMATS="docx ppt rtf csv xls xlsx spreadsheet all"
FORMAT="${1:-}"
GOTENBERG_URL="${2:-http://localhost:3000}"

usage() {
  cat <<EOF
Usage: $0 <format> [gotenberg_url]

Formats:
  docx, ppt, rtf          — Office documents
  csv, xls, xlsx          — Spreadsheets (per-type)
  spreadsheet             — All spreadsheet types at once
  all                     — Every format above

Examples:
  $0 docx
  $0 spreadsheet http://localhost:3001
  $0 all
EOF
  exit 1
}

[ -z "$FORMAT" ] && usage
if [ "$FORMAT" != "all" ]; then
  echo "$VALID_FORMATS" | grep -qw "$FORMAT" || usage
fi

# ── Gotenberg health check ────────────────────────────────────────────
check_gotenberg() {
  if ! curl -sf --connect-timeout 5 "$GOTENBERG_URL/health" > /dev/null 2>&1; then
    echo "Error: Gotenberg not reachable at $GOTENBERG_URL" >&2
    echo "Run: docker run -d -p 3000:3000 gotenberg/gotenberg:8" >&2
    exit 1
  fi
}

# ── Convert a single file ─────────────────────────────────────────────
convert_one() {
  local filepath="$1"
  local format="$2"
  local outdir="$3"

  local filename
  filename=$(basename "$filepath")
  local ext="${filename##*.}"
  local outname="${filename%.$ext}.pdf"
  local outpath="$outdir/$format/$outname"

  mkdir -p "$(dirname "$outpath")"
  printf "  %-60s" "$format/$filename"

  set +e
  local status_code
  status_code=$(curl -s -w "%{http_code}" \
    --connect-timeout 10 --max-time 90 \
    -o "$outpath" \
    -F "files=@$filepath" \
    -F "nativePageProperties=true" \
    "$GOTENBERG_URL/forms/libreoffice/convert")
  local curl_exit=$?
  set -e

  if [ $curl_exit -ne 0 ] || [ "$status_code" != "200" ]; then
    echo "FAILED"
    rm -f "$outpath"
    return 1
  fi
  echo "SUCCESS"
}

# ── Process one format ────────────────────────────────────────────────
process_format() {
  local format="$1"
  local input_dir find_args=()

  case "$format" in
    docx) input_dir="app/datasets/docx";         find_args=(-name "*.docx") ;;
    ppt)  input_dir="app/datasets/ppt";          find_args=("(" -name "*.ppt" -o -name "*.pptx" ")") ;;
    rtf)  input_dir="app/datasets/rtf";          find_args=(-name "*.rtf") ;;
    csv)  input_dir="app/datasets/spreadsheets"; find_args=(-name "*.csv") ;;
    xls)  input_dir="app/datasets/spreadsheets"; find_args=(-name "*.xls") ;;
    xlsx) input_dir="app/datasets/spreadsheets"; find_args=(-name "*.xlsx") ;;
  esac

  if [ ! -d "$input_dir" ]; then
    echo "Skip $format: $input_dir not found"
    return
  fi

  local date_stamp
  date_stamp=$(date +%Y-%m-%d)
  local outdir="tests/outputs/pdf/$date_stamp"

  echo "── $format ──"
  local success=0 fail=0

  while IFS= read -r -d '' filepath; do
    if convert_one "$filepath" "$format" "$outdir"; then
      success=$((success + 1))
    else
      fail=$((fail + 1))
    fi
  done < <(find "$input_dir" -type f "${find_args[@]}" -print0 2>/dev/null)

  echo "  Result: $success ok, $fail failed"
  echo ""
}

check_gotenberg

if [ "$FORMAT" = "all" ]; then
  for f in docx ppt rtf csv xls xlsx; do
    process_format "$f"
  done
elif [ "$FORMAT" = "spreadsheet" ]; then
  process_format "csv"
  process_format "xls"
  process_format "xlsx"
else
  process_format "$FORMAT"
fi

echo "Done. Output: tests/outputs/pdf/$(date +%Y-%m-%d)/"
