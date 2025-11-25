#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Prepare Corpus Script
数据准备脚本：下载/清洗/格式化为JSONL

功能:
- 可从 HuggingFace Datasets 下载（需指定dataset与配置）
- 或从输入文件读取（TSV/CSV/JSONL）并转换为统一JSONL
- 文本清洗与语言验证

输出JSONL格式（每行一条）：
  {"doc_id": "...", "text": "...", "language": "zh|fr|en"}

示例:
  python scripts/prepare_corpus.py \
    --dataset wikipedia \
    --config_name 20220301.en \
    --text_field text \
    --id_field id \
    --language en \
    --output data/processed/documents.jsonl

  或使用本地文件:
  python scripts/prepare_corpus.py \
    --input data/raw/sample.tsv --input_format tsv \
    --text_field text --id_field id --language fr \
    --output data/processed/documents.jsonl
"""

from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from typing import Optional, List

from src.utils.logger import logger
from src.utils.io import save_jsonl
from src.utils.text_norm import clean_text
from src.utils.lang_detect import detect_language


def iter_hf_dataset(dataset: str, config_name: Optional[str], split: str) -> Optional[List[dict]]:
    try:
        from datasets import load_dataset
    except Exception as e:
        logger.error(f"datasets not available: {e}")
        return None

    logger.info(f"Loading HF dataset: {dataset}, config={config_name}, split={split}")
    try:
        ds = load_dataset(dataset, config_name, split=split)
    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        return None
    records = []
    for i, row in enumerate(ds):
        records.append(dict(row))
    return records


def read_local(path: str, fmt: str) -> List[dict]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    if fmt == "jsonl":
        with open(p, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    if fmt in ("tsv", "csv"):
        import csv
        sep = "\t" if fmt == "tsv" else ","
        with open(p, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=sep)
            return list(reader)
    raise ValueError(f"Unsupported input_format: {fmt}")


def to_jsonl(records: List[dict], text_field: str, id_field: str, language: Optional[str], 
             output: str, max_records: Optional[int] = None, verify_lang: bool = True) -> int:
    out = []
    cnt = 0
    for i, r in enumerate(records):
        if max_records and cnt >= max_records:
            break
        text = str(r.get(text_field, "")).strip()
        if not text:
            continue
        text = clean_text(text)
        doc_id = str(r.get(id_field, f"doc_{i}"))
        lang = language or detect_language(text) or "en"
        if verify_lang and language and lang != language:
            # 过滤与目标语言不匹配的
            continue
        out.append({"doc_id": doc_id, "text": text, "language": lang})
        cnt += 1
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    save_jsonl(out, output)
    logger.info(f"Saved {len(out)} records to {output}")
    return len(out)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Prepare corpus JSONL")
    ap.add_argument("--dataset", type=str, default=None, help="HF dataset name, e.g., wikipedia")
    ap.add_argument("--config_name", type=str, default=None, help="HF dataset config")
    ap.add_argument("--split", type=str, default="train", help="HF split")
    ap.add_argument("--input", type=str, default=None, help="Local input file (jsonl/tsv/csv)")
    ap.add_argument("--input_format", type=str, default="jsonl", choices=["jsonl", "tsv", "csv"])
    ap.add_argument("--text_field", type=str, default="text")
    ap.add_argument("--id_field", type=str, default="id")
    ap.add_argument("--language", type=str, default=None, help="Target language (zh/fr/en)")
    ap.add_argument("--output", type=str, required=True)
    ap.add_argument("--max_records", type=int, default=None)
    ap.add_argument("--no_lang_verify", action="store_true")
    args = ap.parse_args()

    records: Optional[List[dict]] = None
    if args.dataset:
        records = iter_hf_dataset(args.dataset, args.config_name, args.split)
        if records is None:
            logger.error("Failed to load HF dataset; abort")
            sys.exit(1)
    else:
        if not args.input:
            logger.error("Either --dataset or --input is required")
            sys.exit(1)
        records = read_local(args.input, args.input_format)

    to_jsonl(records, args.text_field, args.id_field, args.language, args.output, args.max_records, not args.no_lang_verify)


if __name__ == "__main__":
    main()

