#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BM25 Sparse Retrieval for Cross-lingual Information Retrieval
BM25稀疏检索（基于rank-bm25 + ElasticSearch）

BM25 Algorithm:
    Score(D, Q) = Σ(qi ∈ Q) IDF(qi) × (f(qi, D) × (k1 + 1)) / 
                               (f(qi, D) + k1 × (1 - b + b × |D| / avgdl))

where:
- f(qi, D): Term frequency of qi in document D
- |D|: Length of document D
- avgdl: Average document length in the collection
- k1, b: Free parameters (typically k1=1.5, b=0.75)
- IDF(qi): Inverse document frequency

Academic References:
- Robertson & Zaragoza (2009). The Probabilistic Relevance Framework: 
  BM25 and Beyond. Foundations and Trends in Information Retrieval.
- BM25 is the de facto standard for sparse retrieval in IR
"""

import os
import pickle
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import numpy as np

try:
    from rank_bm25 import BM25Okapi
    RANK_BM25_AVAILABLE = True
except ImportError:
    RANK_BM25_AVAILABLE = False

try:
    from elasticsearch import Elasticsearch
    ES_AVAILABLE = True
except ImportError:
    ES_AVAILABLE = False

from ..utils.logger import logger
from ..utils.io import load_jsonl, save_json
from ..utils.text_norm import tokenize_simple, remove_stopwords


class BM25Retriever:
    """
    BM25稀疏检索器（基于rank-bm25库）

    Args:
        k1: BM25参数k1（控制词频饱和度）
        b: BM25参数b（控制文档长度归一化）
        use_stopwords: 是否去除停用词
        language: 主要语言（用于停用词）

    Examples:
        >>> retriever = BM25Retriever(k1=1.5, b=0.75)
        >>> retriever.index_documents(documents, doc_ids)
        >>> results = retriever.search(query="cours de grammaire", top_k=10)
        >>> # [(doc_id, score), ...]
    """

    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        use_stopwords: bool = True,
        language: str = "fr"
    ):
        if not RANK_BM25_AVAILABLE:
            raise ImportError("rank-bm25 not installed. Install with: pip install rank-bm25")

        self.k1 = k1
        self.b = b
        self.use_stopwords = use_stopwords
        self.language = language

        self.bm25 = None
        self.doc_ids = []
        self.tokenized_corpus = []
        self.id_to_text = {}

        logger.info(f"BM25Retriever initialized (k1={k1}, b={b}, use_stopwords={use_stopwords})")

    def _preprocess(self, text: str) -> List[str]:
        """
        文本预处理（分词 + 停用词过滤）

        Args:
            text: 输入文本

        Returns:
            分词后的token列表
        """
        # 分词
        tokens = tokenize_simple(text, language=self.language)

        # 去除停用词
        if self.use_stopwords:
            tokens = remove_stopwords(tokens, language=self.language)

        return tokens

    def build_index(
        self,
        documents: List[str],
        doc_ids: List[str]
    ):
        """
        构建BM25索引

        Args:
            documents: 文档文本列表
            doc_ids: 文档ID列表

        Raises:
            ValueError: 如果documents和doc_ids长度不匹配
        """
        if len(documents) != len(doc_ids):
            raise ValueError(f"Length mismatch: {len(documents)} documents vs {len(doc_ids)} doc_ids")

        logger.info(f"Building BM25 index for {len(documents)} documents")

        # 分词
        self.tokenized_corpus = [self._preprocess(doc) for doc in documents]
        self.doc_ids = doc_ids
        self.id_to_text = {doc_id: text for doc_id, text in zip(doc_ids, documents)}

        # 构建BM25索引
        self.bm25 = BM25Okapi(self.tokenized_corpus, k1=self.k1, b=self.b)

        logger.info(f"BM25 index built: {len(self.doc_ids)} documents indexed")

    def search(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        检索相似文档

        Args:
            query: 查询文本
            top_k: 返回前k个结果

        Returns:
            [(doc_id, score), ...] 按BM25分数降序排列

        Raises:
            ValueError: 如果索引未构建
        """
        if self.bm25 is None:
            raise ValueError("Index not built. Call build_index() first.")

        # 分词查询
        tokenized_query = self._preprocess(query)

        if len(tokenized_query) == 0:
            logger.warning(f"Empty query after preprocessing: {query}")
            return []

        # 计算BM25分数
        scores = self.bm25.get_scores(tokenized_query)

        # 获取top-k结果
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            doc_id = self.doc_ids[idx]
            score = float(scores[idx])
            if score > 0:  # 只返回有正分数的结果
                results.append((doc_id, score))

        return results

    def batch_search(
        self,
        queries: List[str],
        top_k: int = 10
    ) -> List[List[Tuple[str, float]]]:
        """
        批量检索

        Args:
            queries: 查询列表
            top_k: 每个查询返回前k个结果

        Returns:
            [[(doc_id, score), ...], ...] 每个查询的检索结果
        """
        if self.bm25 is None:
            raise ValueError("Index not built. Call build_index() first.")

        logger.info(f"Batch searching {len(queries)} queries")

        all_results = []
        for query in queries:
            results = self.search(query, top_k=top_k)
            all_results.append(results)

        return all_results

    def save(self, save_dir: str):
        """
        保存索引和元数据

        Args:
            save_dir: 保存目录路径
        """
        if self.bm25 is None:
            raise ValueError("Index not built. Call build_index() first.")

        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)

        # 保存BM25索引（包含IDF和文档长度信息）
        index_data = {
            "k1": self.k1,
            "b": self.b,
            "use_stopwords": self.use_stopwords,
            "language": self.language,
            "doc_ids": self.doc_ids,
            "tokenized_corpus": self.tokenized_corpus,
            "id_to_text": self.id_to_text,
            "bm25_idf": self.bm25.idf,
            "bm25_doc_len": self.bm25.doc_len,
            "bm25_avgdl": self.bm25.avgdl
        }

        with open(save_path / "bm25_index.pkl", "wb") as f:
            pickle.dump(index_data, f)

        logger.info(f"BM25 index saved to {save_dir}")

    def load(self, load_dir: str):
        """
        加载索引和元数据

        Args:
            load_dir: 加载目录路径
        """
        load_path = Path(load_dir)

        index_file = load_path / "bm25_index.pkl"
        if not index_file.exists():
            raise FileNotFoundError(f"Index file not found: {index_file}")

        with open(index_file, "rb") as f:
            index_data = pickle.load(f)

        self.k1 = index_data["k1"]
        self.b = index_data["b"]
        self.use_stopwords = index_data["use_stopwords"]
        self.language = index_data["language"]
        self.doc_ids = index_data["doc_ids"]
        self.tokenized_corpus = index_data["tokenized_corpus"]
        self.id_to_text = index_data["id_to_text"]

        # 重建BM25对象
        self.bm25 = BM25Okapi(self.tokenized_corpus, k1=self.k1, b=self.b)
        self.bm25.idf = index_data["bm25_idf"]
        self.bm25.doc_len = index_data["bm25_doc_len"]
        self.bm25.avgdl = index_data["bm25_avgdl"]

        logger.info(f"BM25 index loaded from {load_dir} ({len(self.doc_ids)} documents)")

    def get_statistics(self) -> Dict:
        """
        获取索引统计信息

        Returns:
            统计信息字典
        """
        if self.bm25 is None:
            return {"status": "not_built"}

        return {
            "status": "built",
            "k1": self.k1,
            "b": self.b,
            "use_stopwords": self.use_stopwords,
            "language": self.language,
            "num_documents": len(self.doc_ids),
            "avgdl": float(self.bm25.avgdl),
            "vocabulary_size": len(self.bm25.idf)
        }


class ElasticSearchRetriever:
    """
    ElasticSearch BM25检索器（用于大规模场景）

    Args:
        host: ElasticSearch服务器地址
        index_name: 索引名称
        k1: BM25参数k1
        b: BM25参数b

    Examples:
        >>> retriever = ElasticSearchRetriever(host="localhost:9200", index_name="french_corpus")
        >>> retriever.index_documents(documents, doc_ids)
        >>> results = retriever.search(query="grammaire française", top_k=10)
    """

    def __init__(
        self,
        host: str = "localhost:9200",
        index_name: str = "corpus",
        k1: float = 1.5,
        b: float = 0.75
    ):
        if not ES_AVAILABLE:
            raise ImportError("elasticsearch not installed. Install with: pip install elasticsearch")

        self.host = host
        self.index_name = index_name
        self.k1 = k1
        self.b = b

        try:
            self.es = Elasticsearch([host])
            logger.info(f"ElasticSearch connected: {host}")
        except Exception as e:
            logger.error(f"Failed to connect to ElasticSearch: {e}")
            raise

    def build_index(
        self,
        documents: List[str],
        doc_ids: List[str],
        batch_size: int = 1000
    ):
        """
        构建ElasticSearch索引

        Args:
            documents: 文档文本列表
            doc_ids: 文档ID列表
            batch_size: 批处理大小
        """
        if len(documents) != len(doc_ids):
            raise ValueError(f"Length mismatch: {len(documents)} documents vs {len(doc_ids)} doc_ids")

        logger.info(f"Building ElasticSearch index: {self.index_name}")

        # 创建索引（配置BM25参数）
        index_settings = {
            "settings": {
                "index": {
                    "similarity": {
                        "default": {
                            "type": "BM25",
                            "k1": self.k1,
                            "b": self.b
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "text": {"type": "text"},
                    "doc_id": {"type": "keyword"}
                }
            }
        }

        # 删除已存在的索引
        if self.es.indices.exists(index=self.index_name):
            self.es.indices.delete(index=self.index_name)

        self.es.indices.create(index=self.index_name, body=index_settings)

        # 批量索引文档
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_ids = doc_ids[i:i + batch_size]

            bulk_data = []
            for doc_id, text in zip(batch_ids, batch_docs):
                bulk_data.append({"index": {"_index": self.index_name, "_id": doc_id}})
                bulk_data.append({"text": text, "doc_id": doc_id})

            self.es.bulk(body=bulk_data, refresh=True)

        logger.info(f"ElasticSearch index built: {len(documents)} documents")

    def search(
        self,
        query: str,
        top_k: int = 10
    ) -> List[Tuple[str, float]]:
        """
        检索相似文档

        Args:
            query: 查询文本
            top_k: 返回前k个结果

        Returns:
            [(doc_id, score), ...] 按BM25分数降序排列
        """
        search_body = {
            "query": {
                "match": {
                    "text": query
                }
            },
            "size": top_k
        }

        response = self.es.search(index=self.index_name, body=search_body)

        results = []
        for hit in response["hits"]["hits"]:
            doc_id = hit["_source"]["doc_id"]
            score = float(hit["_score"])
            results.append((doc_id, score))

        return results

    def get_statistics(self) -> Dict:
        """获取索引统计信息"""
        stats = self.es.indices.stats(index=self.index_name)
        return {
            "status": "built",
            "index_name": self.index_name,
            "num_documents": stats["indices"][self.index_name]["total"]["docs"]["count"],
            "size_bytes": stats["indices"][self.index_name]["total"]["store"]["size_in_bytes"]
        }


def build_bm25_index_from_corpus(
    corpus_path: str,
    output_dir: str,
    config: Dict,
    use_elasticsearch: bool = False
):
    """
    从语料库构建BM25索引

    Args:
        corpus_path: 语料库文件路径（JSONL格式）
        output_dir: 输出目录
        config: 配置字典
        use_elasticsearch: 是否使用ElasticSearch

    Expected JSONL format:
        {"doc_id": "doc_001", "text": "Le français est une langue romane."}
    """
    logger.info(f"Building BM25 index from corpus: {corpus_path}")

    # 加载语料库
    corpus = load_jsonl(corpus_path)
    logger.info(f"Loaded {len(corpus)} documents")

    # 提取文档和ID
    documents = [doc.get("text", "") for doc in corpus]
    doc_ids = [doc.get("doc_id", f"doc_{i}") for i, doc in enumerate(corpus)]

    bm25_config = config.get("bm25", {})

    if use_elasticsearch and ES_AVAILABLE:
        # 使用ElasticSearch
        retriever = ElasticSearchRetriever(
            host=bm25_config.get("elasticsearch", {}).get("host", "localhost:9200"),
            index_name=bm25_config.get("elasticsearch", {}).get("index_name", "corpus"),
            k1=bm25_config.get("k1", 1.5),
            b=bm25_config.get("b", 0.75)
        )
        retriever.build_index(documents, doc_ids)
    else:
        # 使用rank-bm25
        retriever = BM25Retriever(
            k1=bm25_config.get("k1", 1.5),
            b=bm25_config.get("b", 0.75),
            use_stopwords=bm25_config.get("use_stopwords", True),
            language=bm25_config.get("language", "fr")
        )
        retriever.build_index(documents, doc_ids)
        retriever.save(output_dir)

    # 保存统计信息
    stats = retriever.get_statistics()
    save_json(stats, os.path.join(output_dir, "bm25_index_stats.json"))

    logger.info(f"BM25 index built and saved to {output_dir}")
    return retriever


def main():
    """主函数：命令行构建索引"""
    import argparse
    from ..utils.io import load_yaml

    parser = argparse.ArgumentParser(description="Build BM25 index for CLIR")
    parser.add_argument("--corpus", type=str, required=True, help="Corpus JSONL file")
    parser.add_argument("--config", type=str, default="config/retrieval.yaml", help="Config file")
    parser.add_argument("--output", type=str, default="outputs/retrieval/bm25_index", help="Output directory")
    parser.add_argument("--elasticsearch", action="store_true", help="Use ElasticSearch")

    args = parser.parse_args()

    # 加载配置
    config = load_yaml(args.config)

    # 构建索引
    build_bm25_index_from_corpus(
        corpus_path=args.corpus,
        output_dir=args.output,
        config=config,
        use_elasticsearch=args.elasticsearch
    )

    logger.info("BM25 index construction completed")


if __name__ == "__main__":
    main()
