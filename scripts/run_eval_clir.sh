#!/usr/bin/env bash
set -euo pipefail

CORPUS=${1:-data/processed/documents.jsonl}
QRELS=${2:-data/qrels/test.qrels}
QUERIES=${3:-data/qrels/queries.tsv}
CONFIG=${4:-config/retrieval.yaml}
OUT=${5:-outputs/retrieval/eval_results.json}

python -m src.retrieval.evaluate_clir \
  --corpus "$CORPUS" \
  --qrels "$QRELS" \
  --queries "$QUERIES" \
  --config "$CONFIG" \
  --output "$OUT" \
  --top_k 10

echo "[EVAL] Results saved to $OUT"

