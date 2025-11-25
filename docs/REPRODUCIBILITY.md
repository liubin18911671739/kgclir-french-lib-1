# 可复现实验指南

本文档给出从环境构建到实验复现的完整步骤。

## 1. 环境准备

### 1.1 系统要求
- Python 3.10+
- 建议：NVIDIA GPU + CUDA（可选）

### 1.2 创建虚拟环境
```
python3.10 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 1.3 下载 spaCy 模型
```
python -m spacy download en_core_web_sm
python -m spacy download fr_core_news_sm
python -m spacy download zh_core_web_sm
```

### 1.4 环境检查
```
python scripts/check_environment.py
```

## 2. 数据准备

可从 HuggingFace Datasets 或本地文件准备语料。

### 2.1 使用本地文件（推荐）
```
python scripts/prepare_corpus.py \
  --input data/processed/documents.jsonl \
  --input_format jsonl \
  --text_field text --id_field doc_id --language fr \
  --output outputs/retrieval/corpus.jsonl
```

### 2.2 数据质量验证
```
python scripts/validate_corpus.py --input outputs/retrieval/corpus.jsonl --output outputs/validation/corpus_report.json
```

## 3. 知识图谱构建

```
bash scripts/run_build_kg.sh
```

## 4. 跨语言对齐

```
bash scripts/run_align.sh
```

## 5. 索引构建

```
bash scripts/run_index.sh outputs/retrieval/corpus.jsonl config/retrieval.yaml outputs/retrieval
```

## 6. 检索评测

```
bash scripts/run_eval_clir.sh outputs/retrieval/corpus.jsonl data/qrels/test.qrels data/qrels/queries.tsv config/retrieval.yaml outputs/retrieval/eval_results.json
```

## 7. 一键全流程

```
bash scripts/run_full_experiment.sh
```

## 8. 预期结果与验证

- 评测输出：`outputs/retrieval/eval_results.json`，包含各系统（Translate+BM25、Dense Only、Dense+BM25、KG-CLIR）的平均指标与显著性检验。
- 如需进一步检查，请参考 `src/utils/metrics.py` 的实现与 `tests/` 用例。

## 9. 故障排除（FAQ）

- FAISS 安装失败：
  - CPU 环境请使用 `faiss-cpu==1.7.4`；GPU 环境使用 `faiss-gpu==1.7.4`。
- spaCy 模型下载失败：
  - 使用镜像或离线安装方式；或临时跳过与模型相关功能。
- LLM Key 不存在：
  - RAG 练习生成将自动降级为启发式，不影响其余功能。
- Elasticsearch/Neo4j 不可用：
  - 系统提供 rank-bm25 与内存图降级方案；也可用 `scripts/run_app.sh` 启动 Docker 容器。

