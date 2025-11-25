#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FastAPI Application
Web API服务

提供RESTful API接口：
- /search: 跨语言检索
- /recommend: 学习路径推荐
- /exercise: RAG生成练习
- /health: 健康检查
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import uvicorn

from ..utils.logger import logger, setup_logging
from ..utils.io import load_yaml
from ..kg.ontology import FLOOntology
from ..kg.export_kg import export_to_networkx
from ..retrieval.kg_rerank import KGReranker, SearchResult
from ..learning.path_recommend import PathRecommender, LearnerModel

# 初始化日志
setup_logging(log_file="logs/api.log", level="INFO")

# 创建FastAPI应用
app = FastAPI(
    title="KG-CLIR French Learning API",
    description="跨语言知识图谱检索与法语学习支持系统",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量（启动时加载）
ontology: Optional[FLOOntology] = None
kg_reranker: Optional[KGReranker] = None
path_recommender: Optional[PathRecommender] = None


# ==================== 请求/响应模型 ====================

class SearchRequest(BaseModel):
    """检索请求"""
    query: str = Field(..., description="查询文本")
    query_language: str = Field("zh", description="查询语言 (zh/fr/en)")
    target_language: str = Field("fr", description="目标语言 (zh/fr/en)")
    top_k: int = Field(10, ge=1, le=100, description="返回结果数量")
    use_kg: bool = Field(True, description="是否使用KG增强")


class SearchResponse(BaseModel):
    """检索响应"""
    results: List[Dict]
    total: int
    query: str
    processing_time_ms: float


class RecommendRequest(BaseModel):
    """路径推荐请求"""
    learner_id: str = Field(..., description="学习者ID")
    current_level: str = Field("A1", description="当前CEFR等级")
    target_level: str = Field("B1", description="目标CEFR等级")
    max_nodes: int = Field(20, ge=5, le=50, description="最大节点数")


class RecommendResponse(BaseModel):
    """路径推荐响应"""
    path_id: str
    learner_id: str
    target_level: str
    nodes: List[Dict]
    total_time: int
    processing_time_ms: float


class ExerciseRequest(BaseModel):
    """练习生成请求"""
    concept: str = Field(..., description="概念/知识点")
    exercise_type: str = Field("multiple_choice", description="练习类型")
    difficulty: str = Field("medium", description="难度 (easy/medium/hard)")
    language: str = Field("fr", description="语言")


class ExerciseResponse(BaseModel):
    """练习生成响应"""
    concept: str
    exercise_type: str
    content: str
    answer: Optional[str]
    explanation: str


# ==================== API端点 ====================

@app.on_event("startup")
async def startup_event():
    """应用启动时加载模型"""
    global ontology, kg_reranker, path_recommender
    
    logger.info("Loading models...")
    
    try:
        # 加载配置
        config = load_yaml("config/app.yaml")
        
        # 加载本体（这里简化，实际应从文件加载）
        ontology = FLOOntology()
        logger.info("✓ Loaded ontology")
        
        # 初始化重排序器
        kg_reranker = KGReranker(
            ontology=ontology,
            alpha=config.get("reranking", {}).get("alpha", 0.4),
            beta=config.get("reranking", {}).get("beta", 0.3),
            gamma=config.get("reranking", {}).get("gamma", 0.3)
        )
        logger.info("✓ Initialized KG reranker")
        
        # 初始化路径推荐器
        path_recommender = PathRecommender(ontology=ontology)
        logger.info("✓ Initialized path recommender")
        
        logger.info("All models loaded successfully!")
        
    except Exception as e:
        logger.error(f"Failed to load models: {e}")
        raise


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "KG-CLIR French Learning API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "ontology_loaded": ontology is not None,
        "entities": len(ontology.entities) if ontology else 0,
        "relations": len(ontology.relations) if ontology else 0
    }


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    跨语言检索
    
    执行BM25 + Dense + KG联合检索。
    """
    import time
    start_time = time.time()
    
    logger.info(f"Search request: {request.query} ({request.query_language} → {request.target_language})")
    
    if not ontology or not kg_reranker:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    try:
        # 这里简化演示，实际应调用完整的检索流程
        # 1. BM25检索
        # 2. Dense检索
        # 3. KG重排序
        
        # 模拟检索结果
        dummy_results = [
            SearchResult(
                doc_id=f"doc_{i}",
                title=f"Document {i}",
                content=f"Content of document {i}",
                language=request.target_language,
                bm25_score=0.8 - i * 0.05,
                dense_score=0.75 - i * 0.04,
                kg_score=0.7 - i * 0.03
            )
            for i in range(request.top_k)
        ]
        
        if request.use_kg:
            # 应用KG重排序
            reranked_results = kg_reranker.rerank(
                query=request.query,
                query_language=request.query_language,
                results=dummy_results,
                top_k=request.top_k
            )
        else:
            reranked_results = dummy_results
        
        # 转换为响应格式
        results_dict = [
            {
                "doc_id": r.doc_id,
                "title": r.title,
                "content": r.content[:200] + "...",
                "language": r.language,
                "score": r.final_score,
                "scores_breakdown": {
                    "bm25": r.bm25_score,
                    "dense": r.dense_score,
                    "kg": r.kg_score
                }
            }
            for r in reranked_results
        ]
        
        processing_time = (time.time() - start_time) * 1000
        
        return SearchResponse(
            results=results_dict,
            total=len(results_dict),
            query=request.query,
            processing_time_ms=processing_time
        )
    
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recommend", response_model=RecommendResponse)
async def recommend_path(request: RecommendRequest):
    """
    学习路径推荐
    
    基于学习者当前水平和目标，生成个性化学习路径。
    """
    import time
    start_time = time.time()
    
    logger.info(f"Recommend request: learner={request.learner_id}, {request.current_level} → {request.target_level}")
    
    if not path_recommender:
        raise HTTPException(status_code=503, detail="Path recommender not loaded")
    
    try:
        # 创建学习者模型
        learner = LearnerModel(
            learner_id=request.learner_id,
            current_level=request.current_level
        )
        
        # 生成路径
        path = path_recommender.recommend_path(
            learner=learner,
            target_level=request.target_level,
            max_nodes=request.max_nodes
        )
        
        # 转换为响应格式
        nodes_dict = [
            {
                "entity_id": node.entity_id,
                "name": node.entity_name,
                "type": node.entity_type.value,
                "difficulty": node.difficulty,
                "estimated_time": node.estimated_time,
                "prerequisites": node.prerequisites
            }
            for node in path.nodes
        ]
        
        processing_time = (time.time() - start_time) * 1000
        
        return RecommendResponse(
            path_id=path.path_id,
            learner_id=path.learner_id,
            target_level=path.target_level,
            nodes=nodes_dict,
            total_time=path.total_time,
            processing_time_ms=processing_time
        )
    
    except Exception as e:
        logger.error(f"Recommend error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/exercise", response_model=ExerciseResponse)
async def generate_exercise(request: ExerciseRequest):
    """
    生成练习题
    
    使用RAG方法从KG中检索相关知识，生成个性化练习。
    """
    logger.info(f"Exercise request: concept={request.concept}, type={request.exercise_type}")
    
    try:
        # 这里简化演示，实际应调用RAG模块
        # 1. 从KG检索相关知识
        # 2. 构建prompt
        # 3. 调用LLM生成
        
        # 模拟生成结果
        content = f"根据概念 '{request.concept}' 生成的 {request.exercise_type} 练习题。"
        answer = "答案示例"
        explanation = f"这道题目考察了 {request.concept} 的核心概念，难度为 {request.difficulty}。"
        
        return ExerciseResponse(
            concept=request.concept,
            exercise_type=request.exercise_type,
            content=content,
            answer=answer,
            explanation=explanation
        )
    
    except Exception as e:
        logger.error(f"Exercise generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 主函数 ====================

def main():
    """启动服务"""
    import argparse
    
    parser = argparse.ArgumentParser(description="KG-CLIR API Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    uvicorn.run(
        "src.app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()
