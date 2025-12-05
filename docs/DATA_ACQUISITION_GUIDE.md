# 数据获取系统使用指南

## 概述

KG-CLIR数据获取系统提供全面的多源数据采集、处理和管理功能，支持学术数据库、开放数据平台、图书馆系统和社交媒体等多种数据源。系统包含四个核心模块：

1. **数据源连接器** (`src/data/connectors.py`) - 多源数据连接和获取
2. **文本处理器** (`src/data/processors.py`) - 多语言文本处理和元数据提取
3. **数据质量控制** (`src/data/quality_control.py`) - 质量检查、验证和清洗
4. **数据更新调度器** (`src/data/scheduler.py`) - 自动化调度和监控

## 快速开始

### 安装依赖

```bash
# 基础依赖
pip install requests beautifulsoup4 feedparser

# 数据库连接
pip install neo4j arxiv scholarly

# 文本处理
pip install spacy jieba langdetect
python -m spacy download en_core_web_sm
python -m spacy download zh_core_web_sm
python -m spacy download fr_core_news_sm

# 文件处理
pip install PyPDF2 pdfplumber python-docx openpyxl pandas

# 调度系统
pip install schedule

# 可选：特定平台API
pip install kaggle praw tweepy datasets
```

### 基本使用示例

```python
from src.data.connectors import AcademicDatabaseConnector
from src.data.processors import TextProcessor
from src.data.quality_control import DataQualityController

# 1. 数据获取
connector = AcademicDatabaseConnector({
    'pubmed': {'email': 'your-email@example.com'},
    'arxiv': {}
})

results = connector.search("machine learning", databases=['pubmed', 'arxiv'], max_results=50)

# 2. 文本处理
processor = TextProcessor({
    'language_detection': {'enabled': True},
    'nlp_models': {
        'en': {'model': 'en_core_web_sm', 'enabled': True}
    }
})

for record in results:
    processed = processor.process(record.content)
    print(f"语言: {processed.language}, 质量分数: {processed.quality_score:.2f}")

# 3. 质量控制
controller = DataQualityController({
    'validation': {'quality_thresholds': {'overall': 0.7}}
})

data_dict = {
    'id': results[0].id,
    'title': results[0].title,
    'content': results[0].content,
    'authors': results[0].authors,
    'language': 'en'
}

cleaned_data, quality_report, actions = controller.assess_and_clean(data_dict)
print(f"质量分数: {quality_report.overall_score:.2f}")
```

## 数据源连接器详解

### 学术数据库连接器

支持多个主要学术数据库：

#### PubMed
```python
connector = AcademicDatabaseConnector({
    'pubmed': {
        'email': 'your-email@example.com'  # 必需
    }
})

results = connector.search("deep learning", databases=['pubmed'], max_results=100)
```

#### IEEE Xplore
```python
connector = AcademicDatabaseConnector({
    'ieee': {
        'api_key': 'your-ieee-api-key'  # 必需
    }
})

results = connector.search("neural networks", databases=['ieee'], max_results=50)
```

#### arXiv
```python
connector = AcademicDatabaseConnector({
    'arxiv': {}  # 不需要API密钥
})

results = connector.search("transformer models", databases=['arxiv'], max_results=30)
```

#### Google Scholar
```python
connector = AcademicDatabaseConnector({
    'google_scholar': {}  # 使用scholarly库，有限制
})

results = connector.search("attention mechanism", databases=['google_scholar'], max_results=20)
```

#### CNKI (知网)
```python
connector = AcademicDatabaseConnector({
    'cnki': {
        'api_key': 'your-cnki-api-key',  # 可选
        'username': 'your-username',     # 可选
        'password': 'your-password'      # 可选
    }
})

results = connector.search("法语学习", databases=['cnki'], max_results=50)
```

### 开放数据平台连接器

#### HuggingFace Datasets
```python
from src.data.connectors import OpenDataConnector

connector = OpenDataConnector({
    'huggingface': {}  # 不需要额外配置
})

results = connector.search("text classification", platforms=['huggingface'], max_results=20)
```

#### Kaggle
```python
connector = OpenDataConnector({
    'kaggle': {
        'username': 'your-kaggle-username',
        'api_key': 'your-kaggle-api-key'
    }
})

results = connector.search("machine learning", platforms=['kaggle'], max_results=15)
```

### 数据记录格式

所有连接器返回统一的数据记录格式：

```python
@dataclass
class DataRecord:
    id: str                    # 唯一标识符
    title: str                 # 标题
    authors: List[str]         # 作者列表
    abstract: str              # 摘要
    content: str              # 内容
    source: str               # 数据源
    url: Optional[str]        # URL链接
    doi: Optional[str]        # DOI标识符
    publish_date: Optional[str]  # 发表日期
    language: Optional[str]   # 语言代码
    keywords: List[str]       # 关键词
    category: Optional[str]   # 分类
    metadata: Dict[str, Any]  # 额外元数据
```

## 文本处理器详解

### 多语言文本处理

支持中文、法语、英语的处理：

```python
from src.data.processors import TextProcessor

processor = TextProcessor({
    'text_normalization': {
        'remove_whitespace': True,
        'remove_punctuation': False,
        'lowercase': False
    },
    'language_detection': {
        'enabled': True,
        'default_language': 'en'
    },
    'nlp_models': {
        'zh': {'model': 'zh_core_web_sm', 'enabled': True},
        'fr': {'model': 'fr_core_news_sm', 'enabled': True},
        'en': {'model': 'en_core_web_sm', 'enabled': True}
    }
})

# 自动语言检测
result = processor.process("这是一个中文测试文本")
print(f"检测语言: {result.language}")
print(f"句子数: {result.sentence_count}")
print(f"词汇数: {result.word_count}")
print(f"实体数: {len(result.entities)}")

# 指定语言处理
result = processor.process("This is an English text", language="en")
```

### 元数据提取

```python
from src.data.processors import MetadataExtractor

extractor = MetadataExtractor({
    'extraction_rules': {
        'enable_doi_extraction': True,
        'enable_url_extraction': True,
        'enable_date_extraction': True
    }
}

text = """
Title: Machine Learning in Education
Authors: John Doe, Jane Smith
Keywords: machine learning, education, AI
DOI: 10.1234/education.ml.2023
Publication: 2023-01-15
"""

metadata = extractor.extract_metadata(text)

print(f"标题: {metadata.title}")
print(f"作者: {metadata.authors}")
print(f"关键词: {metadata.keywords}")
print(f"DOI: {metadata.doi}")
```

### 多语言对齐

```python
from src.data.processors import MultilingualAligner

aligner = MultilingualAligner({
    'alignment_methods': ['lexical', 'embedding']
})

source_text = "机器学习是人工智能的一个重要分支"
target_text = "Machine learning is an important branch of artificial intelligence"

alignment = aligner.align_texts(
    source_text, target_text, "zh", "en"
)

print(f"对齐分数: {alignment['alignment_score']:.2f}")
print(f"对齐片段数: {len(alignment['aligned_segments'])}")

for segment in alignment['aligned_segments']:
    print(f"源: {segment['source_sentence']}")
    print(f"目标: {segment['target_sentence']}")
    print(f"类型: {segment['alignment_type']}")
    print("-" * 50)
```

### 知识提取

```python
from src.data.processors import KnowledgeExtractor

extractor = KnowledgeExtractor({
    'knowledge_patterns': {
        'enable_concept_extraction': True,
        'enable_relation_extraction': True
    }
})

text = """
Machine learning is a subset of artificial intelligence.
Deep learning is a type of machine learning.
Neural networks are used in deep learning applications.
"""

# 提取概念
concepts = extractor.extract_concepts(text, language="en")
for concept in concepts:
    print(f"概念: {concept['name']}, 类型: {concept['type']}")

# 提取关系
relations = extractor.extract_relations(text, concepts)
for relation in relations:
    print(f"关系: {relation['subject']} -> {relation['object']}")
    print(f"类型: {relation['relation_type']}")
```

## 数据质量控制详解

### 质量评估

```python
from src.data.quality_control import DataQualityController

controller = DataQualityController({
    'validation': {
        'quality_thresholds': {
            'overall': 0.7,      # 总体质量阈值
            'content': 0.6,      # 内容质量阈值
            'metadata': 0.5,     # 元数据质量阈值
            'structure': 0.6     # 结构质量阈值
        }
    },
    'cleaning': {
        'enable_text_cleaning': True,
        'enable_format_standardization': True
    }
})

data = {
    'id': 'example_001',
    'title': 'A Comprehensive Study on Machine Learning',
    'content': 'This paper presents a comprehensive analysis of machine learning techniques...',
    'authors': ['John Doe', 'Jane Smith'],
    'keywords': ['machine learning', 'artificial intelligence'],
    'language': 'en',
    'publish_date': '2023-01-01'
}

# 评估质量并清洗
cleaned_data, quality_report, cleaning_actions = controller.assess_and_clean(data)

print(f"总体质量分数: {quality_report.overall_score:.2f}")
print(f"问题数量: {len(quality_report.issues)}")
print(f"改进建议: {len(quality_report.recommendations)}")
print(f"清洗操作: {len(cleaning_actions)}")

# 查看详细指标
for metric in quality_report.metrics:
    print(f"{metric.name}: {metric.value:.2f} (阈值: {metric.threshold})")
```

### 质量指标说明

#### 内容质量指标
- **内容长度** (weight: 0.15): 基于内容字符数的质量分数
- **语言质量** (weight: 0.10): 语言检测置信度
- **内容结构** (weight: 0.10): 句子和段落结构的合理性
- **标题质量** (weight: 0.10): 标题长度和描述性

#### 元数据质量指标
- **作者完整性** (weight: 0.08): 作者信息的完整性
- **关键词质量** (weight: 0.06): 关键词数量和相关性
- **日期质量** (weight: 0.05): 发表日期的存在和格式
- **标识符质量** (weight: 0.06): DOI/URL等标识符的存在

#### 结构质量指标
- **必需字段完整性** (weight: 0.15): 必需字段的存在性
- **数据类型一致性** (weight: 0.10): 字段数据类型的正确性
- **格式一致性** (weight: 0.05): 字段格式的规范性

#### 一致性质量指标
- **语言一致性** (weight: 0.08): 声明语言与实际内容的一致性
- **日期一致性** (weight: 0.05): 多个日期字段的逻辑一致性
- **长度合理性** (weight: 0.07): 各长度字段值的合理性

### 数据清洗功能

```python
from src.data.quality_control import DataCleaner

cleaner = DataCleaner({
    'text_cleaning': {
        'remove_extra_whitespace': True,
        'normalize_punctuation': True,
        'remove_special_chars': True
    },
    'format_standardization': {
        'date_format': 'YYYY-MM-DD',
        'url_protocol': 'https'
    }
})

dirty_data = {
    'title': '  Machine Learning   Applications  ',
    'content': 'Content with   extra   whitespace\t\tand\n\nline breaks.',
    'authors': ['  Author One  ', 'Author Two', '  Author One  '],  # 重复
    'url': 'example.com',  # 缺少协议
    'publish_date': '01/15/2023'  # 非标准格式
}

cleaned_data, actions = cleaner.clean_data(dirty_data)

print("清洗操作:")
for action in actions:
    print(f"  {action['field']}: {action['action']}")

print(f"\n清洗后标题: '{cleaned_data['title']}'")
print(f"清洗后URL: {cleaned_data['url']}")
print(f"清洗后作者: {cleaned_data['authors']}")
print(f"清洗后日期: {cleaned_data['publish_date']}")
```

## 数据更新调度器详解

### 创建调度任务

```python
from src.data.scheduler import TaskScheduler, ScheduledTask, TaskPriority

scheduler = TaskScheduler({
    'max_workers': 3,
    'max_concurrent_tasks': 2,
    'database_path': 'data/scheduler.db'
})

# 创建数据获取任务
acquisition_task = ScheduledTask(
    id="pubmed_daily_update",
    name="PubMed每日更新",
    description="每日从PubMed获取最新的机器学习相关文献",
    task_type="data_acquisition",
    schedule="daily_09:00",  # 每天9点执行
    connector_config={
        'type': 'academic',
        'pubmed': {'email': 'your-email@example.com'}
    },
    parameters={
        'query': 'machine learning',
        'max_results': 100,
        'date_range': '7d'  # 最近7天
    },
    priority=TaskPriority.HIGH,
    enabled=True,
    max_retries=3,
    retry_delay=300,
    timeout=1800
)

scheduler.add_task(acquisition_task)
```

### 调度表达式格式

#### 间隔调度
```python
# 每隔5分钟
schedule="every_5m"

# 每隔2小时
schedule="every_2h"

# 每隔1天
schedule="every_1d"
```

#### 定时调度
```python
# 每天9:00
schedule="daily_09:00"

# 每周一10:30
schedule="weekly_monday_10:30"

# 每周三14:00
schedule="weekly_wednesday_14:00"
```

### 任务类型

#### 数据获取任务
```python
data_acquisition_task = ScheduledTask(
    id="academic_update",
    task_type="data_acquisition",
    connector_config={
        'type': 'academic',
        'pubmed': {},
        'arxiv': {}
    },
    parameters={
        'query': 'french language learning',
        'databases': ['pubmed', 'arxiv'],
        'max_results': 50
    },
    schedule="daily_08:00"
)
```

#### 质量检查任务
```python
quality_check_task = ScheduledTask(
    id="quality_check",
    task_type="quality_check",
    connector_config={
        'validation': {
            'quality_thresholds': {'overall': 0.7}
        }
    },
    parameters={
        'limit': 100,  # 检查最近100条记录
        'quality_threshold': 0.7
    },
    schedule="every_1h"
)
```

#### 数据更新任务
```python
data_update_task = ScheduledTask(
    id="data_refresh",
    task_type="data_update",
    connector_config={
        'type': 'academic',
        'pubmed': {}
    },
    parameters={
        'update_frequency': 'weekly',
        'max_age_days': 30  # 更新30天前的记录
    },
    schedule="weekly_sunday_02:00"
)
```

### 启动和监控调度器

```python
# 启动调度器
scheduler.start()

# 获取任务状态
status = scheduler.get_task_status("pubmed_daily_update")
print(f"任务状态: {status}")

# 获取执行历史
history = scheduler.get_task_history("pubmed_daily_update", limit=10)
for execution in history:
    print(f"{execution.started_at}: {execution.status.value}")
    if execution.result:
        print(f"  处理记录数: {execution.records_processed}")

# 获取系统状态
from src.data.scheduler import MonitoringService

monitor = MonitoringService(scheduler, {
    'alert_thresholds': {
        'failure_rate': 0.2,
        'execution_time': 1800,
        'queue_size': 5
    }
})

system_status = monitor.get_system_status()
print(f"运行任务数: {system_status['tasks']['running']}")
print(f"24小时失败率: {system_status['executions']['last_24h']['failure_rate']:.1%}")

# 停止调度器
scheduler.stop()
```

## 配置文件示例

### 完整配置文件 (config/data_acquisition.yaml)

```yaml
# 数据获取配置
connectors:
  academic:
    pubmed:
      email: "your-email@example.com"
      api_key: null  # 可选
    ieee:
      api_key: "your-ieee-api-key"
    arxiv: {}
    google_scholar: {}
    cnki:
      api_key: null  # 可选
      username: null
      password: null

  open_data:
    huggingface: {}
    kaggle:
      username: "your-kaggle-username"
      api_key: "your-kaggle-api-key"

  library_systems:
    university_library:
      type: "opac"
      url: "https://library.university.edu"
      name: "University Library"

# 文本处理配置
processors:
  text_normalization:
    remove_whitespace: true
    remove_punctuation: false
    lowercase: false
    remove_stopwords: false

  language_detection:
    enabled: true
    default_language: "en"
    confidence_threshold: 0.8

  nlp_models:
    zh:
      model: "zh_core_web_sm"
      enabled: true
    fr:
      model: "fr_core_news_sm"
      enabled: true
    en:
      model: "en_core_web_sm"
      enabled: true

# 质量控制配置
quality_control:
  validation:
    quality_thresholds:
      overall: 0.7
      content: 0.6
      metadata: 0.5
      structure: 0.6

    validation_rules:
      title_length:
        min_length: 5
        max_length: 200
      content_length:
        min_length: 50
        max_length: 100000

  cleaning:
    enable_text_cleaning: true
    enable_format_standardization: true
    remove_empty_fields: true

  database_path: "data/quality_control.db"

# 调度器配置
scheduler:
  max_workers: 4
  max_concurrent_tasks: 3
  database_path: "data/scheduler.db"

  monitoring:
    alert_thresholds:
      failure_rate: 0.3
      execution_time: 3600
      queue_size: 10

    notifications:
      enabled: false
      email:
        smtp_server: "smtp.example.com"
        smtp_port: 587
        username: "your-email@example.com"
        password: "your-password"
        recipients: ["admin@example.com"]

# 预定义任务
tasks:
  pubmed_daily:
    name: "PubMed每日更新"
    description: "每日获取最新医学文献"
    task_type: "data_acquisition"
    schedule: "daily_09:00"
    connector_config:
      type: "academic"
      pubmed:
        email: "your-email@example.com"
    parameters:
      query: "machine learning"
      max_results: 100
      databases: ["pubmed"]
    priority: "high"
    enabled: true

  quality_hourly:
    name: "质量检查"
    description: "每小时检查数据质量"
    task_type: "quality_check"
    schedule: "every_1h"
    connector_config:
      validation:
        quality_thresholds:
          overall: 0.7
    parameters:
      limit: 50
    priority: "normal"
    enabled: true
```

## 性能优化建议

### 1. 连接器优化

```python
# 使用连接池和重试机制
connector_config = {
    'rate_limit': {
        'requests_per_second': 2  # 限制请求频率
    },
    'timeout': 30,
    'max_retries': 3
}

# 批量处理
batch_size = 50
for i in range(0, len(queries), batch_size):
    batch_queries = queries[i:i+batch_size]
    results = connector.search_batch(batch_queries)  # 批量搜索
```

### 2. 处理器优化

```python
# 缓存NLP模型
processor = TextProcessor({
    'nlp_models': {
        'en': {'model': 'en_core_web_sm', 'enabled': True}
    },
    'cache_models': True  # 启用模型缓存
})

# 并行处理
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(processor.process, texts))
```

### 3. 质量控制优化

```python
# 增量质量检查
controller = DataQualityController({
    'validation': {
        'incremental_check': True,
        'batch_size': 100
    }
})

# 异步质量评估
import asyncio

async def batch_quality_check(data_batch):
    tasks = [controller.assess_quality_async(data) for data in data_batch]
    results = await asyncio.gather(*tasks)
    return results
```

### 4. 调度器优化

```python
# 智能任务调度
scheduler = TaskScheduler({
    'max_workers': 6,
    'max_concurrent_tasks': 3,
    'load_balancing': True,  # 启用负载均衡
    'priority_queue': True   # 启用优先级队列
})

# 任务依赖管理
dependent_task = ScheduledTask(
    id="dependent_task",
    name: "依赖任务",
    depends_on=["parent_task_id"],  # 依赖任务ID
    # ... 其他配置
)
```

## 故障排除

### 常见问题

1. **API限制错误**
   ```python
   # 解决方案：增加重试和延迟
   connector_config = {
       'rate_limit': {'requests_per_second': 1},
       'retry_strategy': {
           'max_retries': 5,
           'backoff_factor': 2
       }
   }
   ```

2. **NLP模型加载失败**
   ```python
   # 解决方案：检查模型是否已下载
   try:
       import spacy
       nlp = spacy.load('en_core_web_sm')
   except OSError:
       print("请下载spacy模型: python -m spacy download en_core_web_sm")
   ```

3. **内存使用过高**
   ```python
   # 解决方案：使用流式处理
   def process_large_dataset(file_path, batch_size=1000):
       for batch in read_in_batches(file_path, batch_size):
           yield process_batch(batch)
   ```

4. **调度器任务不执行**
   ```python
   # 解决方案：检查调度表达式和任务配置
   task = ScheduledTask(
       schedule="daily_09:00",  # 确保格式正确
       enabled=True,            # 确保任务启用
       # ... 其他配置
   )
   ```

### 日志和调试

```python
import logging

# 启用详细日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 查看特定模块日志
logger = logging.getLogger('src.data.connectors')
logger.setLevel(logging.DEBUG)
```

## 最佳实践

1. **渐进式数据获取**: 先小批量测试，确认质量后再大规模获取
2. **质量优先**: 设置合理的质量阈值，避免低质量数据污染
3. **资源管理**: 合理设置并发数和请求频率，避免被API限制
4. **监控告警**: 设置关键指标监控，及时发现问题
5. **数据备份**: 定期备份获取的数据和元数据
6. **版本控制**: 对数据进行版本管理，支持回滚和比较

## 扩展开发

### 添加新的数据源连接器

```python
from src.data.connectors import BaseConnector

class CustomConnector(BaseConnector):
    def search(self, query: str, max_results: int = 100, **kwargs):
        # 实现自定义搜索逻辑
        pass

    def get_record(self, record_id: str):
        # 实现获取单条记录逻辑
        pass

# 注册到主连接器
academic_connector.connectors['custom'] = CustomConnector(config)
```

### 添加新的质量指标

```python
from src.data.quality_control import QualityMetric

def custom_quality_check(data):
    # 实现自定义质量检查
    score = calculate_custom_score(data)
    return QualityMetric(
        name='custom_metric',
        value=score,
        threshold=0.8,
        passed=score >= 0.8,
        description='自定义质量指标'
    )
```

### 添加新的任务类型

```python
class CustomTaskExecutor:
    def execute(self, task: ScheduledTask):
        if task.task_type == 'custom_processing':
            return self._execute_custom_task(task)
        else:
            raise ValueError(f"不支持的任务类型: {task.task_type}")

    def _execute_custom_task(self, task):
        # 实现自定义任务逻辑
        pass
```

## API参考

详细的API文档请参考各个模块的docstring和类型注解。所有公共类和函数都包含了详细的参数说明和使用示例。

---

**更新时间**: 2025-12-04
**版本**: v1.0.0
**兼容性**: Python 3.10+