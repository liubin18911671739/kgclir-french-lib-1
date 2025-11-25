#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cross-lingual Entity Alignment Evaluation
跨语言实体对齐评测

Evaluation Metrics:
1. Precision@k: 前k个预测中正确的比例
2. Recall@k: 前k个预测覆盖的真实对齐比例  
3. F1@k: Precision和Recall的调和平均
4. Hits@k: 前k个预测中是否包含正确答案
5. MRR (Mean Reciprocal Rank): 首个正确答案排名的倒数

Academic References:
- Standard metrics for entity alignment evaluation
- Commonly used in ISWC, EMNLP entity alignment papers
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import matplotlib.pyplot as plt
from pathlib import Path

from ..utils.logger import logger
from ..utils.io import save_json
from .mtrans_e import AlignmentPair


class AlignmentEvaluator:
    """
    对齐评测器

    Args:
        ground_truth: 真实对齐（测试集）
        predictions: 预测对齐（模型输出）

    Examples:
        >>> evaluator = AlignmentEvaluator(ground_truth, predictions)
        >>> metrics = evaluator.evaluate(k_values=[1, 5, 10])
        >>> evaluator.plot_precision_recall_curve("outputs/pr_curve.png")
    """

    def __init__(
        self,
        ground_truth: List[AlignmentPair],
        predictions: List[AlignmentPair]
    ):
        self.ground_truth = ground_truth
        self.predictions = predictions

        # 构建真实对齐字典
        self.gt_dict = {
            (pair.entity1, pair.entity2): True
            for pair in ground_truth
        }

        # 按置信度排序预测
        self.predictions.sort(key=lambda x: x.confidence, reverse=True)

    def evaluate(
        self,
        k_values: List[int] = [1, 5, 10, 50],
        save_path: Optional[str] = None
    ) -> Dict[str, float]:
        """
        完整评测

        Args:
            k_values: k值列表
            save_path: 保存路径（JSON格式）

        Returns:
            评测结果字典 {
                "precision@1": 0.85,
                "recall@1": 0.12,
                "f1@1": 0.21,
                "hits@1": 0.85,
                "mrr": 0.78,
                ...
            }
        """
        logger.info("Evaluating alignment results...")

        metrics = {}

        # 计算各个k值的指标
        for k in k_values:
            precision_k = self.precision_at_k(k)
            recall_k = self.recall_at_k(k)
            f1_k = self.f1_at_k(k)
            hits_k = self.hits_at_k(k)

            metrics[f"precision@{k}"] = precision_k
            metrics[f"recall@{k}"] = recall_k
            metrics[f"f1@{k}"] = f1_k
            metrics[f"hits@{k}"] = hits_k

        # MRR
        metrics["mrr"] = self.mean_reciprocal_rank()

        # 总体统计
        metrics["total_predictions"] = len(self.predictions)
        metrics["total_ground_truth"] = len(self.ground_truth)
        metrics["correct_predictions"] = self._count_correct()

        # 打印结果
        self._print_metrics(metrics)

        # 保存结果
        if save_path:
            save_json(metrics, save_path)
            logger.info(f"Evaluation results saved to {save_path}")

        return metrics

    def precision_at_k(self, k: int) -> float:
        """
        Precision@k: 前k个预测中正确的比例

        Formula:
            Precision@k = (前k个预测中正确的数量) / k

        Args:
            k: 截断位置

        Returns:
            Precision@k ∈ [0, 1]
        """
        if k <= 0 or k > len(self.predictions):
            k = len(self.predictions)

        if k == 0:
            return 0.0

        top_k_predictions = self.predictions[:k]

        correct = sum(
            1 for pred in top_k_predictions
            if (pred.entity1, pred.entity2) in self.gt_dict
        )

        return correct / k

    def recall_at_k(self, k: int) -> float:
        """
        Recall@k: 前k个预测覆盖的真实对齐比例

        Formula:
            Recall@k = (前k个预测中正确的数量) / (真实对齐总数)

        Args:
            k: 截断位置

        Returns:
            Recall@k ∈ [0, 1]
        """
        if len(self.ground_truth) == 0:
            return 0.0

        if k <= 0 or k > len(self.predictions):
            k = len(self.predictions)

        top_k_predictions = self.predictions[:k]

        correct = sum(
            1 for pred in top_k_predictions
            if (pred.entity1, pred.entity2) in self.gt_dict
        )

        return correct / len(self.ground_truth)

    def f1_at_k(self, k: int) -> float:
        """
        F1@k: Precision@k和Recall@k的调和平均

        Formula:
            F1@k = 2 * (Precision@k * Recall@k) / (Precision@k + Recall@k)

        Args:
            k: 截断位置

        Returns:
            F1@k ∈ [0, 1]
        """
        precision = self.precision_at_k(k)
        recall = self.recall_at_k(k)

        if precision + recall == 0:
            return 0.0

        return 2 * precision * recall / (precision + recall)

    def hits_at_k(self, k: int) -> float:
        """
        Hits@k: 前k个预测中是否包含至少一个正确答案

        对于每个源实体，检查其top-k预测中是否有正确对齐

        Args:
            k: 截断位置

        Returns:
            Hits@k ∈ [0, 1] (命中的源实体比例)
        """
        if k <= 0:
            return 0.0

        # 按源实体分组预测
        predictions_by_source = defaultdict(list)

        for pred in self.predictions:
            predictions_by_source[pred.entity1].append(pred)

        hits = 0
        total = 0

        # 对每个源实体，检查其top-k预测
        for source_entity in predictions_by_source:
            preds = predictions_by_source[source_entity][:k]

            # 检查是否有正确对齐
            has_hit = any(
                (pred.entity1, pred.entity2) in self.gt_dict
                for pred in preds
            )

            if has_hit:
                hits += 1

            total += 1

        return hits / total if total > 0 else 0.0

    def mean_reciprocal_rank(self) -> float:
        """
        MRR (Mean Reciprocal Rank): 首个正确答案排名的倒数

        Formula:
            MRR = (1/N) * Σ(1 / rank_of_first_correct)

        Returns:
            MRR ∈ [0, 1]

        Academic Reference:
            Voorhees (1999). TREC-8 Question Answering Track.
        """
        # 按源实体分组预测
        predictions_by_source = defaultdict(list)

        for pred in self.predictions:
            predictions_by_source[pred.entity1].append(pred)

        reciprocal_ranks = []

        for source_entity in predictions_by_source:
            preds = predictions_by_source[source_entity]

            # 找到首个正确预测的排名
            for rank, pred in enumerate(preds, start=1):
                if (pred.entity1, pred.entity2) in self.gt_dict:
                    reciprocal_ranks.append(1.0 / rank)
                    break
            else:
                # 没有找到正确答案
                reciprocal_ranks.append(0.0)

        return np.mean(reciprocal_ranks) if reciprocal_ranks else 0.0

    def _count_correct(self) -> int:
        """统计正确预测数量"""
        return sum(
            1 for pred in self.predictions
            if (pred.entity1, pred.entity2) in self.gt_dict
        )

    def _print_metrics(self, metrics: Dict[str, float]):
        """打印评测指标（格式化）"""
        logger.info("\n" + "=" * 60)
        logger.info("Alignment Evaluation Results")
        logger.info("=" * 60)

        # Precision@k
        logger.info("\nPrecision@k:")
        for k in [1, 5, 10, 50]:
            key = f"precision@{k}"
            if key in metrics:
                logger.info(f"  P@{k:2d}: {metrics[key]:.4f}")

        # Recall@k
        logger.info("\nRecall@k:")
        for k in [1, 5, 10, 50]:
            key = f"recall@{k}"
            if key in metrics:
                logger.info(f"  R@{k:2d}: {metrics[key]:.4f}")

        # F1@k
        logger.info("\nF1@k:")
        for k in [1, 5, 10, 50]:
            key = f"f1@{k}"
            if key in metrics:
                logger.info(f"  F1@{k:2d}: {metrics[key]:.4f}")

        # Hits@k
        logger.info("\nHits@k:")
        for k in [1, 10]:
            key = f"hits@{k}"
            if key in metrics:
                logger.info(f"  Hits@{k:2d}: {metrics[key]:.4f}")

        # MRR
        if "mrr" in metrics:
            logger.info(f"\nMRR: {metrics['mrr']:.4f}")

        # Summary
        logger.info("\nSummary:")
        logger.info(f"  Total Predictions: {metrics.get('total_predictions', 0)}")
        logger.info(f"  Total Ground Truth: {metrics.get('total_ground_truth', 0)}")
        logger.info(f"  Correct Predictions: {metrics.get('correct_predictions', 0)}")

        logger.info("=" * 60 + "\n")

    def plot_precision_recall_curve(
        self,
        save_path: str = "precision_recall_curve.png",
        max_k: int = 100
    ):
        """
        绘制Precision-Recall曲线

        Args:
            save_path: 保存路径
            max_k: 最大k值
        """
        logger.info("Plotting Precision-Recall curve...")

        k_values = range(1, min(max_k + 1, len(self.predictions) + 1))
        precisions = []
        recalls = []

        for k in k_values:
            precisions.append(self.precision_at_k(k))
            recalls.append(self.recall_at_k(k))

        # 绘图
        plt.figure(figsize=(10, 6))
        plt.plot(recalls, precisions, marker='o', markersize=3, linewidth=2)
        plt.xlabel('Recall', fontsize=12)
        plt.ylabel('Precision', fontsize=12)
        plt.title('Precision-Recall Curve (Entity Alignment)', fontsize=14)
        plt.grid(True, alpha=0.3)
        plt.xlim([0, 1])
        plt.ylim([0, 1])

        # 保存
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()

        logger.info(f"Precision-Recall curve saved to {save_path}")

    def compare_methods(
        self,
        other_predictions: Dict[str, List[AlignmentPair]],
        k_values: List[int] = [1, 5, 10]
    ) -> Dict[str, Dict[str, float]]:
        """
        对比多个方法

        Args:
            other_predictions: {method_name: predictions}
            k_values: k值列表

        Returns:
            对比结果 {
                "Method1": {"precision@1": 0.85, ...},
                "Method2": {"precision@1": 0.82, ...}
            }
        """
        results = {}

        # 当前方法
        current_evaluator = AlignmentEvaluator(self.ground_truth, self.predictions)
        results["Current"] = current_evaluator.evaluate(k_values)

        # 其他方法
        for method_name, preds in other_predictions.items():
            evaluator = AlignmentEvaluator(self.ground_truth, preds)
            results[method_name] = evaluator.evaluate(k_values)

        # 打印对比表格
        self._print_comparison_table(results, k_values)

        return results

    def _print_comparison_table(self, results: Dict, k_values: List[int]):
        """打印对比表格"""
        logger.info("\n" + "=" * 80)
        logger.info("Method Comparison")
        logger.info("=" * 80)

        # 表头
        methods = list(results.keys())
        header = "Metric".ljust(20) + "".join([m.ljust(15) for m in methods])
        logger.info(header)
        logger.info("-" * 80)

        # 每个指标
        metrics_to_compare = []
        for k in k_values:
            metrics_to_compare.extend([f"precision@{k}", f"recall@{k}", f"f1@{k}"])
        metrics_to_compare.append("mrr")

        for metric in metrics_to_compare:
            row = metric.ljust(20)
            for method in methods:
                value = results[method].get(metric, 0.0)
                row += f"{value:.4f}".ljust(15)
            logger.info(row)

        logger.info("=" * 80 + "\n")


def main():
    """主函数：命令行评测入口"""
    import argparse
    from ..utils.io import load_tsv

    parser = argparse.ArgumentParser(description="Evaluate entity alignment results")
    parser.add_argument("--predictions", type=str, required=True, help="Predictions TSV file")
    parser.add_argument("--ground_truth", type=str, required=True, help="Ground truth TSV file")
    parser.add_argument("--output", type=str, default="outputs/alignment", help="Output directory")

    args = parser.parse_args()

    # 加载数据
    logger.info("Loading data...")

    def load_alignments(filepath):
        """从TSV加载对齐"""
        data = load_tsv(filepath, skip_header=True)
        alignments = []
        for row in data:
            if len(row) >= 3:
                alignments.append(AlignmentPair(
                    entity1=row[0],
                    entity2=row[1],
                    confidence=float(row[2]) if len(row) > 2 else 1.0
                ))
        return alignments

    predictions = load_alignments(args.predictions)
    ground_truth = load_alignments(args.ground_truth)

    logger.info(f"Loaded {len(predictions)} predictions")
    logger.info(f"Loaded {len(ground_truth)} ground truth alignments")

    # 评测
    evaluator = AlignmentEvaluator(ground_truth, predictions)
    metrics = evaluator.evaluate(
        k_values=[1, 5, 10, 50],
        save_path=f"{args.output}/evaluation_results.json"
    )

    # 绘制PR曲线
    evaluator.plot_precision_recall_curve(
        save_path=f"{args.output}/precision_recall_curve.png"
    )

    logger.info("Evaluation completed")


if __name__ == "__main__":
    main()
