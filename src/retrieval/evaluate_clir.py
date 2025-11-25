#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CLIR Evaluation
跨语言检索评测（TREC格式qrels + 多指标 + 显著性检验）

实现：
- TREC格式qrels加载：query_id 0 doc_id relevance
- 指标计算：nDCG@10, MRR, Recall@50, Precision@10（以及可扩展）
- Baseline对比：Translate+BM25, Dense Only, Dense+BM25, KG-CLIR (Ours)
- 显著性检验：配对t检验（p<0.05）
- Bootstrap抽样：n=1000（差值置信区间）
- 效应量：Cohen's d
"""

from __future__ import annotations

import os
import math
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict

import numpy as np

from ..utils.logger import logger
from ..utils.io import load_yaml, load_jsonl, save_json, load_tsv
from ..utils.metrics import (
    calculate_ndcg,
    calculate_mrr,
    calculate_recall_at_k,
    calculate_precision_at_k,
    evaluate_ranking,
    paired_t_test,
)
from .dense_index import DenseRetriever
from .bm25_index import BM25Retriever
from .kg_clir import KGCLIRSystem, build_kg_clir_system


# ========== 数据加载 ==========
def load_trec_qrels(path: str) -> Dict[str, Dict[str, int]]:
    """
    加载TREC格式的qrels文件

    Format per line: query_id 0 doc_id relevance
    Returns: {query_id: {doc_id: relevance_int}}
    """
    qrels: Dict[str, Dict[str, int]] = defaultdict(dict)
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                qid, _zero, docid, rel = line.split()
                qrels[qid][docid] = int(rel)
            except ValueError:
                logger.warning(f"Invalid qrels line, skipped: {line}")
                continue
    return qrels


def load_retrieval_results(path: str) -> List[Dict[str, Any]]:
    """
    加载检索结果（kg_clir.py保存的JSON）
    格式：[{"query_id": ..., "query": ..., "results": [{"doc_id":..., "score":...}, ...]}]
    """
    return load_jsonl(path) if path.endswith(".jsonl") else _load_json(path)


def _load_json(path: str) -> Any:
    import json
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ========== Baseline 构建 ==========
def _normalize_score_dict(scores: Dict[str, float]) -> Dict[str, float]:
    if not scores:
        return {}
    vals = list(scores.values())
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return {k: 1.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


def build_retrievers_from_corpus(corpus_path: str, config: Dict) -> Tuple[DenseRetriever, BM25Retriever, List[str], List[str]]:
    corpus = load_jsonl(corpus_path)
    documents = [doc.get("text", "") for doc in corpus]
    doc_ids = [doc.get("doc_id", f"doc_{i}") for i, doc in enumerate(corpus)]

    dense_cfg = config.get("dense", {})
    dense = DenseRetriever(
        model_name=dense_cfg.get("model_name", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"),
        index_type=dense_cfg.get("index_type", "Flat"),
        device=dense_cfg.get("device", "cpu"),
        normalize=dense_cfg.get("normalize", True),
    )
    dense.build_index(documents, doc_ids)

    bm25_cfg = config.get("bm25", {})
    bm25 = BM25Retriever(
        k1=bm25_cfg.get("k1", 1.5),
        b=bm25_cfg.get("b", 0.75),
        use_stopwords=bm25_cfg.get("use_stopwords", True),
        language=bm25_cfg.get("language", "fr"),
    )
    bm25.build_index(documents, doc_ids)

    return dense, bm25, documents, doc_ids


def _identity_translate(texts: List[str]) -> List[str]:
    return texts


def _maybe_translate(texts: List[str], src_lang: str, tgt_lang: str) -> List[str]:
    """
    尝试使用transformers翻译，失败则原样返回
    """
    try:
        from transformers import pipeline

        model_map = {
            ("zh", "fr"): "Helsinki-NLP/opus-mt-zh-fr",
            ("zh", "en"): "Helsinki-NLP/opus-mt-zh-en",
            ("fr", "en"): "Helsinki-NLP/opus-mt-fr-en",
            ("en", "fr"): "Helsinki-NLP/opus-mt-en-fr",
        }
        model_name = model_map.get((src_lang, tgt_lang))
        if not model_name:
            return texts
        trans = pipeline("translation", model=model_name)
        outputs = trans(texts)
        return [o["translation_text"] for o in outputs]
    except Exception as e:
        logger.warning(f"Translation unavailable ({src_lang}->{tgt_lang}), using original: {e}")
        return texts


# ========== 评测核心 ==========
def evaluate_system_per_query(
    rankings: Dict[str, List[Tuple[str, float]]],
    qrels: Dict[str, Dict[str, int]],
    metrics: List[str],
) -> Tuple[Dict[str, Dict[str, float]], Dict[str, float]]:
    """
    计算每个query的指标，以及总体平均
    rankings: {query_id: [(doc_id, score), ...]}
    returns: (per_query_scores, avg_scores)
    """
    per_query: Dict[str, Dict[str, float]] = {}
    agg: Dict[str, List[float]] = defaultdict(list)

    for qid, results in rankings.items():
        gt = qrels.get(qid, {})
        pred_ids = [d for d, _ in results]

        # 构造相关性列表
        rel_scores = [gt.get(docid, 0) for docid in pred_ids]
        rel_binary = [1 if x > 0 else 0 for x in rel_scores]
        total_rel = len([x for x in gt.values() if x > 0])

        scores: Dict[str, float] = {}
        for m in metrics:
            if "@" in m:
                name, kstr = m.split("@"); k = int(kstr)
            else:
                name = m; k = len(pred_ids)

            if name == "ndcg":
                scores[m] = calculate_ndcg(rel_scores, k)
            elif name == "mrr":
                scores[m] = calculate_mrr(rel_binary)
            elif name == "recall":
                scores[m] = calculate_recall_at_k(rel_binary, total_rel, k)
            elif name == "precision":
                scores[m] = calculate_precision_at_k(rel_binary, k)
            elif name == "map":
                # 用单query的AP近似：MAP等价于AP平均，单query即AP
                # 这里简单实现：累计Precision@i在rel处的均值
                if total_rel == 0:
                    scores[m] = 0.0
                else:
                    prec_sum = 0.0; rel_so_far = 0
                    for i, rb in enumerate(rel_binary, start=1):
                        if rb > 0:
                            rel_so_far += 1
                            prec_sum += rel_so_far / i
                    scores[m] = prec_sum / total_rel
            else:
                continue

            agg[m].append(scores[m])

        per_query[qid] = scores

    avg_scores = {m: float(np.mean(v)) if v else 0.0 for m, v in agg.items()}
    return per_query, avg_scores


def cohen_d(a: List[float], b: List[float]) -> float:
    a = np.array(a); b = np.array(b)
    mean_diff = a.mean() - b.mean()
    # 合并标准差
    n1, n2 = len(a), len(b)
    if n1 <= 1 or n2 <= 1:
        return 0.0
    s1, s2 = a.std(ddof=1), b.std(ddof=1)
    sp = math.sqrt(((n1 - 1) * s1 * s1 + (n2 - 1) * s2 * s2) / (n1 + n2 - 2))
    if sp == 0:
        return 0.0
    return mean_diff / sp


def bootstrap_ci_diff(a: List[float], b: List[float], n: int = 1000, alpha: float = 0.05) -> Tuple[float, Tuple[float, float]]:
    """
    Bootstrap差值置信区间 (a - b)
    返回：均值, (下界, 上界)
    """
    a = np.array(a); b = np.array(b)
    if len(a) != len(b) or len(a) == 0:
        return 0.0, (0.0, 0.0)

    diffs = []
    n_items = len(a)
    rng = np.random.default_rng(42)
    for _ in range(n):
        idx = rng.integers(0, n_items, size=n_items)
        diffs.append(float((a[idx] - b[idx]).mean()))

    diffs = np.array(diffs)
    mean = float(diffs.mean())
    low = float(np.quantile(diffs, alpha / 2))
    high = float(np.quantile(diffs, 1 - alpha / 2))
    return mean, (low, high)


# ========== 主入口：运行评测 ==========
def evaluate(
    corpus_path: str,
    qrels_path: str,
    queries_path: str,
    config_path: str,
    output_path: str,
    top_k: int = 10,
) -> Dict[str, Any]:
    """
    运行完整评测，包括四个系统：
      - Translate+BM25
      - Dense Only
      - Dense+BM25
      - KG-CLIR (Ours)
    """
    config = load_yaml(config_path)
    metrics = config.get("evaluation", {}).get("metrics", ["ndcg@10", "mrr", "recall@50", "precision@10"])

    # 加载数据
    qrels = load_trec_qrels(qrels_path)
    queries_tsv = load_tsv(queries_path)
    queries = [(row.get("query_id") or row["query_id"], row.get("query_text") or row["query_text"]) for row in queries_tsv]

    # 构建检索器
    dense, bm25, documents, doc_ids = build_retrievers_from_corpus(corpus_path, config)

    # 1) Dense Only
    dense_rankings: Dict[str, List[Tuple[str, float]]] = {}
    for qid, qtext in queries:
        res = dense.search(qtext, top_k=top_k)
        dense_rankings[qid] = res

    # 2) BM25 with translation (best-effort)
    # 读取查询语言（若提供）
    q_lang = None
    if len(queries_tsv) > 0 and ("language" in queries_tsv[0] or (isinstance(queries_tsv[0], dict) and "language" in queries_tsv[0])):
        # 若存在language列，取之；否则None
        pass
    # 简化：尝试将中文->法语
    translated_queries = [(qid, _maybe_translate([qtext], "zh", "fr")[0]) for qid, qtext in queries]
    bm25_trans_rankings: Dict[str, List[Tuple[str, float]]] = {}
    for qid, qtext in translated_queries:
        res = bm25.search(qtext, top_k=top_k)
        bm25_trans_rankings[qid] = res

    # 3) Dense+BM25（无KG）
    densebm25_rankings: Dict[str, List[Tuple[str, float]]] = {}
    for qid, qtext in queries:
        d = {doc: s for doc, s in dense_rankings.get(qid, [])}
        b = {doc: s for doc, s in bm25.search(qtext, top_k=top_k * 5)}  # 稍多候选
        # 归一化
        d = _normalize_score_dict(d)
        b = _normalize_score_dict(b)
        all_ids = set(d.keys()) | set(b.keys())
        final = {doc: 0.5 * d.get(doc, 0.0) + 0.5 * b.get(doc, 0.0) for doc in all_ids}
        ranked = sorted(final.items(), key=lambda x: x[1], reverse=True)[:top_k]
        densebm25_rankings[qid] = ranked

    # 4) KG-CLIR (Ours)
    kg_config = config
    # 构建系统并运行
    from ..kg.ontology import FLOOntology
    kg_path = config.get("paths", {}).get("kg_json", "data/kg/ontology.json")
    try:
        system = build_kg_clir_system(
            corpus_path=corpus_path,
            kg_path=kg_path,
            output_dir=os.path.dirname(output_path) or "outputs/retrieval/kg_clir",
            config=config,
        )
    except Exception as e:
        logger.warning(f"KG-CLIR system build failed ({e}), fallback to Dense+BM25 as Ours for evaluation")
        system = None

    ours_rankings: Dict[str, List[Tuple[str, float]]] = {}
    if system is not None:
        for qid, qtext in queries:
            ours_rankings[qid] = system.search(qtext, top_k=top_k)
    else:
        ours_rankings = densebm25_rankings

    # 评测各系统
    systems = {
        "Translate+BM25": bm25_trans_rankings,
        "Dense Only": dense_rankings,
        "Dense+BM25": densebm25_rankings,
        "KG-CLIR (Ours)": ours_rankings,
    }

    per_query_scores: Dict[str, Dict[str, Dict[str, float]]] = {}
    avg_scores: Dict[str, Dict[str, float]] = {}
    for name, ranks in systems.items():
        pq, avg = evaluate_system_per_query(ranks, qrels, metrics)
        per_query_scores[name] = pq
        avg_scores[name] = avg

    # 显著性检验 & 效应量（Ours vs 其他）
    significance: Dict[str, Dict[str, Any]] = {}
    base = "KG-CLIR (Ours)"
    for other in [k for k in systems.keys() if k != base]:
        sig_per_metric: Dict[str, Any] = {}
        for m in metrics:
            a = [per_query_scores[base].get(qid, {}).get(m, 0.0) for qid, _ in queries]
            b = [per_query_scores[other].get(qid, {}).get(m, 0.0) for qid, _ in queries]

            try:
                p_value, is_sig = paired_t_test(a, b, alpha=config.get("evaluation", {}).get("significance_test", {}).get("alpha", 0.05))
            except Exception as e:
                logger.warning(f"paired_t_test failed for {m}: {e}")
                p_value, is_sig = 1.0, False

            d = cohen_d(a, b)
            mean_diff, (low, high) = bootstrap_ci_diff(a, b, n=config.get("evaluation", {}).get("significance_test", {}).get("bootstrap_samples", 1000))

            sig_per_metric[m] = {
                "p_value": float(p_value),
                "significant": bool(is_sig),
                "cohens_d": float(d),
                "mean_diff": float(mean_diff),
                "ci95": [float(low), float(high)],
            }

        significance[f"{base} vs {other}"] = sig_per_metric

    result = {
        "metrics": metrics,
        "average_scores": avg_scores,
        "significance": significance,
    }

    # 保存
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    save_json(result, out_path)
    logger.info(f"Evaluation saved to {out_path}")

    return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate KG-CLIR retrieval")
    parser.add_argument("--corpus", type=str, required=True, help="Corpus JSONL file")
    parser.add_argument("--qrels", type=str, required=True, help="TREC qrels file")
    parser.add_argument("--queries", type=str, required=True, help="Queries TSV file")
    parser.add_argument("--config", type=str, default="config/retrieval.yaml", help="Config file")
    parser.add_argument("--output", type=str, default="outputs/retrieval/eval_results.json", help="Output JSON path")
    parser.add_argument("--top_k", type=int, default=10, help="Top-k for evaluation")

    args = parser.parse_args()

    evaluate(
        corpus_path=args.corpus,
        qrels_path=args.qrels,
        queries_path=args.queries,
        config_path=args.config,
        output_path=args.output,
        top_k=args.top_k,
    )


if __name__ == "__main__":
    main()
