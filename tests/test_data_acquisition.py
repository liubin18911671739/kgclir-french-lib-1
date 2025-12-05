"""
数据获取模块集成测试

测试数据源连接器、文本处理器、质量控制和调度器的集成功能
"""

import pytest
import tempfile
import os
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.data.connectors import (
    AcademicDatabaseConnector,
    OpenDataConnector,
    DataRecord
)
from src.data.processors import (
    TextProcessor,
    MetadataExtractor,
    MultilingualAligner,
    KnowledgeExtractor
)
from src.data.quality_control import (
    DataQualityController,
    QualityValidator,
    DataCleaner
)
from src.data.scheduler import (
    TaskScheduler,
    ScheduledTask,
    TaskStatus,
    TaskPriority
)

class TestDataConnectors:
    """数据连接器测试"""

    @pytest.fixture
    def academic_config(self):
        """学术数据库配置"""
        return {
            'cnki': {
                'api_key': 'test_key',
                'username': 'test_user',
                'password': 'test_pass'
            },
            'pubmed': {
                'email': 'test@example.com'
            },
            'ieee': {
                'api_key': 'test_ieee_key'
            }
        }

    @pytest.fixture
    def open_data_config(self):
        """开放数据平台配置"""
        return {
            'huggingface': {},
            'kaggle': {
                'username': 'test_user',
                'api_key': 'test_kaggle_key'
            }
        }

    def test_academic_connector_init(self, academic_config):
        """测试学术连接器初始化"""
        connector = AcademicDatabaseConnector(academic_config)
        assert connector is not None
        assert 'cnki' in connector.connectors
        assert 'pubmed' in connector.connectors
        assert 'ieee' in connector.connectors

    @patch('src.data.connectors.scholarly.search_pubs')
    def test_google_scholar_search(self, mock_search, academic_config):
        """测试Google Scholar搜索"""
        # 模拟搜索结果
        mock_pub = {
            'bib': {
                'title': 'Test Paper',
                'author': 'Test Author',
                'pub_year': '2023'
            },
            'pub_url': 'https://scholar.google.com/test'
        }
        mock_search.return_value = iter([mock_pub])

        connector = AcademicDatabaseConnector(academic_config)
        results = connector.search("machine learning", databases=['google_scholar'], max_results=1)

        assert len(results) == 1
        assert results[0].title == 'Test Paper'
        assert 'Test Author' in results[0].authors

    def test_data_record_creation(self):
        """测试数据记录创建"""
        record = DataRecord(
            id="test_001",
            title="Test Title",
            authors=["Author 1", "Author 2"],
            abstract="Test abstract",
            content="Test content",
            source="Test Source"
        )

        assert record.id == "test_001"
        assert record.title == "Test Title"
        assert len(record.authors) == 2
        assert record.source == "Test Source"
        assert record.keywords == []  # 默认值

    @patch('src.data.connectors.arxiv.Search')
    def test_arxiv_connector(self, mock_search, academic_config):
        """测试arXiv连接器"""
        # 模拟arXiv搜索结果
        mock_paper = Mock()
        mock_paper.title = "Test arXiv Paper"
        mock_paper.authors = [Mock()]
        mock_paper.authors[0].__str__ = Mock(return_value="Test Author")
        mock_paper.summary = "Test summary"
        mock_paper.entry_id = "https://arxiv.org/test"
        mock_paper.get_short_id = Mock(return_value="test123")
        mock_paper.published = datetime(2023, 1, 1)
        mock_paper.published.strftime = Mock(return_value="2023-01-01")
        mock_paper.primary_category = "cs.AI"
        mock_paper.doi = None

        mock_search_result = Mock()
        mock_search_result.__iter__ = Mock(return_value=iter([mock_paper]))
        mock_search.return_value = mock_search_result

        connector = AcademicDatabaseConnector(academic_config)
        results = connector.search("deep learning", databases=['arxiv'], max_results=1)

        assert len(results) == 1
        assert results[0].title == "Test arXiv Paper"
        assert results[0].source == "arXiv"

class TestTextProcessors:
    """文本处理器测试"""

    @pytest.fixture
    def text_processor_config(self):
        """文本处理器配置"""
        return {
            'text_normalization': {
                'remove_whitespace': True,
                'remove_punctuation': False
            },
            'language_detection': {
                'enabled': True
            },
            'nlp_models': {
                'en': {'model': 'en_core_web_sm', 'enabled': True},
                'zh': {'model': 'zh_core_web_sm', 'enabled': True}
            }
        }

    def test_text_processor_init(self, text_processor_config):
        """测试文本处理器初始化"""
        processor = TextProcessor(text_processor_config)
        assert processor is not None
        assert processor.config == text_processor_config

    def test_text_processing_empty(self, text_processor_config):
        """测试空文本处理"""
        processor = TextProcessor(text_processor_config)
        result = processor.process("")

        assert result.original_text == ""
        assert result.normalized_text == ""
        assert result.word_count == 0
        assert result.sentence_count == 0

    def test_text_processing_basic(self, text_processor_config):
        """测试基本文本处理"""
        processor = TextProcessor(text_processor_config)
        test_text = "This is a test sentence. This is another sentence."
        result = processor.process(test_text, language="en")

        assert result.original_text == test_text
        assert result.language == "en"
        assert result.sentence_count >= 1
        assert result.word_count >= 5
        assert result.quality_score > 0

    def test_multilingual_text_processing(self, text_processor_config):
        """测试多语言文本处理"""
        processor = TextProcessor(text_processor_config)

        # 中文文本
        chinese_text = "这是一个中文测试句子。这是另一个句子。"
        chinese_result = processor.process(chinese_text)
        assert chinese_result.language == "zh"

        # 英文文本
        english_text = "This is an English test sentence."
        english_result = processor.process(english_text)
        assert english_result.language == "en"

    def test_metadata_extraction(self, text_processor_config):
        """测试元数据提取"""
        extractor = MetadataExtractor(text_processor_config)

        test_text = """
        Title: Machine Learning Applications
        Authors: John Doe, Jane Smith
        Abstract: This paper discusses machine learning applications...
        Keywords: machine learning, artificial intelligence, deep learning
        DOI: 10.1234/example.doi
        """

        metadata = extractor.extract_metadata(test_text)

        assert metadata is not None
        # 注意：实际提取效果依赖于正则表达式和文本结构

    def test_multilingual_alignment(self, text_processor_config):
        """测试多语言对齐"""
        aligner = MultilingualAligner(text_processor_config)

        source_text = "This is a test sentence about machine learning."
        target_text = "这是一个关于机器学习的测试句子。"

        alignment = aligner.align_texts(source_text, target_text, "en", "zh")

        assert alignment['source_lang'] == "en"
        assert alignment['target_lang'] == "zh"
        assert 'alignment_score' in alignment
        assert 'aligned_segments' in alignment

    def test_knowledge_extraction(self, text_processor_config):
        """测试知识提取"""
        extractor = KnowledgeExtractor(text_processor_config)

        test_text = """
        Machine learning is a subset of artificial intelligence.
        Deep learning is a type of machine learning.
        Neural networks are used in deep learning.
        """

        concepts = extractor.extract_concepts(test_text, language="en")
        relations = extractor.extract_relations(test_text, concepts)

        assert isinstance(concepts, list)
        assert isinstance(relations, list)

class TestQualityControl:
    """质量控制测试"""

    @pytest.fixture
    def quality_config(self):
        """质量控制配置"""
        return {
            'validation': {
                'quality_thresholds': {
                    'overall': 0.7,
                    'content': 0.6,
                    'metadata': 0.5
                }
            },
            'cleaning': {},
            'database_path': ':memory:'  # 使用内存数据库
        }

    def test_quality_validator_init(self, quality_config):
        """测试质量验证器初始化"""
        validator = QualityValidator(quality_config)
        assert validator is not None
        assert validator.quality_thresholds['overall'] == 0.7

    def test_quality_assessment_good_data(self, quality_config):
        """测试高质量数据评估"""
        validator = QualityValidator(quality_config)

        good_data = {
            'id': 'test_001',
            'title': 'A Comprehensive Study on Machine Learning Applications',
            'content': 'This is a detailed academic paper about machine learning applications in various domains. ' * 20,  # 长内容
            'authors': ['John Doe', 'Jane Smith', 'Bob Johnson'],
            'keywords': ['machine learning', 'artificial intelligence', 'applications'],
            'publish_date': '2023-01-01',
            'doi': '10.1234/example.doi',
            'language': 'en'
        }

        report = validator.assess_quality(good_data)

        assert report.record_id == 'test_001'
        assert report.overall_score > 0.7
        assert len(report.metrics) > 0

    def test_quality_assessment_poor_data(self, quality_config):
        """测试低质量数据评估"""
        validator = QualityValidator(quality_config)

        poor_data = {
            'id': 'test_002',
            'title': 'Bad',  # 太短
            'content': 'Short',  # 太短
            'authors': [],  # 空列表
            'language': 'invalid_lang'  # 无效语言
        }

        report = validator.assess_quality(poor_data)

        assert report.record_id == 'test_002'
        assert report.overall_score < 0.5
        assert len(report.issues) > 0
        assert len(report.recommendations) > 0

    def test_data_cleaning(self, quality_config):
        """测试数据清洗"""
        cleaner = DataCleaner(quality_config)

        dirty_data = {
            'id': 'test_003',
            'title': '  Test Title with   extra spaces  ',
            'content': 'Content with\t\ttabs\n\nand\nextra\nwhitespace',
            'authors': [' Author1 ', '  Author2  ', 'Author1'],  # 重复和多余空格
            'keywords': ['keyword1', '', 'keyword2', 'keyword1'],  # 空值和重复
            'url': 'example.com'  # 缺少协议
        }

        cleaned_data, actions = cleaner.clean_data(dirty_data)

        assert cleaned_data['title'].strip() == cleaned_data['title']  # 无首尾空格
        assert len(cleaned_data['authors']) == 2  # 去重
        assert cleaned_data['url'].startswith('http')  # 添加协议
        assert len(actions) > 0

    def test_data_quality_controller(self, quality_config):
        """测试数据质量控制器"""
        controller = DataQualityController(quality_config)

        test_data = {
            'id': 'test_004',
            'title': 'Test Data Quality Controller',
            'content': 'This is a test for the data quality controller functionality. ' * 10,
            'authors': ['Test Author'],
            'language': 'en'
        }

        cleaned_data, quality_report, cleaning_actions = controller.assess_and_clean(test_data)

        assert cleaned_data is not None
        assert quality_report is not None
        assert isinstance(cleaning_actions, list)
        assert quality_report.record_id == test_data['id']

class TestTaskScheduler:
    """任务调度器测试"""

    @pytest.fixture
    def scheduler_config(self):
        """调度器配置"""
        return {
            'max_workers': 2,
            'max_concurrent_tasks': 2,
            'database_path': ':memory:'
        }

    @pytest.fixture
    def sample_task(self):
        """示例任务"""
        return ScheduledTask(
            id="test_task_001",
            name="Test Data Acquisition",
            description="Test task for data acquisition",
            task_type="data_acquisition",
            schedule="every_1h",
            connector_config={
                'type': 'academic',
                'pubmed': {}
            },
            parameters={
                'query': 'machine learning',
                'max_results': 10
            },
            priority=TaskPriority.NORMAL,
            enabled=True
        )

    def test_scheduler_init(self, scheduler_config):
        """测试调度器初始化"""
        scheduler = TaskScheduler(scheduler_config)
        assert scheduler is not None
        assert scheduler.max_concurrent_tasks == 2

    def test_add_task(self, scheduler_config, sample_task):
        """测试添加任务"""
        scheduler = TaskScheduler(scheduler_config)

        result = scheduler.add_task(sample_task)
        assert result is True
        assert sample_task.id in scheduler.tasks

    def test_remove_task(self, scheduler_config, sample_task):
        """测试移除任务"""
        scheduler = TaskScheduler(scheduler_config)

        # 先添加任务
        scheduler.add_task(sample_task)
        assert sample_task.id in scheduler.tasks

        # 移除任务
        result = scheduler.remove_task(sample_task.id)
        assert result is True
        assert sample_task.id not in scheduler.tasks

    def test_task_status(self, scheduler_config, sample_task):
        """测试任务状态查询"""
        scheduler = TaskScheduler(scheduler_config)

        # 任务不存在
        status = scheduler.get_task_status(sample_task.id)
        assert status is None

        # 添加任务
        scheduler.add_task(sample_task)
        status = scheduler.get_task_status(sample_task.id)
        assert status == TaskStatus.PENDING

    @patch('src.data.connectors.AcademicDatabaseConnector.search')
    def test_task_execution_mock(self, mock_search, scheduler_config, sample_task):
        """测试任务执行（模拟）"""
        # 模拟搜索结果
        mock_records = [
            DataRecord(
                id="mock_001",
                title="Mock Paper 1",
                authors=["Mock Author"],
                abstract="Mock abstract",
                content="Mock content",
                source="Mock Source"
            )
        ]
        mock_search.return_value = mock_records

        scheduler = TaskScheduler(scheduler_config)
        scheduler.add_task(sample_task)

        # 验证任务已添加
        assert sample_task.id in scheduler.tasks

        # 注意：完整的任务执行测试需要更复杂的设置
        # 这里主要测试调度器的基本功能

class TestIntegration:
    """集成测试"""

    @pytest.fixture
    def integration_config(self):
        """集成测试配置"""
        return {
            'connectors': {
                'academic': {
                    'pubmed': {
                        'email': 'test@example.com'
                    }
                }
            },
            'processors': {
                'text_normalization': {},
                'language_detection': {}
            },
            'quality_control': {
                'database_path': ':memory:'
            },
            'scheduler': {
                'max_workers': 1,
                'max_concurrent_tasks': 1,
                'database_path': ':memory:'
            }
        }

    def test_end_to_end_data_processing(self, integration_config):
        """端到端数据处理测试"""
        # 1. 创建数据记录
        record = DataRecord(
            id="integration_001",
            title="机器学习在法语学习中的应用研究",
            authors=["张三", "李四"],
            abstract="本文探讨了机器学习技术在法语教学中的创新应用...",
            content="这是一个详细的学术内容，包含了大量的法语学习相关的研究和分析。" * 10,
            source="测试来源",
            language="zh",
            keywords=["机器学习", "法语学习", "教育技术"]
        )

        # 2. 文本处理
        processor = TextProcessor(integration_config['processors'])
        processed = processor.process(record.content, language=record.language)
        assert processed.language == "zh"
        assert processed.word_count > 0

        # 3. 元数据提取
        extractor = MetadataExtractor(integration_config['processors'])
        metadata = extractor.extract_metadata(record.content)
        assert metadata is not None

        # 4. 质量控制
        controller = DataQualityController(integration_config['quality_control'])

        # 转换为字典格式
        data_dict = {
            'id': record.id,
            'title': record.title,
            'content': record.content,
            'authors': record.authors,
            'language': record.language,
            'keywords': record.keywords
        }

        cleaned_data, quality_report, cleaning_actions = controller.assess_and_clean(data_dict)

        assert cleaned_data is not None
        assert quality_report is not None
        assert isinstance(cleaning_actions, list)

    def test_multilingual_pipeline(self, integration_config):
        """多语言处理管道测试"""
        # 创建多语言数据记录
        records = [
            DataRecord(
                id="zh_001",
                title="中文机器学习研究",
                content="这是关于机器学习的中文研究内容。" * 5,
                source="中文来源",
                language="zh"
            ),
            DataRecord(
                id="en_001",
                title="English Machine Learning Research",
                content="This is English machine learning research content." * 5,
                source="English Source",
                language="en"
            ),
            DataRecord(
                id="fr_001",
                title="Recherche français sur l'apprentissage automatique",
                content="Ceci est un contenu de recherche français sur l'apprentissage automatique." * 5,
                source="Source français",
                language="fr"
            )
        ]

        processor = TextProcessor(integration_config['processors'])

        # 处理每种语言的记录
        for record in records:
            processed = processor.process(record.content, language=record.language)
            assert processed.language == record.language
            assert processed.quality_score > 0

        # 测试多语言对齐
        aligner = MultilingualAligner(integration_config['processors'])

        # 对齐中英文
        zh_record = records[0]
        en_record = records[1]

        alignment = aligner.align_texts(
            zh_record.content, en_record.content, "zh", "en"
        )

        assert alignment['source_lang'] == "zh"
        assert alignment['target_lang'] == "en"
        assert 'alignment_score' in alignment

if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])