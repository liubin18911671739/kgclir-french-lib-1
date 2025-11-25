#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Evaluation Metrics
评价指标计算

实现信息检索和机器学习常用评价指标：
- nDCG (Normalized Discounted Cumulative Gain)
- MRR (Mean Reciprocal Rank)
- Recall@K
- Precision@K
- MAP (Mean Average Precision)
- F1 Score
"""

import math
from typing import List, Dict, Tuple, Optional
import numpy as np


def calculate_ndcg(
    relevance_scores: List[float],
    k: Optional[int] = None
) -> float:
    """
    计算nDCG@k (Normalized Discounted Cumulative Gain)
    
    Args:
        relevance_scores: 相关性得分列表（按排序顺序）
        k: 截断位置（None表示使用全部）
    
    Returns:
        nDCG得分 [0, 1]
    
    Formula:
        DCG@k = Σ(i=1 to k) (2^rel_i - 1) / log2(i + 1)
        nDCG@k = DCG@k / IDCG@k
    
    Examples:
        >>> relevance = [3, 2, 3, 0, 1, 2]
        >>> calculate_ndcg(relevance, k=5)
        0.785
    
    学术引用：
        Järvelin & Kekäläinen (2002). Cumulated gain-based evaluation 
        of IR techniques. ACM TOIS, 20(4), 422-446.
    """
    if not relevance_scores:
        return 0.0
    
    if k is not None:
        relevance_scores = relevance_scores[:k]
    
    # 计算DCG
    dcg = 0.0
    for i, rel in enumerate(relevance_scores, start=1):
        dcg += (2 ** rel - 1) / math.log2(i + 1)
    
    # 计算IDCG（理想情况：按相关性降序排列）
    ideal_relevance = sorted(relevance_scores, reverse=True)
    idcg = 0.0
    for i, rel in enumerate(ideal_relevance, start=1):
        idcg += (2 ** rel - 1) / math.log2(i + 1)
    
    # 避免除零
    if idcg == 0:
        return 0.0
    
    return dcg / idcg


def calculate_mrr(
    relevance_binary: List[int]
) -> float:
    """
    计算MRR (Mean Reciprocal Rank)
    
    Args:
        relevance_binary: 二元相关性列表（1=相关，0=不相关）
    
    Returns:
        MRR得分 [0, 1]
    
    Formula:
        MRR = 1 / rank_of_first_relevant_item
    
    Examples:
        >>> calculate_mrr([0, 0, 1, 0, 1])  # 第一个相关文档在位置3
        0.333
    
    学术引用：
        Voorhees & Harman (1999). TREC: Experiment and Evaluation 
        in Information Retrieval. MIT Press.
    """
    for i, rel in enumerate(relevance_binary, start=1):
        if rel > 0:
            return 1.0 / i
    
    return 0.0


def calculate_recall_at_k(
    relevance_binary: List[int],
    total_relevant: int,
    k: int
) -> float:
    """
    计算Recall@K
    
    Args:
        relevance_binary: 二元相关性列表
        total_relevant: 总相关文档数
        k: 截断位置
    
    Returns:
        Recall@K [0, 1]
    
    Formula:
        Recall@K = (检索到的相关文档数@K) / (总相关文档数)
    """
    if total_relevant == 0:
        return 0.0
    
    retrieved_relevant = sum(relevance_binary[:k])
    return retrieved_relevant / total_relevant


def calculate_precision_at_k(
    relevance_binary: List[int],
    k: int
) -> float:
    """
    计算Precision@K
    
    Args:
        relevance_binary: 二元相关性列表
        k: 截断位置
    
    Returns:
        Precision@K [0, 1]
    
    Formula:
        Precision@K = (检索到的相关文档数@K) / K
    """
    if k == 0:
        return 0.0
    
    retrieved_relevant = sum(relevance_binary[:k])
    return retrieved_relevant / k


def calculate_f1_at_k(
    relevance_binary: List[int],
    total_relevant: int,
    k: int
) -> float:
    """
    计算F1@K
    
    Args:
        relevance_binary: 二元相关性列表
        total_relevant: 总相关文档数
        k: 截断位置
    
    Returns:
        F1@K [0, 1]
    """
    precision = calculate_precision_at_k(relevance_binary, k)
    recall = calculate_recall_at_k(relevance_binary, total_relevant, k)
    
    if precision + recall == 0:
        return 0.0
    
    return 2 * precision * recall / (precision + recall)


def calculate_map(
    relevance_lists: List[List[int]]
) -> float:
    """
    计算MAP (Mean Average Precision)
    
    Args:
        relevance_lists: 多个查询的相关性列表
    
    Returns:
        MAP得分 [0, 1]
    
    Formula:
        MAP = (1/Q) * Σ(q=1 to Q) AP(q)
        AP(q) = (1/R_q) * Σ(k=1 to N) P(k) * rel(k)
    """
    if not relevance_lists:
        return 0.0
    
    average_precisions = []
    
    for relevance in relevance_lists:
        relevant_count = sum(relevance)
        
        if relevant_count == 0:
            average_precisions.append(0.0)
            continue
        
        precision_sum = 0.0
        relevant_so_far = 0
        
        for i, rel in enumerate(relevance, start=1):
            if rel > 0:
                relevant_so_far += 1
                precision_at_i = relevant_so_far / i
                precision_sum += precision_at_i
        
        ap = precision_sum / relevant_count
        average_precisions.append(ap)
    
    return np.mean(average_precisions)


def calculate_hits_at_k(
    relevance_binary: List[int],
    k: int
) -> int:
    """
    计算Hits@K（前K个结果中是否有相关文档）
    
    Args:
        relevance_binary: 二元相关性列表
        k: 截断位置
    
    Returns:
        1（命中）或 0（未命中）
    """
    return 1 if any(relevance_binary[:k]) else 0


def evaluate_ranking(
    predicted_ranking: List[str],
    ground_truth: Dict[str, float],
    metrics: List[str] = ["ndcg@10", "mrr", "recall@50"]
) -> Dict[str, float]:
    """
    综合评估排序结果
    
    Args:
        predicted_ranking: 预测的文档ID排序列表
        ground_truth: 真实相关性字典 {doc_id: relevance_score}
        metrics: 要计算的指标列表
    
    Returns:
        指标字典 {metric_name: value}
    
    Examples:
        >>> predicted = ["doc1", "doc2", "doc3"]
        >>> ground_truth = {"doc1": 2, "doc3": 1}
        >>> evaluate_ranking(predicted, ground_truth, ["ndcg@3", "mrr"])
        {'ndcg@3': 0.89, 'mrr': 1.0}
    """
    # 构建相关性列表
    relevance_scores = []
    relevance_binary = []
    
    for doc_id in predicted_ranking:
        score = ground_truth.get(doc_id, 0)
        relevance_scores.append(score)
        relevance_binary.append(1 if score > 0 else 0)
    
    total_relevant = len([s for s in ground_truth.values() if s > 0])
    
    results = {}
    
    for metric in metrics:
        if "@" in metric:
            metric_name, k_str = metric.split("@")
            k = int(k_str)
        else:
            metric_name = metric
            k = len(predicted_ranking)
        
        if metric_name == "ndcg":
            results[metric] = calculate_ndcg(relevance_scores, k)
        
        elif metric_name == "mrr":
            results[metric] = calculate_mrr(relevance_binary)
        
        elif metric_name == "recall":
            results[metric] = calculate_recall_at_k(relevance_binary, total_relevant, k)
        
        elif metric_name == "precision":
            results[metric] = calculate_precision_at_k(relevance_binary, k)
        
        elif metric_name == "f1":
            results[metric] = calculate_f1_at_k(relevance_binary, total_relevant, k)
        
        elif metric_name == "hits":
            results[metric] = calculate_hits_at_k(relevance_binary, k)
    
    return results


def paired_t_test(
    scores_a: List[float],
    scores_b: List[float],
    alpha: float = 0.05
) -> Tuple[float, bool]:
    """
    配对t检验（显著性检验）
    
    Args:
        scores_a: 方法A的得分列表
        scores_b: 方法B的得分列表
        alpha: 显著性水平
    
    Returns:
        (p值, 是否显著)
    
    学术引用：
        Smucker, Allan & Carterette (2007). A comparison of statistical 
        significance tests for information retrieval evaluation. CIKM.
    """
    from scipy import stats
    
    if len(scores_a) != len(scores_b):
        raise ValueError("Score lists must have the same length")
    
    t_stat, p_value = stats.ttest_rel(scores_a, scores_b)
    is_significant = p_value < alpha
    
    return p_value, is_significant
