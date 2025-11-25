#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Learning Feedback Loop
学习反馈闭环

功能:
- 答题记录存储（SQLite）
- 实时反馈生成（基于正确性与证据）
- 自适应难度调整（基于最近准确率）
- 掌握度更新（结合 LearnerModel）
- 推荐策略调整（连接 PathRecommender）
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ..utils.logger import logger
from .learner_model import LearnerModel, LearnerDB
from .path_recommend import PathRecommender
from ..kg.ontology import FLOOntology


class FeedbackLoop:
    """学习反馈闭环"""

    def __init__(self, ontology: FLOOntology, db: Optional[LearnerDB] = None):
        self.ontology = ontology
        self.db = db or LearnerDB()
        self.recommender = PathRecommender(ontology)

    def record_answer(
        self,
        learner: LearnerModel,
        concept_id: str,
        question_id: str,
        correct: bool,
        difficulty: float,
        response_time: float,
    ) -> float:
        """
        记录答题并更新掌握度，返回新掌握度
        """
        mastery = learner.update_progress(
            concept_id=concept_id,
            success=bool(correct),
            question_id=question_id,
            difficulty=difficulty,
            response_time=response_time,
        )
        return mastery

    def generate_feedback(
        self,
        learner: LearnerModel,
        concept_id: str,
        correct: bool,
        evidence: Optional[List[str]] = None,
    ) -> str:
        """
        生成即时反馈（简短文本）
        """
        mastery = learner.compute_mastery(concept_id)
        concept_name = self.ontology.entities.get(concept_id).name if concept_id in self.ontology.entities else concept_id
        if correct:
            base = f"✅ 正确！你在『{concept_name}』的当前掌握度为 {mastery:.2f}。"
            tip = "继续保持，可以尝试更高难度。" if mastery > learner.mastery_threshold else "再巩固2-3题可达掌握阈值。"
            return f"{base} {tip}"
        else:
            ref = "；参考证据：" + " | ".join(evidence[:2]) if evidence else ""
            return f"❌ 不正确。建议复习『{concept_name}』的关键点{ref}。"

    def adjust_difficulty(self, learner: LearnerModel, concept_id: Optional[str] = None) -> float:
        """
        自适应难度：根据最近k次准确率调节 [0.2, 0.9]
        """
        acc = learner.concept_accuracy(concept_id, k_recent=10) if concept_id else learner.overall_accuracy(50)
        # 简单线性映射：低准确率→降低难度，高准确率→提升难度
        target = 0.5 + (acc - 0.5) * 0.8
        return min(0.9, max(0.2, target))

    def recommend_next(
        self,
        learner: LearnerModel,
        target_level: str,
        max_nodes: int = 10,
    ) -> Dict:
        """
        推荐下一段学习路径（简要）
        """
        path = self.recommender.recommend_path(learner, target_level=target_level, max_nodes=max_nodes)
        return {
            "path_id": path.path_id,
            "target_level": path.target_level,
            "total_time": path.total_time,
            "nodes": [
                {
                    "entity_id": n.entity_id,
                    "name": n.entity_name,
                    "difficulty": n.difficulty,
                    "estimated_time": n.estimated_time,
                    "prerequisites": n.prerequisites,
                }
                for n in path.nodes
            ],
        }
