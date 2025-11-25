#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Statistics Utilities
统计分析工具

提供数据统计和分析功能。
"""

from typing import Dict, List, Any, Union, Optional
from collections import Counter
import numpy as np


def compute_statistics(
    data: List[Union[int, float]],
    percentiles: List[int] = [25, 50, 75]
) -> Dict[str, float]:
    """
    计算基本统计量
    
    Args:
        data: 数值列表
        percentiles: 要计算的百分位数
    
    Returns:
        统计量字典
    
    Examples:
        >>> data = [1, 2, 3, 4, 5]
        >>> stats = compute_statistics(data)
        >>> print(stats['mean'], stats['std'])
    """
    if not data:
        return {}
    
    data_array = np.array(data)
    
    stats = {
        "count": len(data),
        "mean": float(np.mean(data_array)),
        "std": float(np.std(data_array)),
        "min": float(np.min(data_array)),
        "max": float(np.max(data_array)),
        "sum": float(np.sum(data_array))
    }
    
    # 百分位数
    for p in percentiles:
        stats[f"p{p}"] = float(np.percentile(data_array, p))
    
    return stats


def count_distribution(
    items: List[Any]
) -> Dict[Any, int]:
    """
    统计元素分布
    
    Args:
        items: 元素列表
    
    Returns:
        {元素: 出现次数}
    """
    return dict(Counter(items))


def export_statistics(
    stats_dict: Dict[str, Any],
    output_path: str
) -> None:
    """
    导出统计信息到JSON文件
    
    Args:
        stats_dict: 统计字典
        output_path: 输出路径
    """
    from .io import save_json
    save_json(stats_dict, output_path)


def calculate_improvement(
    baseline_score: float,
    new_score: float,
    percentage: bool = True
) -> float:
    """
    计算性能提升
    
    Args:
        baseline_score: 基线得分
        new_score: 新方法得分
        percentage: 是否返回百分比
    
    Returns:
        提升量
    """
    if baseline_score == 0:
        return 0.0
    
    improvement = (new_score - baseline_score) / baseline_score
    
    return improvement * 100 if percentage else improvement


def cohen_d(
    group1: List[float],
    group2: List[float]
) -> float:
    """
    计算Cohen's d效应量
    
    Args:
        group1: 组1数据
        group2: 组2数据
    
    Returns:
        效应量d
    
    学术参考：
        Cohen (1988). Statistical Power Analysis for the Behavioral Sciences.
    """
    mean1 = np.mean(group1)
    mean2 = np.mean(group2)
    
    std1 = np.std(group1, ddof=1)
    std2 = np.std(group2, ddof=1)
    
    n1 = len(group1)
    n2 = len(group2)
    
    # 合并标准差
    pooled_std = np.sqrt(((n1 - 1) * std1**2 + (n2 - 1) * std2**2) / (n1 + n2 - 2))
    
    if pooled_std == 0:
        return 0.0
    
    return (mean1 - mean2) / pooled_std
