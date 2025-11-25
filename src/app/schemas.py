#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Pydantic Schemas for API
Pydantic数据模型
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field


# ========== Search ==========

class QueryRequest(BaseModel):
    """跨语言检索请求"""
    query: str = Field(..., description="查询文本")
    language: str = Field("zh", description="查询语言 (zh/fr/en)")
    top_k: int = Field(10, ge=1, le=100, description="返回Top-K")
    use_kg: bool = Field(True, description="是否使用KG增强")


class SearchResultItem(BaseModel):
    doc_id: str
    title: Optional[str] = None
    snippet: Optional[str] = None
    language: Optional[str] = None
    score: float = 0.0
    scores_breakdown: Optional[Dict[str, float]] = None


class SearchResponse(BaseModel):
    results: List[SearchResultItem]
    total: int
    query: str
    query_expansion: Optional[List[str]] = None
    processing_time_ms: float


# ========== Exercise (RAG) ==========

class ExerciseRequest(BaseModel):
    concept: str = Field(..., description="概念/知识点")
    user_level: str = Field("A1", description="学习者水平 (A1-C2)")
    num_questions: int = Field(5, ge=1, le=20, description="题目数量")


class ExerciseQA(BaseModel):
    id: str
    type: str
    question: str
    options: Optional[List[str]] = None
    answer: Optional[str] = None
    explanation: Optional[str] = None
    evidence_refs: Optional[List[int]] = None


class ExerciseResponse(BaseModel):
    concept: str
    user_level: str
    exercises: List[ExerciseQA]


# ========== Learning Path ==========

class LearningPathRequest(BaseModel):
    user_id: str = Field(..., description="学习者ID")
    target_level: str = Field("B1", description="目标CEFR等级 (A1-C2)")
    max_nodes: int = Field(20, ge=5, le=100)
    # 兼容TODO中提及的target_concept（可选，不一定使用）
    target_concept: Optional[str] = None


class PathNode(BaseModel):
    entity_id: str
    name: str
    difficulty: float
    estimated_time: int
    prerequisites: Optional[List[str]] = None


class LearningPathResponse(BaseModel):
    user_id: str
    target_level: str
    path_nodes: List[PathNode]
    path_edges: List[List[str]]  # [[src_id, dst_id], ...]
    total_time: int
    processing_time_ms: float
