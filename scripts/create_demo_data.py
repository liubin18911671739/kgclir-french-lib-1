#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Create minimal demo dataset for the project.
生成最小演示数据集：
- data/demo/demo_corpus.jsonl (100 docs, zh/fr/en)
- data/seeds/align_seeds.tsv (~60 pairs)
- data/qrels/queries.tsv (100 queries)
- data/qrels/test.qrels (~300 judgments)
"""

from __future__ import annotations

import os
from pathlib import Path
import json
from typing import List, Dict


def ensure_dir(p: str):
    Path(p).mkdir(parents=True, exist_ok=True)


topics = [
    {"fr": "subjonctif", "zh": "虚拟式", "en": "subjunctive"},
    {"fr": "passé composé", "zh": "复合过去时", "en": "passe compose"},
    {"fr": "imparfait", "zh": "未完成过去时", "en": "imparfait"},
    {"fr": "articles", "zh": "冠词", "en": "articles"},
    {"fr": "pronoms", "zh": "代词", "en": "pronouns"},
    {"fr": "conditionnel", "zh": "条件式", "en": "conditional"},
    {"fr": "futur", "zh": "将来时", "en": "future tense"},
    {"fr": "négation", "zh": "否定", "en": "negation"},
    {"fr": "accord", "zh": "配合一致", "en": "agreement"},
    {"fr": "vocabulaire", "zh": "词汇", "en": "vocabulary"},
]

lang_cycle = ["fr", "zh", "en"]


def build_corpus(n_docs: int = 100) -> List[Dict]:
    docs = []
    for i in range(n_docs):
        idx = i + 1
        topic = topics[i % len(topics)]
        lang = lang_cycle[i % len(lang_cycle)]
        term = topic[lang]
        title = {
            "fr": f"FR: {term}",
            "zh": f"ZH: {term}",
            "en": f"EN: {term}",
        }[lang]
        content = {
            "fr": f"Ce document traite de {term} en français. Exemples et règles essentielles.",
            "zh": f"本文介绍法语{term}的用法与例句，含基本规则。",
            "en": f"This document covers French {term} with rules and examples.",
        }[lang]
        rec = {
            "doc_id": f"doc_{idx:04d}",
            "title": title,
            "content": content,
            "text": content,  # 兼容现有检索构建脚本
            "language": lang,
        }
        docs.append(rec)
    return docs


def save_jsonl(recs: List[Dict], path: str):
    ensure_dir(Path(path).parent)
    with open(path, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def build_align_seeds(n_pairs: int = 60) -> List[str]:
    lines = ["source_id\ttarget_id\tconfidence"]
    # 主题映射：zh <-> fr
    pairs = []
    for i, t in enumerate(topics):
        pairs.append((t["zh"], t["fr"]))
    # 重复填充到 n_pairs
    i = 0
    while len(pairs) < n_pairs:
        pairs.append(pairs[i % len(topics)])
        i += 1
    for (src, tgt) in pairs[:n_pairs]:
        lines.append(f"{src}\t{tgt}\t0.95")
    return lines


def build_queries(n_queries: int = 100) -> List[str]:
    lines = ["query_id\tquery_text\tlanguage"]
    for i in range(n_queries):
        idx = i + 1
        topic = topics[i % len(topics)]
        lang = lang_cycle[i % len(lang_cycle)]
        text = {
            "fr": f"{topic['fr']} français",
            "zh": f"{topic['zh']} 用法",
            "en": f"French {topic['en']} usage",
        }[lang]
        lines.append(f"q{idx}\t{text}\t{lang}")
    return lines


def build_qrels(n_queries: int = 100, rel_per_q: int = 3) -> List[str]:
    lines: List[str] = []
    for i in range(n_queries):
        qid = f"q{i+1}"
        topic_idx = i % len(topics)
        # 选择与该topic匹配的文档（索引 % 10 == topic_idx）
        picked = 0
        doc_num = topic_idx + 1
        tries = 0
        while picked < rel_per_q and tries < 200:
            did = f"doc_{doc_num:04d}"
            lines.append(f"{qid} 0 {did} 1")
            picked += 1
            doc_num += 10  # 下一批同主题
            if doc_num > 100:
                doc_num = (doc_num % 100)
                if doc_num == 0:
                    doc_num = 10
            tries += 1
    return lines


def main():
    # 1) Corpus
    corpus = build_corpus(100)
    save_jsonl(corpus, "data/demo/demo_corpus.jsonl")

    # 2) Align seeds
    ensure_dir("data/seeds")
    with open("data/seeds/align_seeds.tsv", "w", encoding="utf-8") as f:
        f.write("\n".join(build_align_seeds(60)) + "\n")

    # 3) Queries
    ensure_dir("data/qrels")
    with open("data/qrels/queries.tsv", "w", encoding="utf-8") as f:
        f.write("\n".join(build_queries(100)) + "\n")

    # 4) Qrels
    with open("data/qrels/test.qrels", "w", encoding="utf-8") as f:
        f.write("\n".join(build_qrels(100, 3)) + "\n")

    print("Demo data generated.")


if __name__ == "__main__":
    main()

