#!/usr/bin/env bash
set -euo pipefail

OUTPUT_DIR="tests/outputs"
OLDER_THAN=""
DRY_RUN=false

usage() {
  cat <<EOF
Usage: $0 [OPTIONS]

Options:
  --older-than DAYS   Delete dirs older than N days
  --dry-run           Show what would be deleted without deleting
  --all               Delete everything in $OUTPUT_DIR
  -h, --help          Show this help
EOF
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --older-than) OLDER_THAN="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    --all) OLDER_THAN=""; shift ;;
    -h|--help) usage ;;
    *) echo "Unknown option: $1" >&2; usage ;;
  esac
done

if [ ! -d "$OUTPUT_DIR" ]; then
  echo "No output dir at $OUTPUT_DIR"
  exit 0
fi

echo "=== Test Outputs: $OUTPUT_DIR ==="
echo ""

mapfile -t dirs < <(find "$OUTPUT_DIR" -maxdepth 1 -mindepth 1 -type d | sort)

if [ ${#dirs[@]} -eq 0 ]; then
  echo "No output directories found."
  exit 0
fi

echo "Found ${#dirs[@]} output directories:"
echo ""

targets=()
for dir in "${dirs[@]}"; do
  name=$(basename "$dir")
  size=$(du -sh "$dir" | cut -f1)
  mod=$(stat -c "%y" "$dir" | cut -d. -f1)

  if [ -n "$OLDER_THAN" ]; then
    age_days=$(( ($(date +%s) - $(stat -c "%Y" "$dir")) / 86400 ))
    if [ "$age_days" -lt "$OLDER_THAN" ]; then
      continue
    fi
  fi

  printf "  %-25s size: %8s  modified: %s\n" "$name" "$size" "$mod"
  targets+=("$dir")
done

echo ""

if [ ${#targets[@]} -eq 0 ]; then
  echo "No directories match criteria for deletion."
  exit 0
fi

if [ "$DRY_RUN" = true ]; then
  echo "Would delete ${#targets[@]} directories (dry-run, no action taken)."
  exit 0
fi

echo "Delete ${#targets[@]} directories listed above?"
select confirm in "yes" "no"; do
  case "$confirm" in
    yes)
      for dir in "${targets[@]}"; do
        rm -rf "$dir"
        echo "Deleted: $dir"
      done
      echo "Done."
      break
      ;;
    no)
      echo "Aborted."
      exit 1
      ;;
  esac
done
