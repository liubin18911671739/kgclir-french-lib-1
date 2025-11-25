#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FastAPI Backend
后端API（按TODO要求实现四个核心端点+基础设施）
"""

from __future__ import annotations

import time
from typing import Dict, Optional, List
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..utils.logger import logger, setup_logging
from ..utils.io import load_yaml
from ..kg.ontology import FLOOntology
from ..retrieval.kg_rerank import KGReranker, SearchResult
from ..retrieval.kg_expansion import KGQueryExpander
from ..learning.path_recommend import PathRecommender
from ..learning.learner_model import LearnerModel
from ..learning.rag_exercise import RAGExerciseGenerator
from .schemas import (
    QueryRequest,
    SearchResponse,
    SearchResultItem,
    ExerciseRequest,
    ExerciseResponse,
    ExerciseQA,
    LearningPathRequest,
    LearningPathResponse,
    PathNode,
)


# ========== App setup ==========
setup_logging(log_file="logs/api.log", level="INFO")
config: Dict = load_yaml("config/app.yaml")

app = FastAPI(
    title=config.get("api", {}).get("docs", {}).get("title", "KG-CLIR API"),
    description=config.get("api", {}).get("docs", {}).get("description", ""),
    version=config.get("api", {}).get("docs", {}).get("version", "1.0.0"),
    openapi_url=config.get("api", {}).get("docs", {}).get("openapi_url", "/openapi.json"),
    docs_url=config.get("api", {}).get("docs", {}).get("docs_url", "/docs"),
    redoc_url=config.get("api", {}).get("docs", {}).get("redoc_url", "/redoc"),
)

# CORS
cors_cfg = config.get("api", {}).get("cors", {})
if cors_cfg.get("enabled", True):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_cfg.get("allow_origins", ["*"]),
        allow_methods=cors_cfg.get("allow_methods", ["*"]),
        allow_headers=cors_cfg.get("allow_headers", ["*"]),
        allow_credentials=cors_cfg.get("allow_credentials", True),
    )


# ========== Global state ==========
ontology: Optional[FLOOntology] = None
kg_reranker: Optional[KGReranker] = None
kg_expander: Optional[KGQueryExpander] = None
path_recommender: Optional[PathRecommender] = None
rag_generator: Optional[RAGExerciseGenerator] = None


# ========== Error handling ==========
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(status_code=500, content={"status": "error", "message": str(exc)})


# ========== Rate limiting (simple in-memory per-IP) ==========
rate_cfg = config.get("api", {}).get("rate_limiting", {"enabled": True, "requests_per_minute": 60, "burst": 10})
RATE_ENABLED = rate_cfg.get("enabled", True)
REQ_PER_MIN = int(rate_cfg.get("requests_per_minute", 60))
BURST = int(rate_cfg.get("burst", 10))
WINDOW = 60.0

_rate_store: Dict[str, Dict[str, float]] = defaultdict(lambda: {"count": 0.0, "window_start": time.time()})


async def _check_rate_limit(request: Request):
    if not RATE_ENABLED:
        return
    client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown").split(",")[0].strip()
    record = _rate_store[client_ip]
    now = time.time()
    # reset window
    if now - record["window_start"] >= WINDOW:
        record["count"] = 0
        record["window_start"] = now
    # allow burst
    if record["count"] >= REQ_PER_MIN + BURST:
        raise HTTPException(status_code=429, detail="Too Many Requests")
    record["count"] += 1


# ========== Startup ==========
@app.on_event("startup")
async def on_startup():
    global ontology, kg_reranker, path_recommender, rag_generator, kg_expander
    logger.info("Starting API and loading resources...")
    # 加载（此处演示：构建空本体；生产应从文件加载）
    ontology = FLOOntology()
    kg_reranker = KGReranker(ontology=ontology)
    kg_expander = KGQueryExpander(ontology=ontology)
    path_recommender = PathRecommender(ontology)
    rag_generator = RAGExerciseGenerator(ontology=ontology, kg_expander=kg_expander)
    logger.info("Resources ready")


# ========== Endpoints ==========
@app.get("/health")
async def health(request: Request):
    await _check_rate_limit(request)
    return {
        "status": "ok",
        "entities": len(ontology.entities) if ontology else 0,
        "relations": len(ontology.relations) if ontology else 0,
    }


@app.post("/search", response_model=SearchResponse)
async def search(request: Request, body: QueryRequest):
    await _check_rate_limit(request)
    if not ontology or not kg_reranker:
        raise HTTPException(status_code=503, detail="Service not ready")

    start = time.time()

    # 简化：使用dummy候选 + KG重排
    top_k = body.top_k
    dummy_results = [
        SearchResult(
            doc_id=f"doc_{i}",
            title=f"Document {i}",
            content=f"Sample content about {body.query} #{i}",
            language=body.language,
            bm25_score=max(0.0, 0.9 - i * 0.02),
            dense_score=max(0.0, 0.85 - i * 0.02),
            kg_score=max(0.0, 0.8 - i * 0.02),
        )
        for i in range(top_k)
    ]

    reranked = kg_reranker.rerank(
        query=body.query,
        query_language=body.language,
        results=dummy_results,
        top_k=top_k,
    ) if body.use_kg else dummy_results

    # KG扩展（用于响应）
    qexp = list((kg_expander.expand_query(body.query) or {}).keys()) if body.use_kg and kg_expander else None

    items: List[SearchResultItem] = []
    for r in reranked:
        items.append(
            SearchResultItem(
                doc_id=r.doc_id,
                title=r.title,
                snippet=(r.content[:200] + "...") if r.content else None,
                language=r.language,
                score=r.final_score,
                scores_breakdown={"bm25": r.bm25_score, "dense": r.dense_score, "kg": r.kg_score},
            )
        )

    return SearchResponse(
        results=items,
        total=len(items),
        query=body.query,
        query_expansion=qexp,
        processing_time_ms=(time.time() - start) * 1000.0,
    )


@app.post("/recommend", response_model=LearningPathResponse)
async def recommend(request: Request, body: LearningPathRequest):
    await _check_rate_limit(request)
    if not ontology or not path_recommender:
        raise HTTPException(status_code=503, detail="Service not ready")
    start = time.time()
    learner = LearnerModel(learner_id=body.user_id, current_level="A1", ontology=ontology)
    path = path_recommender.recommend_path(learner=learner, target_level=body.target_level, max_nodes=body.max_nodes)

    nodes: List[PathNode] = []
    edges: List[List[str]] = []
    # 构造边：先修关系（简单从节点prerequisites）
    id_set = {n.entity_id for n in path.nodes}
    for n in path.nodes:
        nodes.append(PathNode(
            entity_id=n.entity_id,
            name=n.entity_name,
            difficulty=n.difficulty,
            estimated_time=n.estimated_time,
            prerequisites=n.prerequisites,
        ))
        for pre in (n.prerequisites or []):
            if pre in id_set:
                edges.append([pre, n.entity_id])

    return LearningPathResponse(
        user_id=body.user_id,
        target_level=body.target_level,
        path_nodes=nodes,
        path_edges=edges,
        total_time=path.total_time,
        processing_time_ms=(time.time() - start) * 1000.0,
    )


@app.post("/exercise", response_model=ExerciseResponse)
async def exercise(request: Request, body: ExerciseRequest):
    await _check_rate_limit(request)
    if not rag_generator:
        raise HTTPException(status_code=503, detail="Service not ready")
    start = time.time()

    data = rag_generator.generate_exercises(query=body.concept, num_questions=body.num_questions, top_k=5)
    exercises: List[ExerciseQA] = []
    for ex in data.get("exercises", []):
        exercises.append(ExerciseQA(**ex))

    return ExerciseResponse(
        concept=body.concept,
        user_level=body.user_level,
        exercises=exercises,
    )


# ========== Run ==========
def run():
    import uvicorn
    host = config.get("api", {}).get("server", {}).get("host", "0.0.0.0")
    port = int(config.get("api", {}).get("server", {}).get("port", 8000))
    reload = bool(config.get("api", {}).get("server", {}).get("reload", True))
    uvicorn.run("src.app.api:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    run()
