#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Learning Evaluation
学习效果评估

实现:
- 对照实验(实验组vs对照组)的前测/后测统计
- 显著性检验: paired t-test (对同一学习者 pre/post)
- 效应量: Cohen's d
- 学习曲线可视化: 按时间点的平均分折线
- 输出: CSV/JSON 结果
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Tuple, Any
import json

import numpy as np
from scipy import stats
import matplotlib.pyplot as plt

from ..utils.logger import logger
from ..utils.io import load_tsv, save_json
from ..utils.stats import cohen_d


def load_experiment_table(path: str) -> List[Dict[str, Any]]:
    """
    加载对照实验数据 (TSV/CSV)
    要求列: learner_id, group, pre_score, post_score, time(optional)
    """
    sep = "\t" if path.endswith(".tsv") else ","
    import csv
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=sep)
        for r in reader:
            rows.append(r)
    return rows


def evaluate_groups(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """计算每组的前后测统计与检验"""
    groups = {}
    for r in rows:
        g = r.get("group", "control")
        groups.setdefault(g, {"pre": [], "post": []})
        try:
            pre = float(r.get("pre_score", 0))
            post = float(r.get("post_score", 0))
        except Exception:
            continue
        groups[g]["pre"].append(pre)
        groups[g]["post"].append(post)

    results = {"groups": {}}
    for g, data in groups.items():
        pre = np.array(data["pre"], dtype=float)
        post = np.array(data["post"], dtype=float)
        if len(pre) == 0 or len(post) == 0 or len(pre) != len(post):
            continue
        diff = post - pre
        # Paired t-test
        t, p = stats.ttest_rel(post, pre)
        # Cohen's d (paired): 使用差值/标准差近似
        d = cohen_d(post.tolist(), pre.tolist())
        results["groups"][g] = {
            "n": int(len(pre)),
            "pre_mean": float(pre.mean()),
            "post_mean": float(post.mean()),
            "delta_mean": float(diff.mean()),
            "t_stat": float(t),
            "p_value": float(p),
            "cohens_d": float(d),
        }

    # 组间后测对比（independent t-test）
    if len(groups) >= 2:
        keys = list(groups.keys())
        g1, g2 = keys[0], keys[1]
        post1 = np.array(groups[g1]["post"], dtype=float)
        post2 = np.array(groups[g2]["post"], dtype=float)
        if len(post1) > 1 and len(post2) > 1:
            t, p = stats.ttest_ind(post1, post2, equal_var=False)
            results["between_groups"] = {
                "g1": g1,
                "g2": g2,
                "post_mean_g1": float(post1.mean()),
                "post_mean_g2": float(post2.mean()),
                "t_stat": float(t),
                "p_value": float(p),
                "cohens_d": float(cohen_d(post1.tolist(), post2.tolist())),
            }

    return results


def plot_learning_curve(rows: List[Dict[str, Any]], save_path: str) -> None:
    """
    按时间点绘制平均分学习曲线（若有 time 列，如 week1/week2/... 或日期）
    """
    # 聚合时间点
    buckets = {}
    for r in rows:
        t = r.get("time")
        if not t:
            continue
        try:
            post = float(r.get("post_score", 0))
        except Exception:
            continue
        buckets.setdefault(t, []).append(post)

    if not buckets:
        logger.info("No time column found; skip curve plot")
        return

    xs = sorted(buckets.keys())
    ys = [float(np.mean(buckets[x])) for x in xs]

    import matplotlib.pyplot as plt
    plt.figure(figsize=(8, 5))
    plt.plot(xs, ys, marker="o")
    plt.xlabel("Time")
    plt.ylabel("Average Post Score")
    plt.title("Learning Curve")
    plt.grid(True, alpha=0.3)
    Path(os.path.dirname(save_path)).mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close()
    logger.info(f"Learning curve saved to {save_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate learning outcomes")
    parser.add_argument("--table", type=str, required=True, help="Experiment table CSV/TSV with pre/post")
    parser.add_argument("--output_dir", type=str, default="outputs/learning", help="Output directory")

    args = parser.parse_args()

    rows = load_experiment_table(args.table)
    results = evaluate_groups(rows)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    save_json(results, out_dir / "evaluation_results.json")
    logger.info(f"Saved evaluation results to {out_dir / 'evaluation_results.json'}")

    # 学习曲线（可选）
    plot_learning_curve(rows, str(out_dir / "learning_curve.png"))

    # 导出简表CSV
    import csv
    table_path = out_dir / "summary.csv"
    with open(table_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["group", "n", "pre_mean", "post_mean", "delta_mean", "p_value", "cohens_d"])
        for g, stats_dict in results.get("groups", {}).items():
            writer.writerow([
                g,
                stats_dict.get("n", 0),
                f"{stats_dict.get('pre_mean', 0):.3f}",
                f"{stats_dict.get('post_mean', 0):.3f}",
                f"{stats_dict.get('delta_mean', 0):.3f}",
                f"{stats_dict.get('p_value', 1.0):.4f}",
                f"{stats_dict.get('cohens_d', 0):.3f}",
            ])
    logger.info(f"Saved summary CSV to {table_path}")


if __name__ == "__main__":
    main()
