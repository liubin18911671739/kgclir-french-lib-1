#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Environment Check (10关键检查)
彩色输出: ✅/❌
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def ok(msg: str):
    print(f"\033[92m✅ {msg}\033[0m")


def fail(msg: str):
    print(f"\033[91m❌ {msg}\033[0m")


def check_python():
    if sys.version_info >= (3, 10):
        ok(f"Python {sys.version.split()[0]}")
        return True
    fail(f"Python >=3.10 required, got {sys.version}")
    return False


def check_torch_cuda():
    try:
        import torch
        s = f"Torch {torch.__version__}"
        if torch.cuda.is_available():
            s += f" + CUDA({torch.cuda.get_device_name(0)})"
        else:
            s += " (CPU)"
        ok(s)
        return True
    except Exception as e:
        fail(f"PyTorch not available: {e}")
        return False


def check_faiss():
    try:
        import faiss  # noqa
        ok("FAISS available")
        return True
    except Exception as e:
        fail(f"FAISS not available: {e}")
        return False


def check_spacy_models():
    try:
        import spacy
        models = {"en": "en_core_web_sm", "fr": "fr_core_news_sm", "zh": "zh_core_web_sm"}
        missing = []
        for lang, model in models.items():
            try:
                spacy.load(model)
            except Exception:
                missing.append(model)
        if missing:
            fail(f"spaCy models missing: {', '.join(missing)}")
            return False
        ok("spaCy models (en/fr/zh) ready")
        return True
    except Exception as e:
        fail(f"spaCy not available: {e}")
        return False


def check_neo4j():
    try:
        import neo4j  # noqa
        ok("neo4j driver import ok (connection optional)")
        return True
    except Exception as e:
        fail(f"neo4j driver not available: {e}")
        return False


def check_elasticsearch():
    try:
        from elasticsearch import Elasticsearch
        es = Elasticsearch(["http://localhost:9200"])  # best-effort
        try:
            if es.ping():
                ok("Elasticsearch reachable at localhost:9200")
            else:
                fail("Elasticsearch not responding (localhost:9200)")
        except Exception:
            fail("Elasticsearch ping failed (may not be running)")
        return True
    except Exception as e:
        fail(f"elasticsearch client not available: {e}")
        return False


def check_configs():
    files = ["config/retrieval.yaml", "config/align.yaml", "config/kg.yaml", "config/app.yaml"]
    missing = [f for f in files if not Path(f).exists()]
    if missing:
        fail(f"Config files missing: {missing}")
        return False
    ok("Config files present")
    return True


def check_data_dirs():
    dirs = ["data", "outputs", "logs"]
    writable = True
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
        test_file = Path(d) / ".write_test"
        try:
            with open(test_file, "w") as f:
                f.write("ok")
            test_file.unlink()
        except Exception as e:
            writable = False
            fail(f"No write permission to {d}: {e}")
    if writable:
        ok("Data directories writable")
    return writable


def check_llm_keys():
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
    if has_openai or has_anthropic:
        ok("LLM API key found")
        return True
    fail("No LLM API key (OPENAI_API_KEY / ANTHROPIC_API_KEY)")
    return False


def check_write_perm():
    try:
        p = Path(".env.test_write")
        with open(p, "w") as f:
            f.write("ok")
        p.unlink()
        ok("Filesystem write permission")
        return True
    except Exception as e:
        fail(f"Cannot write to project root: {e}")
        return False


def main():
    checks = [
        ("Python版本 ≥3.10", check_python),
        ("PyTorch + CUDA", check_torch_cuda),
        ("FAISS GPU", check_faiss),
        ("spaCy模型 (fr/en/zh)", check_spacy_models),
        ("Neo4j连接(驱动)", check_neo4j),
        ("Elasticsearch", check_elasticsearch),
        ("配置文件完整性", check_configs),
        ("数据目录权限", check_data_dirs),
        ("LLM API密钥", check_llm_keys),
        ("写权限", check_write_perm),
    ]

    print("\n===== Environment Check =====")
    passed = 0
    for name, fn in checks:
        try:
            ok_ = fn()
            if ok_:
                passed += 1
        except Exception as e:
            fail(f"{name} error: {e}")

    print("============================\n")
    print(f"Passed: {passed}/{len(checks)} checks")
    sys.exit(0 if passed == len(checks) else 1)


if __name__ == "__main__":
    main()

