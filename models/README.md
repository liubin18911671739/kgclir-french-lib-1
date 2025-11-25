# KG-CLIR Models Directory

本目录用于缓存预训练模型和生成的索引文件。

## 目录结构

```
models/
├── transformers/        # HuggingFace Transformers模型缓存
├── sentence_transformers/  # Sentence-Transformers模型
├── faiss_index/         # FAISS向量索引
├── spacy/               # spaCy模型
└── custom/              # 自训练模型
```

## 模型说明

### Sentence-Transformers
- **paraphrase-multilingual-MiniLM-L12-v2**: 多语言语义向量模型
- **LaBSE**: 备选多语言模型

### FAISS索引
- `dense_index.faiss`: 密集向量索引
- `index.metadata`: 索引元数据

### spaCy模型
- `fr_core_news_sm`: 法语NLP模型
- `en_core_web_sm`: 英语NLP模型
- `zh_core_web_sm`: 中文NLP模型

## 模型下载

自动下载（首次运行时）：
```bash
python scripts/check_environment.py
```

手动下载：
```bash
# Sentence-Transformers
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# spaCy
python -m spacy download fr_core_news_sm
python -m spacy download en_core_web_sm
python -m spacy download zh_core_web_sm
```

## 磁盘空间

预计所需空间：
- Transformers模型: ~2GB
- FAISS索引: ~1GB
- spaCy模型: ~500MB
- **总计**: ~3.5GB

⚠️ 本目录不包含在版本控制中。
