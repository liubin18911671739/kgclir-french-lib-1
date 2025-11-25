#!/usr/bin/env bash
set -euo pipefail

LOG=outputs/experiment.log
mkdir -p outputs

echo "=========================================" | tee "$LOG"
echo "KG-CLIR Complete Experiment Pipeline" | tee -a "$LOG"
echo "=========================================" | tee -a "$LOG"

step() { echo "\n[Step] $1" | tee -a "$LOG"; }

step "1/6 Environment validation"
python scripts/check_environment.py || { echo "❌ Environment check failed" | tee -a "$LOG"; exit 1; }

step "2/6 Data preparation"
python scripts/prepare_corpus.py --input data/processed/documents.jsonl --input_format jsonl --text_field text --id_field doc_id --language fr --output outputs/retrieval/corpus.jsonl --no_lang_verify || true

step "3/6 Build knowledge graph"
bash scripts/run_build_kg.sh

step "4/6 Cross-lingual alignment"
bash scripts/run_align.sh

step "5/6 Build indexes"
bash scripts/run_index.sh outputs/retrieval/corpus.jsonl config/retrieval.yaml outputs/retrieval

step "6/6 Retrieval evaluation"
bash scripts/run_eval_clir.sh outputs/retrieval/corpus.jsonl data/qrels/test.qrels data/qrels/queries.tsv config/retrieval.yaml outputs/retrieval/eval_results.json

echo "\n✅ Pipeline completed" | tee -a "$LOG"

