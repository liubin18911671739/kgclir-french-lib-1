#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
KG-Enhanced Reranking Module
基于知识图谱增强的重排序

实现论文核心贡献：α·Dense + β·BM25 + γ·KG 联合排序

学术参考：
- Xiong et al. (2017). Explicit Semantic Ranking for Academic Search via Knowledge Graph Embedding. WWW.
- Dalton et al. (2014). Entity Query Feature Expansion using Knowledge Base Links. SIGIR.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

from ..utils.logger import logger
from ..kg.ontology import FLOOntology


@dataclass
class SearchResult:
    """搜索结果"""
    doc_id: str
    title: str
    content: str
    language: str
    bm25_score: float = 0.0
    dense_score: float = 0.0
    kg_score: float = 0.0
    final_score: float = 0.0
    entities: List[str] = None
    
    def __post_init__(self):
        if self.entities is None:
            self.entities = []


class KGReranker:
    """
    KG增强重排序器
    
    核心思想：
    1. 提取查询和文档中的实体
    2. 通过KG扩展相关实体
    3. 计算实体覆盖度和语义相关性
    4. 融合BM25、Dense、KG三种信号
    """
    
    def __init__(
        self,
        ontology: FLOOntology,
        alpha: float = 0.4,  # Dense权重
        beta: float = 0.3,   # BM25权重
        gamma: float = 0.3,  # KG权重
        max_hops: int = 2,
        entity_weight_decay: float = 0.8
    ):
        """
        初始化重排序器
        
        Args:
            ontology: FLO本体
            alpha: 密集检索得分权重
            beta: BM25得分权重
            gamma: KG得分权重
            max_hops: KG扩展最大跳数
            entity_weight_decay: 扩展实体权重衰减
        """
        self.ontology = ontology
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.max_hops = max_hops
        self.entity_weight_decay = entity_weight_decay
        
        # 归一化权重
        total = alpha + beta + gamma
        self.alpha /= total
        self.beta /= total
        self.gamma /= total
        
        logger.info(f"Initialized KGReranker with weights: α={self.alpha:.2f}, β={self.beta:.2f}, γ={self.gamma:.2f}")
    
    def extract_entities_from_text(self, text: str, language: str) -> List[str]:
        """
        从文本中提取实体（简化版，实际应调用NER）
        
        Args:
            text: 文本
            language: 语言
        
        Returns:
            实体名称列表
        """
        # 这里简化处理，实际应调用EntityExtractor
        # 通过匹配本体中的实体名称
        entities = []
        text_lower = text.lower()
        
        for entity_id, entity in self.ontology.entities.items():
            if entity.language == language:
                if entity.name.lower() in text_lower:
                    entities.append(entity.name)
        
        return entities
    
    def expand_entities(
        self,
        seed_entities: List[str],
        max_hops: int = 2
    ) -> Dict[str, float]:
        """
        通过KG扩展实体
        
        Args:
            seed_entities: 种子实体
            max_hops: 最大跳数
        
        Returns:
            扩展实体及其权重 {entity_name: weight}
        """
        entity_weights = {}
        
        # 初始化种子实体
        for entity in seed_entities:
            entity_weights[entity] = 1.0
        
        # 多跳扩展
        current_entities = set(seed_entities)
        
        for hop in range(max_hops):
            next_entities = set()
            weight = self.entity_weight_decay ** (hop + 1)
            
            for entity_name in current_entities:
                # 通过名称解析实体ID
                src_id = self.ontology.entity_index["name"].get(entity_name.lower())
                if not src_id:
                    continue
                # 查找一跳邻居（返回Entity对象）
                neighbors = self.ontology.get_neighbors(src_id, max_hops=1)
                for neighbor in neighbors:
                    neighbor_name = neighbor.name
                        
                        # 更新权重（取最大值）
                    if neighbor_name not in entity_weights:
                            entity_weights[neighbor_name] = weight
                            next_entities.add(neighbor_name)
                    else:
                            entity_weights[neighbor_name] = max(
                                entity_weights[neighbor_name],
                                weight
                            )
            
            current_entities = next_entities
            
            if not current_entities:
                break
        
        return entity_weights
    
    def compute_kg_score(
        self,
        query_entities: Dict[str, float],
        doc_entities: Dict[str, float]
    ) -> float:
        """
        计算KG相关性得分
        
        Args:
            query_entities: 查询实体及权重
            doc_entities: 文档实体及权重
        
        Returns:
            KG得分
        """
        if not query_entities or not doc_entities:
            return 0.0
        
        # 计算加权Jaccard相似度
        intersection_weight = 0.0
        union_weight = 0.0
        
        all_entities = set(query_entities.keys()) | set(doc_entities.keys())
        
        for entity in all_entities:
            q_weight = query_entities.get(entity, 0.0)
            d_weight = doc_entities.get(entity, 0.0)
            
            intersection_weight += min(q_weight, d_weight)
            union_weight += max(q_weight, d_weight)
        
        if union_weight == 0:
            return 0.0
        
        return intersection_weight / union_weight
    
    def rerank(
        self,
        query: str,
        query_language: str,
        results: List[SearchResult],
        top_k: Optional[int] = None
    ) -> List[SearchResult]:
        """
        重排序搜索结果
        
        Args:
            query: 查询文本
            query_language: 查询语言
            results: 初始搜索结果
            top_k: 返回top-k结果
        
        Returns:
            重排序后的结果
        """
        logger.info(f"Reranking {len(results)} results with KG enhancement...")
        
        # 1. 提取查询实体
        query_seed_entities = self.extract_entities_from_text(query, query_language)
        logger.info(f"  Extracted {len(query_seed_entities)} entities from query")
        
        # 2. 扩展查询实体
        query_entities = self.expand_entities(query_seed_entities, self.max_hops)
        logger.info(f"  Expanded to {len(query_entities)} entities")
        
        # 3. 处理每个文档
        for result in results:
            # 提取文档实体
            if not result.entities:
                result.entities = self.extract_entities_from_text(
                    result.content,
                    result.language
                )
            
            # 扩展文档实体
            doc_entities = self.expand_entities(result.entities, max_hops=1)
            
            # 计算KG得分
            result.kg_score = self.compute_kg_score(query_entities, doc_entities)
            
            # 归一化得分（假设bm25_score和dense_score已归一化）
            result.final_score = (
                self.alpha * result.dense_score +
                self.beta * result.bm25_score +
                self.gamma * result.kg_score
            )
        
        # 4. 排序
        results.sort(key=lambda x: x.final_score, reverse=True)
        
        if top_k:
            results = results[:top_k]
        
        logger.info(f"Reranking completed, returning top {len(results)} results")
        
        return results
    
    def explain_ranking(self, result: SearchResult) -> str:
        """
        解释排序结果
        
        Args:
            result: 搜索结果
        
        Returns:
            解释文本
        """
        explanation = f"Document: {result.doc_id}\n"
        explanation += f"  Final Score: {result.final_score:.4f}\n"
        explanation += f"    - Dense: {result.dense_score:.4f} (α={self.alpha:.2f})\n"
        explanation += f"    - BM25: {result.bm25_score:.4f} (β={self.beta:.2f})\n"
        explanation += f"    - KG: {result.kg_score:.4f} (γ={self.gamma:.2f})\n"
        explanation += f"  Entities: {', '.join(result.entities[:5])}"
        
        if len(result.entities) > 5:
            explanation += f" ... ({len(result.entities)} total)"
        
        return explanation


def normalize_scores(results: List[SearchResult], score_field: str = "bm25_score") -> None:
    """
    归一化得分到 [0, 1]
    
    Args:
        results: 搜索结果列表
        score_field: 要归一化的得分字段
    """
    scores = [getattr(r, score_field) for r in results]
    
    if not scores:
        return
    
    min_score = min(scores)
    max_score = max(scores)
    
    if max_score == min_score:
        # 所有得分相同
        for result in results:
            setattr(result, score_field, 1.0)
    else:
        for result in results:
            old_score = getattr(result, score_field)
            new_score = (old_score - min_score) / (max_score - min_score)
            setattr(result, score_field, new_score)
