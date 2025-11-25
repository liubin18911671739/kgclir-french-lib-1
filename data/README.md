# Data Directory

本目录包含KG-CLIR系统的所有数据文件。

## 目录结构

```
data/
├── raw/              # 原始语料（未处理）
├── processed/        # 预处理后语料
├── seeds/            # 跨语言对齐种子
├── qrels/            # 检索评测标注数据
└── demo/             # 演示数据（小规模）
```

## 数据说明

### raw/ - 原始语料
从HuggingFace等数据源下载的原始数据。

### processed/ - 预处理语料
经过清洗、规范化的JSONL格式数据：
- `textbooks_fr.jsonl` - 法语教材
- `academic_resources.jsonl` - 学术文章
- `exercises_fr.jsonl` - 练习题库
- `alignment_seeds.jsonl` - 平行语料

### seeds/ - 对齐种子
人工标注的跨语言实体对齐：
- `align_seeds.tsv` - 训练集种子对齐
- `test_alignments.tsv` - 测试集对齐

格式：`source_id\ttarget_id\tconfidence`

### qrels/ - 检索评测数据
TREC格式的相关性标注：
- `train.qrels` - 训练集
- `validation.qrels` - 验证集
- `test.qrels` - 测试集
- `queries.tsv` - 查询集

格式：`query_id 0 doc_id relevance`

### demo/ - 演示数据
用于快速演示的小规模数据集。

## 数据准备

运行数据准备脚本：

```bash
python scripts/prepare_corpus.py
```

## 数据隐私

⚠️ 本目录不包含在版本控制中。如需获取完整数据集，请联系项目维护者。
