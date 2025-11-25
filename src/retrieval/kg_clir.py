#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Knowledge Graph Enhanced Cross-lingual Information Retrieval
知识图谱增强的跨语言信息检索

Core Contribution:
三路融合排序公式（论文核心贡献）：
    Score(d, q) = α · Dense(d, q) + β · BM25(d, q) + γ · KG(d, q)

where:
- Dense(d, q): 密集向量相似度（Sentence-Transformers）
- BM25(d, q): 稀疏检索分数（BM25算法）
- KG(d, q): 知识图谱相关性（基于实体关系）
- α, β, γ: 融合权重（α + β + γ = 1.0）

Academic References:
- Combining dense and sparse retrieval: Karpukhin et al. (2020). Dense 
  Passage Retrieval for Open-Domain Question Answering. EMNLP.
- KG-enhanced retrieval: Xiong et al. (2017). Explicit Semantic Ranking 
  for Academic Search via Knowledge Graph Embedding. WWW.
"""

import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import numpy as np
from tqdm import tqdm

from ..utils.logger import logger
from ..utils.io import load_jsonl, save_json
from ..kg.ontology import FLOOntology
from .dense_index import DenseRetriever
from .bm25_index import BM25Retriever
from .kg_expansion import KGQueryExpander


class KGCLIRSystem:
    """
    知识图谱增强的跨语言信息检索系统

    Args:
        dense_retriever: 密集向量检索器
        bm25_retriever: BM25稀疏检索器
        kg_expander: 知识图谱查询扩展器
        alpha: 密集向量权重
        beta: BM25权重
        gamma: 知识图谱权重
        normalize_scores: 是否归一化各组件分数

    Examples:
        >>> system = KGCLIRSystem(dense, bm25, kg, alpha=0.4, beta=0.3, gamma=0.3)
        >>> results = system.search(query="grammaire française", top_k=10)
        >>> # [(doc_id, score), ...]
    """

    def __init__(
        self,
        dense_retriever: DenseRetriever,
        bm25_retriever: BM25Retriever,
        kg_expander: KGQueryExpander,
        alpha: float = 0.4,
        beta: float = 0.3,
        gamma: float = 0.3,
        normalize_scores: bool = True
    ):
        self.dense_retriever = dense_retriever
        self.bm25_retriever = bm25_retriever
        self.kg_expander = kg_expander

        # 验证权重和
        weight_sum = alpha + beta + gamma
        if not np.isclose(weight_sum, 1.0, atol=0.01):
            logger.warning(f"Weights sum to {weight_sum:.3f}, normalizing to 1.0")
            self.alpha = alpha / weight_sum
            self.beta = beta / weight_sum
            self.gamma = gamma / weight_sum
        else:
            self.alpha = alpha
            self.beta = beta
            self.gamma = gamma

        self.normalize_scores = normalize_scores

        logger.info(f"KGCLIRSystem initialized (α={self.alpha:.2f}, β={self.beta:.2f}, γ={self.gamma:.2f})")

    def _normalize_scores(self, scores: Dict[str, float]) -> Dict[str, float]:
        """
        归一化分数到[0, 1]

        Args:
            scores: {doc_id: score}

        Returns:
            归一化后的分数字典
        """
        if not scores:
            return {}

        min_score = min(scores.values())
        max_score = max(scores.values())

        if max_score == min_score:
            # 所有分数相同
            return {doc_id: 1.0 for doc_id in scores}

        normalized = {
            doc_id: (score - min_score) / (max_score - min_score)
            for doc_id, score in scores.items()
        }

        return normalized

    def search(
        self,
        query: str,
        top_k: int = 10,
        retrieve_top_n: int = 100,
        query_languages: Optional[List[str]] = None
    ) -> List[Tuple[str, float]]:
        """
        三路融合检索

        Args:
            query: 查询文本
            top_k: 返回前k个结果
            retrieve_top_n: 各检索器初步检索的top-n（用于重排序）
            query_languages: 查询实体的语言

        Returns:
            [(doc_id, final_score), ...] 按最终分数降序排列

        Process:
            1. 各检索器独立检索top-n候选
            2. 合并候选集（union）
            3. 归一化各检索器分数
            4. 加权融合: final_score = α·dense + β·bm25 + γ·kg
            5. 返回top-k结果
        """
        logger.info(f"Searching: {query}")

        # Step 1: 密集向量检索
        dense_results = self.dense_retriever.search(query, top_k=retrieve_top_n)
        dense_scores = {doc_id: score for doc_id, score in dense_results}

        # Step 2: BM25稀疏检索
        bm25_results = self.bm25_retriever.search(query, top_k=retrieve_top_n)
        bm25_scores = {doc_id: score for doc_id, score in bm25_results}

        # Step 3: 合并候选文档集
        all_doc_ids = set(dense_scores.keys()) | set(bm25_scores.keys())
        logger.info(f"Retrieved {len(all_doc_ids)} candidate documents")

        # Step 4: 为候选文档计算KG分数
        kg_scores = {}
        for doc_id in all_doc_ids:
            # 获取文档文本
            doc_text = self.dense_retriever.id_to_text.get(doc_id, "") or \
                      self.bm25_retriever.id_to_text.get(doc_id, "")

            if doc_text:
                kg_score = self.kg_expander.score_document_with_kg(doc_text, query, query_languages)
                kg_scores[doc_id] = kg_score

        # Step 5: 归一化分数
        if self.normalize_scores:
            dense_scores = self._normalize_scores(dense_scores)
            bm25_scores = self._normalize_scores(bm25_scores)
            kg_scores = self._normalize_scores(kg_scores)

        # Step 6: 加权融合
        final_scores = {}
        for doc_id in all_doc_ids:
            score = (
                self.alpha * dense_scores.get(doc_id, 0.0) +
                self.beta * bm25_scores.get(doc_id, 0.0) +
                self.gamma * kg_scores.get(doc_id, 0.0)
            )
            final_scores[doc_id] = score

        # Step 7: 排序并返回top-k
        sorted_results = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        logger.info(f"Returned {len(sorted_results)} results")
        return sorted_results

    def batch_search(
        self,
        queries: List[str],
        top_k: int = 10,
        retrieve_top_n: int = 100,
        query_languages: Optional[List[str]] = None
    ) -> List[List[Tuple[str, float]]]:
        """
        批量检索

        Args:
            queries: 查询列表
            top_k: 每个查询返回前k个结果
            retrieve_top_n: 各检索器初步检索的top-n
            query_languages: 查询实体的语言

        Returns:
            [[(doc_id, score), ...], ...] 每个查询的检索结果
        """
        logger.info(f"Batch searching {len(queries)} queries")

        all_results = []
        for query in tqdm(queries, desc="Batch Search"):
            results = self.search(query, top_k=top_k, retrieve_top_n=retrieve_top_n, query_languages=query_languages)
            all_results.append(results)

        return all_results

    def explain_ranking(
        self,
        query: str,
        doc_id: str,
        query_languages: Optional[List[str]] = None
    ) -> Dict:
        """
        解释单个文档的排序分数

        Args:
            query: 查询文本
            doc_id: 文档ID
            query_languages: 查询实体的语言

        Returns:
            分数分解字典 {
                "dense_score": 0.85,
                "bm25_score": 0.72,
                "kg_score": 0.63,
                "final_score": 0.74,
                "weights": {"alpha": 0.4, "beta": 0.3, "gamma": 0.3}
            }
        """
        # 获取文档文本
        doc_text = self.dense_retriever.id_to_text.get(doc_id, "") or \
                  self.bm25_retriever.id_to_text.get(doc_id, "")

        if not doc_text:
            logger.warning(f"Document not found: {doc_id}")
            return {}

        # 计算各组件分数
        dense_results = self.dense_retriever.search(query, top_k=100)
        dense_score = next((score for did, score in dense_results if did == doc_id), 0.0)

        bm25_results = self.bm25_retriever.search(query, top_k=100)
        bm25_score = next((score for did, score in bm25_results if did == doc_id), 0.0)

        kg_score = self.kg_expander.score_document_with_kg(doc_text, query, query_languages)

        # 归一化
        if self.normalize_scores:
            dense_score = min(dense_score, 1.0)
            bm25_score = min(bm25_score, 1.0)
            kg_score = min(kg_score, 1.0)

        # 最终分数
        final_score = (
            self.alpha * dense_score +
            self.beta * bm25_score +
            self.gamma * kg_score
        )

        # KG路径解释（可选）
        kg_paths = self.kg_expander.explain_paths_between_texts(
            query_text=query,
            doc_text=doc_text,
            query_languages=query_languages,
            max_paths=3
        )

        return {
            "doc_id": doc_id,
            "query": query,
            "dense_score": float(dense_score),
            "bm25_score": float(bm25_score),
            "kg_score": float(kg_score),
            "final_score": float(final_score),
            "weights": {
                "alpha": self.alpha,
                "beta": self.beta,
                "gamma": self.gamma
            },
            "normalized": self.normalize_scores,
            "kg_paths": kg_paths
        }

    def get_statistics(self) -> Dict:
        """
        获取系统统计信息

        Returns:
            统计信息字典
        """
        return {
            "weights": {
                "alpha": self.alpha,
                "beta": self.beta,
                "gamma": self.gamma
            },
            "normalize_scores": self.normalize_scores,
            "dense_retriever": self.dense_retriever.get_statistics(),
            "bm25_retriever": self.bm25_retriever.get_statistics(),
            "kg_expander": self.kg_expander.get_statistics()
        }


def build_kg_clir_system(
    corpus_path: str,
    kg_path: str,
    output_dir: str,
    config: Dict
) -> KGCLIRSystem:
    """
    构建完整的KG-CLIR系统

    Args:
        corpus_path: 语料库文件路径（JSONL格式）
        kg_path: 知识图谱文件路径（JSON格式）
        output_dir: 输出目录
        config: 配置字典

    Returns:
        KGCLIRSystem实例
    """
    logger.info("Building KG-CLIR system")

    # 加载语料库
    corpus = load_jsonl(corpus_path)
    documents = [doc.get("text", "") for doc in corpus]
    doc_ids = [doc.get("doc_id", f"doc_{i}") for i, doc in enumerate(corpus)]

    # 加载知识图谱
    logger.info(f"Loading knowledge graph from {kg_path}")
    ontology = FLOOntology.from_json(kg_path)

    # 构建密集索引
    logger.info("Building dense index...")
    dense_config = config.get("dense", {})
    dense_retriever = DenseRetriever(
        model_name=dense_config.get("model_name", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"),
        index_type=dense_config.get("index_type", "Flat"),
        device=dense_config.get("device", "cpu")
    )
    dense_retriever.build_index(documents, doc_ids)

    # 构建BM25索引
    logger.info("Building BM25 index...")
    bm25_config = config.get("bm25", {})
    bm25_retriever = BM25Retriever(
        k1=bm25_config.get("k1", 1.5),
        b=bm25_config.get("b", 0.75),
        use_stopwords=bm25_config.get("use_stopwords", True)
    )
    bm25_retriever.build_index(documents, doc_ids)

    # 初始化KG扩展器
    logger.info("Initializing KG expander...")
    kg_config = config.get("kg_expansion", {})
    kg_expander = KGQueryExpander(
        ontology=ontology,
        max_hops=kg_config.get("max_hops", 2),
        relation_weights=kg_config.get("relation_weights", None),
        decay_factor=kg_config.get("expansion_strategy", {}).get("decay_factor", 0.8)
    )

    # 创建系统
    reranking_config = config.get("reranking", {})
    system = KGCLIRSystem(
        dense_retriever=dense_retriever,
        bm25_retriever=bm25_retriever,
        kg_expander=kg_expander,
        alpha=reranking_config.get("weights", {}).get("alpha", 0.4),
        beta=reranking_config.get("weights", {}).get("beta", 0.3),
        gamma=reranking_config.get("weights", {}).get("gamma", 0.3),
        normalize_scores=reranking_config.get("normalize_scores", True)
    )

    # 保存统计信息
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    stats = system.get_statistics()
    save_json(stats, os.path.join(output_dir, "kg_clir_stats.json"))

    logger.info("KG-CLIR system built successfully")
    return system


def main():
    """主函数：命令行运行检索系统"""
    import argparse
    from ..utils.io import load_yaml

    parser = argparse.ArgumentParser(description="Run KG-enhanced CLIR system")
    parser.add_argument("--corpus", type=str, required=True, help="Corpus JSONL file")
    parser.add_argument("--kg", type=str, required=True, help="Knowledge graph JSON file")
    parser.add_argument("--queries", type=str, required=True, help="Queries JSONL file")
    parser.add_argument("--config", type=str, default="config/retrieval.yaml", help="Config file")
    parser.add_argument("--output", type=str, default="outputs/retrieval/kg_clir", help="Output directory")
    parser.add_argument("--top_k", type=int, default=10, help="Top-k results per query")

    args = parser.parse_args()

    # 加载配置
    config = load_yaml(args.config)

    # 构建系统
    system = build_kg_clir_system(
        corpus_path=args.corpus,
        kg_path=args.kg,
        output_dir=args.output,
        config=config
    )

    # 加载查询
    queries = load_jsonl(args.queries)
    logger.info(f"Loaded {len(queries)} queries")

    # 批量检索
    query_texts = [q.get("text", "") for q in queries]
    results = system.batch_search(query_texts, top_k=args.top_k)

    # 保存结果
    output_data = []
    for i, query_data in enumerate(queries):
        query_id = query_data.get("query_id", f"q{i}")
        output_data.append({
            "query_id": query_id,
            "query": query_data.get("text", ""),
            "results": [{"doc_id": doc_id, "score": score} for doc_id, score in results[i]]
        })

    output_file = os.path.join(args.output, "retrieval_results.json")
    save_json(output_data, output_file)

    logger.info(f"Retrieval results saved to {output_file}")


if __name__ == "__main__":
    main()
