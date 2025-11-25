#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Learning Path Recommendation
学习路径推荐

基于知识图谱的个性化学习路径推荐：
1. 根据学习者当前水平
2. 考虑先修关系 (hasPrereq)
3. 生成拓扑排序的学习序列

学术参考：
- Dwivedi & Bharadwaj (2015). E-Learning Recommender System for Learners Using Collaborative Filtering. ICCSNT.
- Klašnja-Milićević et al. (2011). E-Learning personalization based on hybrid recommendation strategy and learning style identification. Computers & Education.
"""

from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque
import numpy as np

from ..utils.logger import logger
from ..kg.ontology import FLOOntology, EntityType, RelationType


@dataclass
class LearningNode:
    """学习节点"""
    entity_id: str
    entity_name: str
    entity_type: EntityType
    difficulty: float = 0.5  # 难度 [0, 1]
    estimated_time: int = 30  # 预计学习时间（分钟）
    prerequisites: List[str] = None  # 先修节点
    
    def __post_init__(self):
        if self.prerequisites is None:
            self.prerequisites = []


@dataclass
class LearningPath:
    """学习路径"""
    path_id: str
    learner_id: str
    target_level: str  # 目标CEFR等级 (A1/A2/B1/B2/C1/C2)
    nodes: List[LearningNode]
    total_time: int = 0  # 总预计时间
    completion_rate: float = 0.0  # 完成率
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        
        # 计算总时间
        self.total_time = sum(node.estimated_time for node in self.nodes)


class LearnerModel:
    """
    学习者模型
    
    跟踪学习者的知识掌握情况和学习偏好。
    
    掌握度计算：M(c) = (n_c / N_c) * w1 + coverage_rate * w2
    """
    
    def __init__(
        self,
        learner_id: str,
        current_level: str = "A1",
        mastery_threshold: float = 0.7
    ):
        self.learner_id = learner_id
        self.current_level = current_level
        self.mastery_threshold = mastery_threshold
        
        # 知识掌握情况
        self.mastered_concepts = set()  # 已掌握的概念
        self.learning_history = []  # 学习历史
        self.concept_attempts = defaultdict(int)  # 概念练习次数
        self.concept_successes = defaultdict(int)  # 概念成功次数
    
    def compute_mastery(self, concept: str) -> float:
        """
        计算概念掌握度
        
        Args:
            concept: 概念ID
        
        Returns:
            掌握度 [0, 1]
        """
        attempts = self.concept_attempts.get(concept, 0)
        successes = self.concept_successes.get(concept, 0)
        
        if attempts == 0:
            return 0.0
        
        # 正确率
        accuracy = successes / attempts
        
        # 练习充分度（至少需要3次）
        coverage_rate = min(attempts / 3.0, 1.0)
        
        # 加权平均
        mastery = accuracy * 0.7 + coverage_rate * 0.3
        
        return mastery
    
    def is_mastered(self, concept: str) -> bool:
        """判断是否掌握某概念"""
        return self.compute_mastery(concept) >= self.mastery_threshold
    
    def update_progress(self, concept: str, success: bool):
        """更新学习进度"""
        self.concept_attempts[concept] += 1
        if success:
            self.concept_successes[concept] += 1
        
        # 更新掌握集合
        if self.is_mastered(concept):
            self.mastered_concepts.add(concept)


class PathRecommender:
    """
    学习路径推荐器
    
    基于KG的拓扑排序生成学习路径。
    """
    
    def __init__(self, ontology: FLOOntology):
        self.ontology = ontology
    
    def recommend_path(
        self,
        learner: LearnerModel,
        target_level: str = "B1",
        max_nodes: int = 20
    ) -> LearningPath:
        """
        推荐学习路径
        
        Args:
            learner: 学习者模型
            target_level: 目标CEFR等级
            max_nodes: 最大节点数
        
        Returns:
            学习路径
        """
        logger.info(f"Recommending learning path for learner {learner.learner_id}")
        logger.info(f"  Current level: {learner.current_level} → Target level: {target_level}")
        
        # 1. 提取目标等级相关的概念
        target_concepts = self._get_concepts_by_level(target_level)
        logger.info(f"  Found {len(target_concepts)} concepts for level {target_level}")
        
        # 2. 过滤已掌握的概念
        unmastered_concepts = [
            c for c in target_concepts
            if c not in learner.mastered_concepts
        ]
        logger.info(f"  {len(unmastered_concepts)} concepts not yet mastered")
        
        # 3. 构建依赖图
        dependency_graph = self._build_dependency_graph(unmastered_concepts)
        
        # 4. 拓扑排序
        sorted_concepts = self._topological_sort(dependency_graph)
        
        # 5. 选择优先级最高的概念
        selected_concepts = sorted_concepts[:max_nodes]
        
        # 6. 构建学习节点
        learning_nodes = []
        for concept_id in selected_concepts:
            entity = self.ontology.entities.get(concept_id)
            if entity:
                node = LearningNode(
                    entity_id=concept_id,
                    entity_name=entity.name,
                    entity_type=entity.entity_type,
                    difficulty=self._estimate_difficulty(concept_id),
                    estimated_time=self._estimate_time(entity.entity_type),
                    prerequisites=self._get_prerequisites(concept_id)
                )
                learning_nodes.append(node)
        
        # 7. 创建学习路径
        path = LearningPath(
            path_id=f"path_{learner.learner_id}_{target_level}",
            learner_id=learner.learner_id,
            target_level=target_level,
            nodes=learning_nodes
        )
        
        logger.info(f"Generated learning path with {len(path.nodes)} nodes, total time: {path.total_time} min")
        
        return path
    
    def _get_concepts_by_level(self, level: str) -> List[str]:
        """获取指定等级的所有概念"""
        concepts = []
        
        # 查找等级实体
        level_entities = [
            eid for eid, e in self.ontology.entities.items()
            if e.entity_type == EntityType.CEFR_SKILL and level in e.name
        ]
        
        # 查找属于该等级的概念（通过belongsTo关系）
        for level_id in level_entities:
            neighbors = self.ontology.get_neighbors(
                entity_id=level_id,
                relation_types=[RelationType.BELONGS_TO],
                direction="incoming"  # 找指向level的关系
            )
            
            for neighbor_id, _, _ in neighbors:
                concepts.append(neighbor_id)
        
        return concepts
    
    def _build_dependency_graph(self, concepts: List[str]) -> Dict[str, List[str]]:
        """构建依赖图"""
        graph = defaultdict(list)
        
        for concept_id in concepts:
            # 查找先修关系
            neighbors = self.ontology.get_neighbors(
                entity_id=concept_id,
                relation_types=[RelationType.HAS_PREREQ],
                max_hops=1
            )
            
            for prereq_id, _, _ in neighbors:
                if prereq_id in concepts:
                    graph[prereq_id].append(concept_id)
        
        return graph
    
    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """
        拓扑排序（Kahn算法）
        
        Args:
            graph: 依赖图 {prereq: [dependent_concepts]}
        
        Returns:
            排序后的概念列表
        """
        # 计算入度
        in_degree = defaultdict(int)
        all_nodes = set(graph.keys())
        
        for node in graph:
            for neighbor in graph[node]:
                in_degree[neighbor] += 1
                all_nodes.add(neighbor)
        
        # 零入度队列
        queue = deque([node for node in all_nodes if in_degree[node] == 0])
        sorted_nodes = []
        
        while queue:
            node = queue.popleft()
            sorted_nodes.append(node)
            
            # 更新邻居入度
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        return sorted_nodes
    
    def _estimate_difficulty(self, concept_id: str) -> float:
        """估计概念难度"""
        entity = self.ontology.entities.get(concept_id)
        
        if not entity:
            return 0.5
        
        # 基于实体类型估计难度
        difficulty_map = {
            EntityType.WORD: 0.3,
            EntityType.GRAMMAR: 0.6,
            EntityType.PRAGMATICS: 0.7,
            EntityType.CULTURE: 0.5,
            EntityType.TOPIC: 0.4
        }
        
        return difficulty_map.get(entity.entity_type, 0.5)
    
    def _estimate_time(self, entity_type: EntityType) -> int:
        """估计学习时间（分钟）"""
        time_map = {
            EntityType.WORD: 10,
            EntityType.GRAMMAR: 30,
            EntityType.PRAGMATICS: 25,
            EntityType.CULTURE: 20,
            EntityType.TOPIC: 15,
            EntityType.EXERCISE: 15,
            EntityType.TASK: 45
        }
        
        return time_map.get(entity_type, 20)
    
    def _get_prerequisites(self, concept_id: str) -> List[str]:
        """获取先修概念"""
        neighbors = self.ontology.get_neighbors(
            entity_id=concept_id,
            relation_types=[RelationType.HAS_PREREQ],
            max_hops=1
        )
        
        return [neighbor_id for neighbor_id, _, _ in neighbors]
