"""
数据获取和管理模块

本模块提供多源数据获取、处理和管理功能，支持：
- 学术数据库连接器 (CNKI, PubMed, IEEE, Google Scholar)
- 开放数据平台连接器 (HuggingFace, Kaggle)
- 文本处理器和多语言支持
- 数据质量控制和更新调度
"""

from .connectors import (
    AcademicDatabaseConnector,
    OpenDataConnector,
    LibrarySystemConnector,
    SocialMediaConnector
)

from .processors import (
    TextProcessor,
    MetadataExtractor,
    MultilingualAligner,
    KnowledgeExtractor
)

from .quality_control import (
    DataQualityController,
    QualityValidator,
    DataCleaner
)

from .scheduler import (
    DataUpdateScheduler,
    TaskScheduler,
    MonitoringService
)

__all__ = [
    # Connectors
    "AcademicDatabaseConnector",
    "OpenDataConnector",
    "LibrarySystemConnector",
    "SocialMediaConnector",

    # Processors
    "TextProcessor",
    "MetadataExtractor",
    "MultilingualAligner",
    "KnowledgeExtractor",

    # Quality Control
    "DataQualityController",
    "QualityValidator",
    "DataCleaner",

    # Scheduler
    "DataUpdateScheduler",
    "TaskScheduler",
    "MonitoringService",
]