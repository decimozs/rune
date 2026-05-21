#!/usr/bin/env bash
set -euo pipefail

OUTDIR="tests/outputs/test_ocr_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTDIR"

if [ ! -d "app/datasets" ] || [ -z "$(ls -A app/datasets 2>/dev/null)" ]; then
  echo "Error: app/datasets directory is missing or empty." >&2
  exit 1
fi

for filepath in app/datasets/*; do
  [ -d "$filepath" ] && continue

  filename=$(basename "$filepath")
  echo "Processing $filename"

  curl -s -X POST "http://localhost:8000/ocr/parse" \
    -F "file=@$filepath" \
    | jq . > "$OUTDIR/${filename}.json"

  curl -s -X POST "http://localhost:8000/ocr/parse?format=markdown" \
    -F "file=@$filepath" \
    | jq -r '.data' > "$OUTDIR/${filename}.md"

  echo "$filename done"
done

echo "All done. Files saved in: $OUTDIR"
ls -lh "$OUTDIR"
