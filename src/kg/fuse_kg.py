#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Knowledge Fusion Module
知识融合模块

功能：
1. 实体去重（基于名称相似度 + 类型匹配）
2. 关系去重（基于三元组相似度）
3. 冲突解决（基于置信度投票）

学术参考：
- Dong et al. (2014). Knowledge Vault: A Web-Scale Approach to Probabilistic Knowledge Fusion. KDD.
- Shen et al. (2015). Entity Linking with a Knowledge Base: Issues, Techniques, and Solutions. TKDE.
"""

from typing import List, Dict, Tuple, Set
from collections import defaultdict
import numpy as np

from ..utils.logger import logger
from .ontology import FLOOntology, EntityType, RelationType


def compute_string_similarity(s1: str, s2: str) -> float:
    """
    计算字符串相似度（Levenshtein距离归一化）
    
    Args:
        s1: 字符串1
        s2: 字符串2
    
    Returns:
        相似度 [0, 1]
    """
    # Levenshtein距离
    if s1 == s2:
        return 1.0
    
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0
    
    # DP矩阵
    dp = np.zeros((len1 + 1, len2 + 1))
    
    for i in range(len1 + 1):
        dp[i][0] = i
    for j in range(len2 + 1):
        dp[0][j] = j
    
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(
                    dp[i - 1][j] + 1,      # 删除
                    dp[i][j - 1] + 1,      # 插入
                    dp[i - 1][j - 1] + 1   # 替换
                )
    
    distance = dp[len1][len2]
    max_len = max(len1, len2)
    
    return 1.0 - (distance / max_len)


def find_duplicate_entities(
    ontology: FLOOntology,
    similarity_threshold: float = 0.85,
    same_type_only: bool = True
) -> List[Tuple[str, str, float]]:
    """
    查找重复实体
    
    Args:
        ontology: FLO本体
        similarity_threshold: 相似度阈值
        same_type_only: 是否仅匹配相同类型
    
    Returns:
        重复实体对列表 [(id1, id2, similarity), ...]
    """
    logger.info("Finding duplicate entities...")
    
    duplicates = []
    entity_ids = list(ontology.entities.keys())
    
    for i in range(len(entity_ids)):
        for j in range(i + 1, len(entity_ids)):
            id1, id2 = entity_ids[i], entity_ids[j]
            entity1 = ontology.entities[id1]
            entity2 = ontology.entities[id2]
            
            # 类型检查
            if same_type_only and entity1.entity_type != entity2.entity_type:
                continue
            
            # 计算名称相似度
            sim = compute_string_similarity(
                entity1.name.lower(),
                entity2.name.lower()
            )
            
            if sim >= similarity_threshold:
                duplicates.append((id1, id2, sim))
    
    logger.info(f"Found {len(duplicates)} duplicate entity pairs")
    return duplicates


def merge_duplicate_entities(
    ontology: FLOOntology,
    duplicates: List[Tuple[str, str, float]],
    strategy: str = "confidence"
) -> Dict[str, str]:
    """
    合并重复实体
    
    Args:
        ontology: FLO本体
        duplicates: 重复实体对
        strategy: 合并策略 (confidence/random/first)
    
    Returns:
        实体ID映射 {old_id -> new_id}
    """
    logger.info(f"Merging {len(duplicates)} duplicate entities using strategy: {strategy}")
    
    # 构建连通分量（Union-Find）
    parent = {}
    
    def find(x):
        if x not in parent:
            parent[x] = x
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    
    # 合并重复实体
    for id1, id2, _ in duplicates:
        union(id1, id2)
    
    # 为每个连通分量选择代表节点
    clusters = defaultdict(list)
    for entity_id in ontology.entities.keys():
        root = find(entity_id)
        clusters[root].append(entity_id)
    
    # 选择每个cluster的代表
    id_mapping = {}
    for root, cluster_ids in clusters.items():
        if len(cluster_ids) == 1:
            continue
        
        # 根据策略选择代表
        if strategy == "confidence":
            # 选择置信度最高的
            representative = max(
                cluster_ids,
                key=lambda eid: ontology.entities[eid].metadata.get("confidence", 0.5)
            )
        elif strategy == "random":
            representative = cluster_ids[0]
        else:  # first
            representative = min(cluster_ids)
        
        # 建立映射
        for entity_id in cluster_ids:
            if entity_id != representative:
                id_mapping[entity_id] = representative
    
    logger.info(f"Merged {len(id_mapping)} entities into {len(clusters) - len(id_mapping)} representatives")
    
    return id_mapping


def apply_entity_mapping(ontology: FLOOntology, id_mapping: Dict[str, str]) -> None:
    """
    应用实体ID映射，更新本体
    
    Args:
        ontology: FLO本体
        id_mapping: ID映射
    """
    if not id_mapping:
        return
    
    logger.info("Applying entity mapping to ontology...")
    
    # 更新关系中的实体ID
    for relation in ontology.relations:
        if relation.source_id in id_mapping:
            relation.source_id = id_mapping[relation.source_id]
        if relation.target_id in id_mapping:
            relation.target_id = id_mapping[relation.target_id]
    
    # 删除被合并的实体
    for old_id in id_mapping.keys():
        if old_id in ontology.entities:
            del ontology.entities[old_id]
    
    logger.info(f"Updated ontology: removed {len(id_mapping)} duplicate entities")


def deduplicate_relations(ontology: FLOOntology) -> int:
    """
    关系去重
    
    删除完全相同的三元组（source, relation_type, target）
    
    Args:
        ontology: FLO本体
    
    Returns:
        删除的关系数量
    """
    logger.info("Deduplicating relations...")
    
    # 收集唯一三元组
    seen_triples = set()
    unique_relations = []
    
    for relation in ontology.relations:
        triple = (
            relation.source_id,
            relation.relation_type.value,
            relation.target_id
        )
        
        if triple not in seen_triples:
            seen_triples.add(triple)
            unique_relations.append(relation)
    
    removed_count = len(ontology.relations) - len(unique_relations)
    ontology.relations = unique_relations
    
    logger.info(f"Removed {removed_count} duplicate relations")
    return removed_count


def resolve_conflicting_relations(
    ontology: FLOOntology,
    conflict_types: List[Tuple[str, str]] = None
) -> int:
    """
    解决冲突关系
    
    某些关系类型互斥，保留置信度高的。
    
    Args:
        ontology: FLO本体
        conflict_types: 冲突关系类型对（默认使用预定义规则）
    
    Returns:
        删除的关系数量
    """
    if conflict_types is None:
        # 默认冲突规则
        conflict_types = [
            ("belongsTo", "sameAs"),  # 从属关系与等价关系冲突
        ]
    
    logger.info(f"Resolving conflicting relations with {len(conflict_types)} conflict rules...")
    
    # 按实体对分组关系
    entity_pair_relations = defaultdict(list)
    for relation in ontology.relations:
        key = (relation.source_id, relation.target_id)
        entity_pair_relations[key].append(relation)
    
    # 检测并解决冲突
    relations_to_remove = set()
    
    for (source, target), relations in entity_pair_relations.items():
        if len(relations) <= 1:
            continue
        
        # 提取关系类型
        rel_types = [r.relation_type.value for r in relations]
        
        # 检查是否有冲突
        for type1, type2 in conflict_types:
            if type1 in rel_types and type2 in rel_types:
                # 找到冲突的关系
                conflicting = [r for r in relations if r.relation_type.value in [type1, type2]]
                
                # 保留置信度最高的
                best_relation = max(conflicting, key=lambda r: r.confidence)
                
                # 删除其他关系
                for r in conflicting:
                    if r != best_relation:
                        relations_to_remove.add(id(r))
    
    # 过滤关系
    original_count = len(ontology.relations)
    ontology.relations = [
        r for r in ontology.relations
        if id(r) not in relations_to_remove
    ]
    
    removed_count = original_count - len(ontology.relations)
    logger.info(f"Resolved {removed_count} conflicting relations")
    
    return removed_count


def fuse_knowledge_graph(
    ontology: FLOOntology,
    entity_similarity_threshold: float = 0.85,
    merge_strategy: str = "confidence"
) -> Dict[str, int]:
    """
    完整的知识融合流程
    
    Args:
        ontology: FLO本体
        entity_similarity_threshold: 实体相似度阈值
        merge_strategy: 实体合并策略
    
    Returns:
        融合统计信息
    """
    logger.info("=" * 60)
    logger.info("Starting Knowledge Fusion")
    logger.info("=" * 60)
    
    stats = {
        "original_entities": len(ontology.entities),
        "original_relations": len(ontology.relations),
        "merged_entities": 0,
        "removed_duplicate_relations": 0,
        "removed_conflicting_relations": 0
    }
    
    # 1. 实体去重
    duplicates = find_duplicate_entities(
        ontology,
        similarity_threshold=entity_similarity_threshold
    )
    
    if duplicates:
        id_mapping = merge_duplicate_entities(
            ontology,
            duplicates,
            strategy=merge_strategy
        )
        apply_entity_mapping(ontology, id_mapping)
        stats["merged_entities"] = len(id_mapping)
    
    # 2. 关系去重
    removed_rels = deduplicate_relations(ontology)
    stats["removed_duplicate_relations"] = removed_rels
    
    # 3. 冲突解决
    removed_conflicts = resolve_conflicting_relations(ontology)
    stats["removed_conflicting_relations"] = removed_conflicts
    
    stats["final_entities"] = len(ontology.entities)
    stats["final_relations"] = len(ontology.relations)
    
    logger.info("=" * 60)
    logger.info("Knowledge Fusion Completed!")
    logger.info("=" * 60)
    logger.info(f"Entities: {stats['original_entities']} → {stats['final_entities']}")
    logger.info(f"  - Merged: {stats['merged_entities']}")
    logger.info(f"Relations: {stats['original_relations']} → {stats['final_relations']}")
    logger.info(f"  - Duplicate removed: {stats['removed_duplicate_relations']}")
    logger.info(f"  - Conflicts resolved: {stats['removed_conflicting_relations']}")
    
    return stats
