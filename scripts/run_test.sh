#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_URL="${1:-http://localhost:8000}"

echo "STARTING ALL OCR PIPELINE BENCHMARKS"
echo "Target URL: $BASE_URL"

if [ -f "$SCRIPT_DIR/test_ocr.sh" ]; then
    echo ">> [1/4] Running OCR Parsing & Extraction Pipeline..."
    bash "$SCRIPT_DIR/test_ocr.sh"
    echo ""
fi

if [ -f "$SCRIPT_DIR/benchmark.sh" ]; then
    echo ">> [2/4] Running Performance Benchmarks..."
    bash "$SCRIPT_DIR/benchmark.sh" "3" "$BASE_URL"
    echo ""
fi

if [ -f "$SCRIPT_DIR/compare_runs.sh" ]; then
    echo ">> [3/4] Running Output Consistency Comparisons..."
    bash "$SCRIPT_DIR/compare_runs.sh" "$BASE_URL"
    echo ""
fi

if [ -f "$SCRIPT_DIR/stress.sh" ]; then
    echo ">> [4/4] Running High-Concurrency Stress Profile..."
    bash "$SCRIPT_DIR/stress.sh" "5" "$BASE_URL"
    echo ""
fi

echo "ALL TEST PIPELINES EXECUTED SUCCESSFULLY"
