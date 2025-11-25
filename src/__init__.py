"""
KG-CLIR Utilities Package
工具函数模块

提供项目所需的通用工具函数，包括：
- I/O操作
- 文本规范化
- 语言检测
- 评价指标
- 统计分析
- 日志系统
"""

__version__ = "1.0.0"
__author__ = "KG-CLIR Research Team"

from .io import load_jsonl, save_jsonl, load_tsv, save_tsv
from .text_norm import normalize_text, remove_stopwords, lemmatize
from .lang_detect import detect_language, is_valid_language
from .metrics import calculate_ndcg, calculate_mrr, calculate_recall
from .stats import compute_statistics, export_statistics
from .logger import get_logger, setup_logging

__all__ = [
    # I/O
    "load_jsonl",
    "save_jsonl",
    "load_tsv",
    "save_tsv",
    # Text normalization
    "normalize_text",
    "remove_stopwords",
    "lemmatize",
    # Language detection
    "detect_language",
    "is_valid_language",
    # Metrics
    "calculate_ndcg",
    "calculate_mrr",
    "calculate_recall",
    # Statistics
    "compute_statistics",
    "export_statistics",
    # Logging
    "get_logger",
    "setup_logging",
]
