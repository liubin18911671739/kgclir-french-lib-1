#!/usr/bin/env bash
set -euo pipefail

echo "[APP] Starting services..."

if command -v docker >/dev/null 2>&1; then
  echo "[APP] (optional) Starting Neo4j and Elasticsearch via Docker (best-effort)"
  docker run -d --rm --name neo4j -p7474:7474 -p7687:7687 neo4j:5 || true
  docker run -d --rm --name es -p9200:9200 -e "discovery.type=single-node" docker.elastic.co/elasticsearch/elasticsearch:8.10.2 || true
else
  echo "[APP] Docker not found. Skipping Neo4j/Elasticsearch startup."
fi

echo "[APP] Launching FastAPI backend..."
uvicorn src.app.api:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

echo "[APP] Launching Gradio UI..."
python -m src.app.gradio_ui &
UI_PID=$!

trap 'echo "[APP] Stopping..."; kill $API_PID $UI_PID 2>/dev/null || true; exit 0' INT TERM

echo "[APP] Running. Press Ctrl+C to stop."
wait

