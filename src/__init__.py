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

try:
    from .io import load_jsonl, save_jsonl, load_tsv, save_tsv
except ImportError:
    pass

try:
    from .text_norm import normalize_text, remove_stopwords, lemmatize
except ImportError:
    pass

try:
    from .lang_detect import detect_language, is_valid_language
except ImportError:
    pass

try:
    from .metrics import calculate_ndcg, calculate_mrr, calculate_recall
except ImportError:
    pass

try:
    from .stats import compute_statistics, export_statistics
except ImportError:
    pass

try:
    from .logger import get_logger, setup_logging
except ImportError:
    pass

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
