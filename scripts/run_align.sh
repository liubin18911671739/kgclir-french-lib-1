#!/usr/bin/env bash
set -euo pipefail

echo "[ALIGN] Running two-stage alignment pipeline..."
PYTHON=${PYTHON:-python}
CONFIG=${1:-config/align.yaml}
OUTDIR=${2:-outputs/alignment}

$PYTHON - <<PY
from src.align.align_pipeline import AlignmentPipeline
from src.kg.ontology import FLOOntology
from src.utils.io import load_yaml
from src.align.mtrans_e import AlignmentPair

config = load_yaml("$CONFIG")
ontology = FLOOntology()  # NOTE: replace with FLOOntology.from_json(...) when available
pipeline = AlignmentPipeline(config, ontology)
seed_alignments = []  # TODO: load from config if available
stats = pipeline.run(seed_alignments, validation_alignments=None, output_dir="$OUTDIR")
print("[ALIGN] Stats:", stats)
PY

echo "[ALIGN] Done."

