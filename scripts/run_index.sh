#!/usr/bin/env bash
set -euo pipefail

CORPUS=${1:-data/processed/documents.jsonl}
CONFIG=${2:-config/retrieval.yaml}
OUT_BASE=${3:-outputs/retrieval}

echo "[INDEX] Dense index..."
python -m src.retrieval.dense_index --corpus "$CORPUS" --config "$CONFIG" --output "$OUT_BASE/dense_index"

echo "[INDEX] BM25 index..."
python -m src.retrieval.bm25_index --corpus "$CORPUS" --config "$CONFIG" --output "$OUT_BASE/bm25_index"

echo "[INDEX] Verifying..."
test -f "$OUT_BASE/dense_index/faiss.index" && echo "  - Dense OK" || { echo "Dense index missing"; exit 1; }
test -f "$OUT_BASE/bm25_index/bm25_index.pkl" && echo "  - BM25 OK" || { echo "BM25 index missing"; exit 1; }

echo "[INDEX] Done."

