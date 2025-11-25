#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Dense Vector Indexing for Cross-lingual Information Retrieval
密集向量索引（基于Sentence-Transformers + FAISS）

Core Technologies:
1. Sentence-Transformers: Multilingual sentence embeddings
2. FAISS: Fast approximate nearest neighbor search
3. Batch encoding for large corpora

Academic References:
- Reimers & Gurevych (2019). Sentence-BERT: Sentence Embeddings using
  Siamese BERT-Networks. EMNLP.
- Johnson et al. (2019). Billion-scale similarity search with GPUs.
  IEEE Transactions on Big Data.
"""

import os
import pickle
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import numpy as np
from tqdm import tqdm

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

from sentence_transformers import SentenceTransformer

from ..utils.logger import logger
from ..utils.io import load_jsonl, save_json


class DenseRetriever:
    """
    密集向量检索器（基于Sentence-Transformers + FAISS）

    Args:
        model_name: HuggingFace模型名称
        index_type: FAISS索引类型 ("Flat" 或 "IVF256,Flat")
        device: 运行设备 ("cpu" 或 "cuda")
        normalize: 是否L2归一化向量

    Examples:
        >>> retriever = DenseRetriever(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        >>> retriever.index_documents(documents, doc_ids)
        >>> results = retriever.search(query="grammaire française", top_k=10)
        >>> # [(doc_id, score), ...]
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        index_type: str = "Flat",
        device: str = "cpu",
        normalize: bool = True
    ):
        self.model_name = model_name
        self.index_type = index_type
        self.device = device
        self.normalize = normalize

        # 加载Sentence-Transformers模型
        logger.info(f"Loading Sentence-Transformers model: {model_name}")
        self.model = SentenceTransformer(model_name, device=device)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

        # FAISS索引
        self.index = None
        self.doc_ids = []
        self.id_to_text = {}

        # GPU支持
        self._use_gpu = False
        if FAISS_AVAILABLE and device.startswith("cuda"):
            try:
                ngpu = faiss.get_num_gpus()
                if ngpu > 0:
                    self._use_gpu = True
                    logger.info(f"FAISS GPU detected: {ngpu} GPU(s) available")
                else:
                    logger.info("FAISS GPU not available; falling back to CPU")
            except Exception as e:
                logger.warning(f"FAISS GPU detection failed: {e}")
                self._use_gpu = False

        logger.info(f"DenseRetriever initialized (embedding_dim={self.embedding_dim}, device={device})")

    def encode(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = True
    ) -> np.ndarray:
        """
        批量编码文本为向量

        Args:
            texts: 文本列表
            batch_size: 批大小
            show_progress: 是否显示进度条

        Returns:
            向量矩阵 (N × embedding_dim)
        """
        logger.info(f"Encoding {len(texts)} texts with batch_size={batch_size}")

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=self.normalize
        )

        if not self.normalize:
            # 手动L2归一化
            embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        logger.info(f"Encoded embeddings shape: {embeddings.shape}")
        return embeddings

    def build_index(
        self,
        documents: List[str],
        doc_ids: List[str],
        batch_size: int = 32
    ):
        """
        构建FAISS索引

        Args:
            documents: 文档文本列表
            doc_ids: 文档ID列表
            batch_size: 编码批大小

        Raises:
            ValueError: 如果FAISS不可用
            ValueError: 如果documents和doc_ids长度不匹配
        """
        if not FAISS_AVAILABLE:
            raise ValueError("FAISS is not installed. Install with: pip install faiss-cpu or faiss-gpu")

        if len(documents) != len(doc_ids):
            raise ValueError(f"Length mismatch: {len(documents)} documents vs {len(doc_ids)} doc_ids")

        logger.info(f"Building FAISS index for {len(documents)} documents")

        # 编码文档
        embeddings = self.encode(documents, batch_size=batch_size)

        # 创建FAISS索引
        if self.index_type == "Flat":
            # 精确搜索（适合小规模数据）
            cpu_index = faiss.IndexFlatIP(self.embedding_dim)  # 内积（余弦相似度，因为已归一化）
        elif self.index_type.startswith("IVF"):
            # 倒排索引（适合大规模数据）
            nlist = int(self.index_type.split(",")[0].replace("IVF", ""))
            quantizer = faiss.IndexFlatIP(self.embedding_dim)
            cpu_index = faiss.IndexIVFFlat(quantizer, self.embedding_dim, nlist, faiss.METRIC_INNER_PRODUCT)

            # 训练IVF索引
            logger.info(f"Training IVF index with nlist={nlist}")
            cpu_index.train(embeddings)
        else:
            raise ValueError(f"Unsupported index_type: {self.index_type}")

        # 如可用，迁移到GPU
        if self._use_gpu:
            try:
                res = faiss.StandardGpuResources()
                # 使用默认GPU 0；如需要多GPU，可改为index_cpu_to_all_gpus
                self.index = faiss.index_cpu_to_gpu(res, 0, cpu_index)
                logger.info("FAISS index moved to GPU")
            except Exception as e:
                logger.warning(f"Failed to move FAISS index to GPU, fallback to CPU: {e}")
                self.index = cpu_index
        else:
            self.index = cpu_index

        # 添加向量到索引
        self.index.add(embeddings)
        self.doc_ids = doc_ids
        self.id_to_text = {doc_id: text for doc_id, text in zip(doc_ids, documents)}

        logger.info(f"FAISS index built: {self.index.ntotal} vectors indexed")

    def search(
        self,
        query: str,
        top_k: int = 10,
        nprobe: int = 10
    ) -> List[Tuple[str, float]]:
        """
        检索相似文档

        Args:
            query: 查询文本
            top_k: 返回前k个结果
            nprobe: IVF索引的搜索桶数量（仅对IVF索引有效）

        Returns:
            [(doc_id, score), ...] 按相似度降序排列

        Raises:
            ValueError: 如果索引未构建
        """
        if self.index is None:
            raise ValueError("Index not built. Call build_index() first.")

        # 编码查询
        query_embedding = self.encode([query], show_progress=False)

        # 设置IVF搜索参数
        if self.index_type.startswith("IVF"):
            self.index.nprobe = nprobe

        # 搜索
        scores, indices = self.index.search(query_embedding, top_k)

        # 转换结果
        results = []
        for idx, score in zip(indices[0], scores[0]):
            if idx != -1:  # FAISS返回-1表示未找到足够的结果
                doc_id = self.doc_ids[idx]
                results.append((doc_id, float(score)))

        return results

    def batch_search(
        self,
        queries: List[str],
        top_k: int = 10,
        nprobe: int = 10,
        batch_size: int = 32
    ) -> List[List[Tuple[str, float]]]:
        """
        批量检索

        Args:
            queries: 查询列表
            top_k: 每个查询返回前k个结果
            nprobe: IVF索引的搜索桶数量
            batch_size: 编码批大小

        Returns:
            [[(doc_id, score), ...], ...] 每个查询的检索结果
        """
        if self.index is None:
            raise ValueError("Index not built. Call build_index() first.")

        logger.info(f"Batch searching {len(queries)} queries")

        # 编码查询
        query_embeddings = self.encode(queries, batch_size=batch_size)

        # 设置IVF搜索参数
        if self.index_type.startswith("IVF"):
            self.index.nprobe = nprobe

        # 批量搜索
        scores, indices = self.index.search(query_embeddings, top_k)

        # 转换结果
        all_results = []
        for query_scores, query_indices in zip(scores, indices):
            results = []
            for idx, score in zip(query_indices, query_scores):
                if idx != -1:
                    doc_id = self.doc_ids[idx]
                    results.append((doc_id, float(score)))
            all_results.append(results)

        return all_results

    def save(self, save_dir: str):
        """
        保存索引和元数据

        Args:
            save_dir: 保存目录路径
        """
        if self.index is None:
            raise ValueError("Index not built. Call build_index() first.")

        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)

        # 保存FAISS索引（GPU索引需先转回CPU）
        index_file = save_path / "faiss.index"
        index_to_save = self.index
        try:
            # GPU索引类名包含"Gpu"
            if hasattr(self.index, "__class__") and "Gpu" in self.index.__class__.__name__:
                index_to_save = faiss.index_gpu_to_cpu(self.index)
        except Exception as e:
            logger.warning(f"Detect GPU index failed, try saving directly: {e}")
        faiss.write_index(index_to_save, str(index_file))

        # 保存元数据
        metadata = {
            "model_name": self.model_name,
            "index_type": self.index_type,
            "embedding_dim": self.embedding_dim,
            "normalize": self.normalize,
            "doc_ids": self.doc_ids,
            "id_to_text": self.id_to_text,
            "num_documents": len(self.doc_ids)
        }

        with open(save_path / "metadata.pkl", "wb") as f:
            pickle.dump(metadata, f)

        logger.info(f"Index saved to {save_dir}")

    def load(self, load_dir: str):
        """
        加载索引和元数据

        Args:
            load_dir: 加载目录路径
        """
        if not FAISS_AVAILABLE:
            raise ValueError("FAISS is not installed.")

        load_path = Path(load_dir)

        # 加载FAISS索引
        index_file = load_path / "faiss.index"
        if not index_file.exists():
            raise FileNotFoundError(f"Index file not found: {index_file}")

        cpu_index = faiss.read_index(str(index_file))

        # 如可用，迁移到GPU
        if self._use_gpu:
            try:
                res = faiss.StandardGpuResources()
                self.index = faiss.index_cpu_to_gpu(res, 0, cpu_index)
                logger.info("FAISS index moved to GPU after loading")
            except Exception as e:
                logger.warning(f"Failed to move FAISS index to GPU after loading: {e}")
                self.index = cpu_index
        else:
            self.index = cpu_index

        # 加载元数据
        with open(load_path / "metadata.pkl", "rb") as f:
            metadata = pickle.load(f)

        self.model_name = metadata["model_name"]
        self.index_type = metadata["index_type"]
        self.embedding_dim = metadata["embedding_dim"]
        self.normalize = metadata["normalize"]
        self.doc_ids = metadata["doc_ids"]
        self.id_to_text = metadata["id_to_text"]

        logger.info(f"Index loaded from {load_dir} ({len(self.doc_ids)} documents)")

    def get_statistics(self) -> Dict:
        """
        获取索引统计信息

        Returns:
            统计信息字典
        """
        if self.index is None:
            return {"status": "not_built"}

        return {
            "status": "built",
            "model_name": self.model_name,
            "index_type": self.index_type,
            "embedding_dim": self.embedding_dim,
            "num_documents": len(self.doc_ids),
            "normalize": self.normalize,
            "total_vectors": self.index.ntotal
        }


def build_dense_index_from_corpus(
    corpus_path: str,
    output_dir: str,
    config: Dict
):
    """
    从语料库构建密集索引

    Args:
        corpus_path: 语料库文件路径（JSONL格式）
        output_dir: 输出目录
        config: 配置字典

    Expected JSONL format:
        {"doc_id": "doc_001", "text": "Le français est une langue romane."}
    """
    logger.info(f"Building dense index from corpus: {corpus_path}")

    # 加载语料库
    corpus = load_jsonl(corpus_path)
    logger.info(f"Loaded {len(corpus)} documents")

    # 提取文档和ID
    documents = [doc.get("text", "") for doc in corpus]
    doc_ids = [doc.get("doc_id", f"doc_{i}") for i, doc in enumerate(corpus)]

    # 初始化检索器
    dense_config = config.get("dense", {})
    retriever = DenseRetriever(
        model_name=dense_config.get("model_name", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"),
        index_type=dense_config.get("index_type", "Flat"),
        device=dense_config.get("device", "cpu"),
        normalize=dense_config.get("normalize", True)
    )

    # 构建索引
    retriever.build_index(
        documents=documents,
        doc_ids=doc_ids,
        batch_size=dense_config.get("batch_size", 32)
    )

    # 保存索引
    retriever.save(output_dir)

    # 保存统计信息
    stats = retriever.get_statistics()
    save_json(stats, os.path.join(output_dir, "dense_index_stats.json"))

    logger.info(f"Dense index built and saved to {output_dir}")
    return retriever


def main():
    """主函数：命令行构建索引"""
    import argparse
    from ..utils.io import load_yaml

    parser = argparse.ArgumentParser(description="Build dense vector index for CLIR")
    parser.add_argument("--corpus", type=str, required=True, help="Corpus JSONL file")
    parser.add_argument("--config", type=str, default="config/retrieval.yaml", help="Config file")
    parser.add_argument("--output", type=str, default="outputs/retrieval/dense_index", help="Output directory")

    args = parser.parse_args()

    # 加载配置
    config = load_yaml(args.config)

    # 构建索引
    build_dense_index_from_corpus(
        corpus_path=args.corpus,
        output_dir=args.output,
        config=config
    )

    logger.info("Dense index construction completed")


if __name__ == "__main__":
    main()
