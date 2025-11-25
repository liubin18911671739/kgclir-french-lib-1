#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Validate Corpus Script
数据质量检查（10项）并生成报告
"""

from __future__ import annotations

import os
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Any

from src.utils.logger import logger
from src.utils.io import load_jsonl, save_json
from src.utils.lang_detect import detect_language
from src.utils.text_norm import normalize_text


def validate_corpus(path: str) -> Dict[str, Any]:
    data = load_jsonl(path)
    n = len(data)
    report: Dict[str, Any] = {"path": path, "num_docs": n, "checks": {}, "warnings": []}
    if n == 0:
        report["warnings"].append("Empty corpus")
        return report

    # 1. 非空文本比例
    non_empty = sum(1 for r in data if str(r.get("text", "")).strip())
    report["checks"]["non_empty_ratio"] = non_empty / n

    # 2. 平均文本长度（字符）
    lengths = [len(str(r.get("text", ""))) for r in data]
    report["checks"]["avg_length"] = sum(lengths) / n

    # 3. 语言分布（检测）
    lang_counts = Counter()
    for r in data[: min(n, 2000)]:  # 采样
        text = str(r.get("text", ""))
        lang = r.get("language") or detect_language(text) or "unknown"
        lang_counts[lang] += 1
    report["checks"]["language_distribution_sample"] = dict(lang_counts)

    # 4. doc_id 唯一性
    ids = [str(r.get("doc_id", "")) for r in data]
    report["checks"]["unique_doc_ids"] = len(set(ids)) == len(ids)

    # 5. 文本重复（基于规范化后hash）
    import hashlib
    seen = set()
    dups = 0
    for r in data:
        txt = normalize_text(str(r.get("text", "")))
        h = hashlib.md5(txt.encode("utf-8")).hexdigest()
        if h in seen:
            dups += 1
        else:
            seen.add(h)
    report["checks"]["duplicate_texts"] = dups

    # 6. 极短/极长比例
    short = sum(1 for L in lengths if L < 20)
    very_long = sum(1 for L in lengths if L > 5000)
    report["checks"]["short_ratio"] = short / n
    report["checks"]["very_long_ratio"] = very_long / n

    # 7. ASCII比例（粗略检查非目标语言噪声）
    import string
    def ascii_ratio(s: str) -> float:
        if not s:
            return 0.0
        return sum(1 for ch in s if ch in string.printable) / len(s)
    avg_ascii = sum(ascii_ratio(str(r.get("text", ""))) for r in data[: min(n, 2000)]) / min(n, 2000)
    report["checks"]["avg_ascii_ratio_sample"] = avg_ascii

    # 8. 特殊字符占比（采样）
    import re
    def special_ratio(s: str) -> float:
        if not s:
            return 0.0
        specials = re.findall(r"[^\w\s]", s)
        return len(specials) / max(1, len(s))
    avg_special = sum(special_ratio(str(r.get("text", ""))) for r in data[: min(n, 2000)]) / min(n, 2000)
    report["checks"]["avg_special_ratio_sample"] = avg_special

    # 9. 空语言字段条数
    empty_lang = sum(1 for r in data if not r.get("language"))
    report["checks"]["empty_language_field"] = empty_lang

    # 10. 样例预览
    report["sample"] = data[:3]

    return report


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Validate corpus JSONL")
    ap.add_argument("--input", type=str, required=True)
    ap.add_argument("--output", type=str, default="outputs/validation/corpus_report.json")
    args = ap.parse_args()

    report = validate_corpus(args.input)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    save_json(report, args.output)
    logger.info(f"Saved report to {args.output}")


if __name__ == "__main__":
    main()

