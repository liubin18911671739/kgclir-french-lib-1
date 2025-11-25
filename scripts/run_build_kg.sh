#!/usr/bin/env bash
set -euo pipefail

echo "[KG] Building knowledge graph..."
CONFIG=${1:-config/kg.yaml}

python -m src.kg.build_kg --config "$CONFIG"
echo "[KG] Done."

