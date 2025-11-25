#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Knowledge Graph Query Expansion
知识图谱查询扩展

Core Idea:
利用知识图谱中的结构化知识扩展查询：
1. 识别查询中的实体
2. 通过KG关系查找相关实体和概念
3. 为扩展词计算权重（基于关系类型和距离）
4. 生成扩展查询或对检索结果进行重排序

Academic References:
- Xiong et al. (2017). Explicit Semantic Ranking for Academic Search via 
  Knowledge Graph Embedding. WWW.
- Query expansion using knowledge graphs is a proven technique in IR
"""

import os
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional
from collections import defaultdict, deque
import numpy as np

from ..utils.logger import logger
from ..utils.io import save_json
from ..kg.ontology import FLOOntology, RelationType


class KGQueryExpander:
    """
    基于知识图谱的查询扩展器

    Args:
        ontology: FLO知识图谱
        max_hops: 最大跳数（n-hop邻居）
        relation_weights: 关系类型权重字典

    Examples:
        >>> expander = KGQueryExpander(ontology, max_hops=2)
        >>> expanded_entities = expander.expand_query("subjonctif français")
        >>> # {"虚拟式": 1.0, "条件式": 0.8, "语法": 0.6, ...}
    """

    def __init__(
        self,
        ontology: FLOOntology,
        max_hops: int = 2,
        relation_weights: Optional[Dict[str, float]] = None,
        decay_factor: float = 0.8
    ):
        self.ontology = ontology
        self.max_hops = max_hops
        self.decay_factor = decay_factor

        # 关系类型权重（根据语义相关性）
        if relation_weights is None:
            self.relation_weights = {
                RelationType.SAME_AS.value: 1.0,         # 等价关系（最高权重）
                RelationType.TRANSLATED_AS.value: 0.9,   # 翻译关系
                RelationType.BELONGS_TO.value: 0.7,      # 所属关系
                RelationType.SUPPORTS.value: 0.6,        # 支持关系
                RelationType.HAS_PREREQ.value: 0.5,      # 前置关系
                RelationType.TESTS.value: 0.4,           # 测试关系
                RelationType.COVERS.value: 0.6           # 覆盖关系
            }
        else:
            self.relation_weights = relation_weights

        # 建立(source, target, relation_type) -> confidence 的快速索引
        self._rel_conf: Dict[Tuple[str, str, str], float] = {}
        for rel in self.ontology.relations:
            self._rel_conf[(rel.source_id, rel.target_id, rel.relation_type.value)] = rel.confidence

        logger.info(f"KGQueryExpander initialized (max_hops={max_hops}, decay={decay_factor})")

    def extract_entities_from_query(
        self,
        query: str,
        languages: Optional[List[str]] = None
    ) -> List[str]:
        """
        从查询中提取KG实体

        Args:
            query: 查询文本
            languages: 目标语言列表（None表示所有语言）

        Returns:
            匹配的实体ID列表

        Strategy:
            1. 精确匹配实体名称
            2. 部分匹配（子串匹配）
            3. 考虑别名和同义词
        """
        query_lower = query.lower()
        matched_entities = []

        for entity_id, entity in self.ontology.entities.items():
            # 语言过滤
            if languages and entity.language not in languages:
                continue

            # 精确匹配
            if entity.name.lower() == query_lower:
                matched_entities.append(entity_id)
                continue

            # 部分匹配（实体名称是查询的子串或反之）
            if entity.name.lower() in query_lower or query_lower in entity.name.lower():
                matched_entities.append(entity_id)
                continue

            # 别名匹配
            if hasattr(entity, 'aliases') and entity.aliases:
                for alias in entity.aliases:
                    if alias.lower() in query_lower or query_lower in alias.lower():
                        matched_entities.append(entity_id)
                        break

        logger.info(f"Extracted {len(matched_entities)} entities from query: {query}")
        return matched_entities

    def get_related_entities(
        self,
        entity_id: str,
        max_hops: Optional[int] = None
    ) -> Dict[str, float]:
        """
        获取实体的n-hop相关实体

        Args:
            entity_id: 源实体ID
            max_hops: 最大跳数（None表示使用self.max_hops）

        Returns:
            {related_entity_id: relevance_score} 相关实体字典
            relevance_score ∈ [0, 1]，距离越远权重越低
        """
        if max_hops is None:
            max_hops = self.max_hops

        related_entities: Dict[str, float] = {}
        visited: Set[str] = set()
        queue = deque([(entity_id, 0, 1.0)])  # (entity_id, hop_distance, cumulative_weight)

        while queue:
            current_id, hop, weight = queue.popleft()

            if hop > max_hops:
                continue

            if current_id in visited:
                continue

            visited.add(current_id)

            # 记录相关实体（不包括源实体本身）
            if current_id != entity_id:
                # 如果已有更高权重，保留更高的
                if current_id not in related_entities or weight > related_entities[current_id]:
                    related_entities[current_id] = weight

            # 通过邻接表获取邻居 (neighbor_id, relation_type)
            for neighbor_id, rel_type in self.ontology.adjacency_list.get(current_id, []):
                if neighbor_id in visited:
                    continue

                # 关系类型权重
                relation_weight = self.relation_weights.get(rel_type.value, 0.3)

                # 关系置信度（若未记录，默认为1.0）
                conf = self._rel_conf.get((current_id, neighbor_id, rel_type.value), 1.0)

                # 路径长度衰减（decay_factor^distance）
                new_weight = weight * relation_weight * conf * (self.decay_factor ** (hop + 1))

                queue.append((neighbor_id, hop + 1, new_weight))

        logger.debug(f"Found {len(related_entities)} related entities for {entity_id} (max_hops={max_hops})")
        return related_entities

    def expand_query(
        self,
        query: str,
        top_k: int = 10,
        min_weight: float = 0.1,
        query_languages: Optional[List[str]] = None
    ) -> Dict[str, float]:
        """
        扩展查询

        Args:
            query: 原始查询
            top_k: 返回前k个扩展实体
            min_weight: 最小权重阈值
            query_languages: 查询实体的语言

        Returns:
            {entity_name: relevance_weight} 扩展实体字典
        """
        logger.info(f"Expanding query: {query}")

        # 提取查询实体
        query_entities = self.extract_entities_from_query(query, languages=query_languages)

        if len(query_entities) == 0:
            logger.warning(f"No entities found in query: {query}")
            return {}

        # 收集所有相关实体
        all_related = defaultdict(float)

        for entity_id in query_entities:
            related = self.get_related_entities(entity_id)
            for rel_id, weight in related.items():
                # 累加权重（多个查询实体可能指向同一个相关实体）
                all_related[rel_id] += weight

        # 转换为实体名称
        expanded_terms = {}
        for entity_id, weight in all_related.items():
            entity = self.ontology.entities.get(entity_id)
            if entity and weight >= min_weight:
                expanded_terms[entity.name] = weight

        # 归一化权重
        if expanded_terms:
            max_weight = max(expanded_terms.values())
            expanded_terms = {k: v / max_weight for k, v in expanded_terms.items()}

        # 返回top-k
        sorted_terms = sorted(expanded_terms.items(), key=lambda x: x[1], reverse=True)[:top_k]
        result = dict(sorted_terms)

        logger.info(f"Expanded query with {len(result)} terms")
        return result

    def score_document_with_kg(
        self,
        doc_text: str,
        query: str,
        query_languages: Optional[List[str]] = None
    ) -> float:
        """
        使用KG为文档计算额外的相关性分数

        Args:
            doc_text: 文档文本
            query: 查询文本
            query_languages: 查询实体的语言

        Returns:
            KG-based relevance score ∈ [0, 1]

        Strategy:
            1. 提取查询实体
            2. 提取文档实体
            3. 计算查询实体到文档实体的KG距离
            4. 基于距离和关系类型计算分数
        """
        # 提取查询实体
        query_entities = self.extract_entities_from_query(query, languages=query_languages)

        if len(query_entities) == 0:
            return 0.0

        # 提取文档实体
        doc_entities = self.extract_entities_from_query(doc_text)

        if len(doc_entities) == 0:
            return 0.0

        # 计算查询实体到文档实体的平均相关性
        total_score = 0.0
        count = 0

        for q_entity in query_entities:
            related = self.get_related_entities(q_entity, max_hops=self.max_hops)

            for d_entity in doc_entities:
                if d_entity == q_entity:
                    # 精确匹配
                    total_score += 1.0
                    count += 1
                elif d_entity in related:
                    # 通过KG关联
                    total_score += related[d_entity]
                    count += 1

        if count == 0:
            return 0.0

        avg_score = total_score / count
        return min(avg_score, 1.0)

    def batch_score_documents(
        self,
        documents: List[str],
        query: str,
        query_languages: Optional[List[str]] = None
    ) -> List[float]:
        """
        批量为文档计算KG分数

        Args:
            documents: 文档列表
            query: 查询文本
            query_languages: 查询实体的语言

        Returns:
            KG分数列表
        """
        logger.info(f"Batch scoring {len(documents)} documents with KG")

        scores = []
        for doc in documents:
            score = self.score_document_with_kg(doc, query, query_languages)
            scores.append(score)

        return scores

    def get_statistics(self) -> Dict:
        """
        获取扩展器统计信息

        Returns:
            统计信息字典
        """
        return {
            "max_hops": self.max_hops,
            "relation_weights": self.relation_weights,
            "decay_factor": self.decay_factor,
            "num_entities": len(self.ontology.entities),
            "num_relations": len(self.ontology.relations)
        }

    # ========== 可解释性：查找KG路径 ==========
    def _find_shortest_path(self, src_id: str, tgt_id: str, max_hops: Optional[int] = None) -> Optional[List[Tuple[str, str]]]:
        """
        使用BFS查找最短路径（返回[(entity_id, relation_type), ...]，不含起点关系类型）
        """
        if max_hops is None:
            max_hops = self.max_hops

        if src_id == tgt_id:
            return [(src_id, "self")]  # 退化路径

        visited: Set[str] = set([src_id])
        queue = deque([(src_id, [])])  # current_id, path_edges

        while queue:
            cur, path = queue.popleft()
            if len(path) > max_hops:
                continue

            for nb_id, rel_type in self.ontology.adjacency_list.get(cur, []):
                if nb_id in visited:
                    continue
                visited.add(nb_id)

                new_path = path + [(nb_id, rel_type.value)]
                if nb_id == tgt_id:
                    return new_path
                queue.append((nb_id, new_path))

        return None

    def explain_paths_between_texts(
        self,
        query_text: str,
        doc_text: str,
        query_languages: Optional[List[str]] = None,
        max_paths: int = 3
    ) -> List[Dict[str, any]]:
        """
        返回查询实体与文档实体之间的知识路径解释

        Returns: [{"query_entity": name, "doc_entity": name, "path": ["A -(rel)-> B", ...]}]
        """
        q_entities = self.extract_entities_from_query(query_text, languages=query_languages)
        d_entities = self.extract_entities_from_query(doc_text)

        explanations: List[Dict[str, any]] = []
        if not q_entities or not d_entities:
            return explanations

        for qid in q_entities:
            for did in d_entities:
                path = self._find_shortest_path(qid, did)
                if not path:
                    continue

                # 构建可读路径
                readable = []
                cur = qid
                for nid, rel in path:
                    src_name = self.ontology.entities[cur].name
                    tgt_name = self.ontology.entities[nid].name
                    readable.append(f"{src_name} -({rel})-> {tgt_name}")
                    cur = nid

                explanations.append({
                    "query_entity": self.ontology.entities[qid].name,
                    "doc_entity": self.ontology.entities[did].name,
                    "path": readable
                })

                if len(explanations) >= max_paths:
                    return explanations

        return explanations


def expand_queries_from_file(
    queries_file: str,
    ontology: FLOOntology,
    output_dir: str,
    config: Dict
):
    """
    批量扩展查询（从文件）

    Args:
        queries_file: 查询文件路径（JSONL格式）
        ontology: FLO知识图谱
        output_dir: 输出目录
        config: 配置字典

    Expected JSONL format:
        {"query_id": "q1", "text": "grammaire française"}
    """
    from ..utils.io import load_jsonl

    logger.info(f"Expanding queries from file: {queries_file}")

    # 加载查询
    queries = load_jsonl(queries_file)
    logger.info(f"Loaded {len(queries)} queries")

    # 初始化扩展器
    kg_config = config.get("kg_expansion", {})
    expander = KGQueryExpander(
        ontology=ontology,
        max_hops=kg_config.get("max_hops", 2),
        relation_weights=kg_config.get("relation_weights", None),
        decay_factor=kg_config.get("expansion_strategy", {}).get("decay_factor", 0.8)
    )

    # 扩展查询
    expanded_queries = []
    for query_data in queries:
        query_id = query_data.get("query_id")
        query_text = query_data.get("text", "")

        expanded_terms = expander.expand_query(
            query=query_text,
            top_k=kg_config.get("top_k", 10),
            min_weight=kg_config.get("min_weight", 0.1)
        )

        expanded_queries.append({
            "query_id": query_id,
            "original_query": query_text,
            "expanded_terms": expanded_terms
        })

    # 保存结果
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_file = os.path.join(output_dir, "expanded_queries.json")
    save_json(expanded_queries, output_file)

    logger.info(f"Expanded queries saved to {output_file}")
    return expanded_queries


def main():
    """主函数：命令行查询扩展"""
    import argparse
    from ..utils.io import load_yaml
    from ..kg.ontology import FLOOntology

    parser = argparse.ArgumentParser(description="Expand queries using Knowledge Graph")
    parser.add_argument("--queries", type=str, required=True, help="Queries JSONL file")
    parser.add_argument("--kg", type=str, required=True, help="Knowledge graph JSON file")
    parser.add_argument("--config", type=str, default="config/retrieval.yaml", help="Config file")
    parser.add_argument("--output", type=str, default="outputs/retrieval/kg_expansion", help="Output directory")

    args = parser.parse_args()

    # 加载配置
    config = load_yaml(args.config)

    # 加载知识图谱
    logger.info(f"Loading knowledge graph from {args.kg}")
    ontology = FLOOntology.from_json(args.kg)
    logger.info(f"Loaded KG: {len(ontology.entities)} entities, {len(ontology.relations)} relations")

    # 扩展查询
    expand_queries_from_file(
        queries_file=args.queries,
        ontology=ontology,
        output_dir=args.output,
        config=config
    )

    logger.info("Query expansion completed")


if __name__ == "__main__":
    main()
