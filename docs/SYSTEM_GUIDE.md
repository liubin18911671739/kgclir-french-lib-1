# KG-CLIR 系统运行指南

## 🎯 系统概述

KG-CLIR (Knowledge Graph Cross-Language Information Retrieval) 是一个面向大学图书馆跨语言知识服务的多语种知识图谱与法语学习支持系统。

**核心功能**:
- 📚 多语种知识图谱构建 (中文-法语-英语)
- 🔍 跨语言信息检索
- 🎓 智能法语学习支持
- 🌐 Web用户界面
- 📊 数据获取与管理

## 🚀 快速启动

### 方式一：一键演示启动（推荐新手）

```bash
# 克隆项目
git clone <repository-url>
cd kgclir-french-lib-1

# 启动演示系统
bash scripts/start_demo.sh
```

这将自动：
- ✅ 检查Python环境和依赖
- ✅ 创建示例数据和配置
- ✅ 启动完整的Streamlit界面
- ✅ 在浏览器中打开 http://localhost:8501

### 方式二：快速安装和运行

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 下载NLP模型
python -m spacy download en_core_web_sm
python -m spacy download zh_core_web_sm
python -m spacy download fr_core_news_sm

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要的API密钥

# 5. 启动Web界面
bash scripts/run_streamlit.sh
```

### 方式三：Docker部署（推荐生产环境）

```bash
# 构建Docker镜像
docker build -t kgclir .

# 运行容器
docker run -p 8501:8501 \
  -e PYTHONPATH=/app \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config:/app/config \
  kgclir
```

## 📋 环境要求

### 系统要求
- **操作系统**: Linux, macOS, Windows 10+
- **Python版本**: 3.10+ (推荐 3.11)
- **内存**: 最少4GB，推荐8GB+
- **存储**: 最少10GB可用空间
- **网络**: 稳定的互联网连接（用于数据获取）

### 必需依赖

#### 核心依赖
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install transformers sentence-transformers
pip install streamlit streamlit-agraph plotly pandas
pip install neo4j faiss-cpu
pip install spacy jieba langdetect
```

#### 数据获取依赖
```bash
pip install requests beautifulsoup4 feedparser
pip install scholarly arxiv
pip install PyPDF2 pdfplumber python-docx openpyxl
pip install schedule  # 任务调度
```

#### 可选依赖
```bash
# 高性能检索（GPU支持）
pip install faiss-gpu

# 数据库连接
pip install psycopg2-binary  # PostgreSQL
pip install pymongo          # MongoDB

# 高级NLP功能
pip install nltk              # 自然语言处理
pip install textblob         # 文本处理
pip install gensim            # 主题建模
```

## ⚙️ 系统配置

### 1. 环境变量配置

编辑 `.env` 文件：

```bash
# 基本配置
PYTHONPATH=/path/to/kgclir
DATA_DIR=./data
OUTPUTS_DIR=./outputs
MODELS_DIR=./models

# 数据库配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j

# API密钥（可选）
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
HUGGINGFACE_TOKEN=your_huggingface_token

# 外部服务（可选）
PUBMED_EMAIL=your-email@example.com
IEEE_API_KEY=your_ieee_api_key
KAGGLE_USERNAME=your_kaggle_username
KAGGLE_API_KEY=your_kaggle_key

# 缓存配置
CACHE_DIR=./cache
REDIS_URL=redis://localhost:6379

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=./logs/kgclir.log
```

### 2. 配置文件

系统的主要配置文件位于 `config/` 目录：

#### 知识图谱配置 (`config/kg.yaml`)
```yaml
knowledge_graph:
  entities:
    types: [Concept, Activity, Outcome, Resource]
  relations:
    types: [belongsTo, supports, tests, covers, hasPrereq, translatedAs, sameAs]

extraction:
  spacy_models:
    zh: "zh_core_web_sm"
    fr: "fr_core_news_sm"
    en: "en_core_web_sm"

neo4j:
  uri: "bolt://localhost:7687"
  batch_size: 1000
```

#### 检索系统配置 (`config/retrieval.yaml`)
```yaml
dense_retrieval:
  model: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
  index_path: "./models/faiss_index"

bm25_retrieval:
  index_path: "./models/bm25_index"

ranking:
  weights:
    dense: 0.4
    bm25: 0.3
    knowledge_graph: 0.3
```

#### 应用配置 (`config/app.yaml`)
```yaml
streamlit:
  title: "KG-CLIR 跨语言知识检索系统"
  layout: "wide"

ui:
  theme: "light"
  language: "zh"
  max_results: 50
```

## 🔧 核心功能使用

### 1. Web界面访问

启动后，在浏览器中访问 http://localhost:8501

**主要页面**：
- 📄 **首页**: 系统介绍和快速入门
- 🔍 **跨语言检索**: 多语言搜索功能
- 📊 **知识图谱**: 可视化知识图谱
- 📚 **数据管理**: 文件上传和管理
- 🎓 **学习支持**: 法语学习工具
- ⚙️ **系统设置**: 配置和参数调整

### 2. 命令行工具

#### 知识图谱构建
```bash
# 构建完整知识图谱
python -m src.kg.build_kg --config config/kg.yaml

# 使用演示数据构建
python -m src.kg.build_kg --config config/kg.yaml --demo

# 指定输入文件
python -m src.kg.build_kg --input data/processed/textbooks_fr.jsonl
```

#### 跨语言对齐
```bash
# 执行跨语言实体对齐
python -m src.align.align_entities --config config/align.yaml

# 使用预训练模型
python -m src.align.align_entities --use_mtrans --config config/align.yaml
```

#### 检索系统
```bash
# 构建检索索引
python -m src.retrieval.build_index --config config/retrieval.yaml

# 评估检索性能
python -m src.retrieval.evaluate --config config/retrieval.yaml --test_data data/test/queries.jsonl
```

#### 数据获取
```bash
# 运行数据获取演示
python scripts/demo_data_acquisition.py

# 启动数据获取调度器
python -m src.data.scheduler --config config/data_acquisition.yaml
```

### 3. API接口

系统提供RESTful API接口：

```python
import requests

# 检索API
response = requests.post("http://localhost:8000/api/search", json={
    "query": "机器学习",
    "language": "zh",
    "target_languages": ["en", "fr"],
    "max_results": 10
})

# 知识图谱查询API
response = requests.get("http://localhost:8000/api/kg/entity", params={
    "entity_id": "concept_ml_001",
    "language": "zh"
})

# 学习支持API
response = requests.post("http://localhost:8000/api/learning/exercise", json={
    "concept": "虚拟式",
    "difficulty": "intermediate",
    "language": "zh"
})
```

## 📊 数据管理

### 数据目录结构

```
data/
├── raw/                    # 原始数据
│   ├── textbooks_fr.jsonl
│   ├── academic_resources.jsonl
│   └── exercises_fr.jsonl
├── processed/              # 处理后数据
├── uploads/               # 用户上传文件
├── demo/                  # 演示数据
└── exports/               # 导出数据

outputs/
├── kg/                    # 知识图谱输出
│   ├── knowledge_graph.json
│   └── kg_statistics.json
├── align/                 # 对齐结果
├── retrieval/             # 检索结果
└── learning/              # 学习数据

models/
├── transformers/          # 预训练模型缓存
├── faiss_index/          # 向量索引
└── huggingface/          # HuggingFace缓存

logs/                     # 日志文件
cache/                    # 缓存目录
```

### 数据导入

#### 批量导入文档
```bash
# 导入JSONL文件
python -m src.app.data_manager --action import --file data/raw/documents.jsonl

# 从URL获取
python -m src.app.data_manager --action fetch_url --url "https://example.com/data.json"

# 处理PDF文件
python -m src.app.data_manager --action process_pdf --file data/raw/document.pdf
```

#### 手动添加数据
```python
from src.app.data_manager import create_data_manager

# 创建数据管理器
data_manager = create_data_manager()

# 添加文档
data_manager.add_document({
    'title': '法语学习指南',
    'content': '...',
    'language': 'zh',
    'authors': ['张三'],
    'keywords': ['法语', '学习']
})
```

## 🔍 使用示例

### 1. 跨语言检索

```python
from src.retrieval.cross_lingual_retriever import CrossLingualRetriever

# 创建检索器
retriever = CrossLingualRetriever(config_path="config/retrieval.yaml")

# 跨语言搜索
results = retriever.search(
    query="机器学习",
    source_lang="zh",
    target_lang="en",
    max_results=10
)

for result in results:
    print(f"Title: {result.title}")
    print(f"Score: {result.score:.3f}")
    print(f"Abstract: {result.abstract[:100]}...")
    print("-" * 50)
```

### 2. 知识图谱查询

```python
from src.kg.ontology import FLOOntology

# 加载知识图谱
ontology = FLOOntology()
ontology.load_from_json("outputs/kg/knowledge_graph.json")

# 查询实体邻居
neighbors = ontology.get_neighbors("concept_ml_001", direction="outgoing")

# 路径查找
path = ontology.find_shortest_path("concept_ml_001", "concept_nn_001")
```

### 3. 学习支持

```python
from src.learning.exercise_generator import ExerciseGenerator

# 创建练习生成器
generator = ExerciseGenerator(config_path="config/learning.yaml")

# 生成练习
exercises = generator.generate_exercises(
    concept="虚拟式",
    difficulty="intermediate",
    count=5,
    exercise_types=["multiple_choice", "fill_blank"]
)

for exercise in exercises:
    print(f"题目: {exercise.question}")
    print(f"选项: {exercise.options}")
    print(f"答案: {exercise.answer}")
    print(f"解释: {exercise.explanation}")
    print()
```

## 🛠️ 故障排除

### 常见问题

#### 1. 导入错误
```bash
# 问题: ModuleNotFoundError: No module named 'src'
# 解决方案: 设置PYTHONPATH
export PYTHONPATH="${PWD}:${PYTHONPATH}"
python your_script.py
```

#### 2. 模型下载失败
```bash
# 问题: spacy或transformers模型下载失败
# 解决方案: 手动下载或使用代理
python -m spacy download en_core_web_sm --user
# 或设置代理
export HF_ENDPOINT=https://hf-mirror.com
```

#### 3. 内存不足
```bash
# 问题: 内存不足错误
# 解决方案: 减少批处理大小
export BATCH_SIZE=32
# 或使用CPU版本模型
export DEVICE=cpu
```

#### 4. 数据库连接失败
```bash
# 问题: Neo4j连接失败
# 解决方案: 检查Neo4j服务
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:4.4
```

#### 5. 端口占用
```bash
# 问题: 端口8501被占用
# 解决方案: 更改端口
streamlit run src/app/streamlit_ui.py --server.port 8502
```

### 性能优化

#### 1. 内存优化
```python
# 配置文件设置
config = {
    'batch_size': 32,          # 减少批大小
    'max_sequence_length': 256, # 限制序列长度
    'use_gradient_checkpointing': True
}
```

#### 2. 检索优化
```python
# 使用近似搜索
retriever = CrossLingualRetriever(
    use_faiss=True,            # 启用FAISS近似搜索
    faiss_index_type="IVF",    # 使用IVF索引
    nlist=100,                 # 索引参数
    nprobe=10                  # 搜索参数
)
```

#### 3. 缓存配置
```python
# 启用Redis缓存
import redis
cache = redis.Redis(host='localhost', port=6379, db=0)

# 使用内存缓存
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_function(query):
    return expensive_operation(query)
```

## 📈 监控和维护

### 日志查看

```bash
# 查看应用日志
tail -f logs/kgclir.log

# 查看Streamlit日志
tail -f logs/streamlit.log

# 查看错误日志
grep ERROR logs/kgclir.log
```

### 系统监控

```python
# 内置监控工具
from src.utils.monitoring import SystemMonitor

monitor = SystemMonitor()

# 获取系统状态
status = monitor.get_system_status()
print(f"CPU使用率: {status['cpu_usage']}%")
print(f"内存使用率: {status['memory_usage']}%")
print(f"活跃连接数: {status['active_connections']}")
```

### 数据备份

```bash
# 备份数据库
python scripts/backup_neo4j.sh --output backup/neo4j_$(date +%Y%m%d).dump

# 备份配置文件
tar -czf backup/config_$(date +%Y%m%d).tar.gz config/

# 备份模型
rsync -av models/ backup/models_$(date +%Y%m%d)/
```

## 🔒 安全注意事项

### 1. API密钥管理
```bash
# 使用环境变量存储敏感信息
export OPENAI_API_KEY="your_key_here"

# 或使用密钥管理服务
export HUGGINGFACE_HUB_TOKEN="your_token_here"
```

### 2. 数据隐私
```python
# 启用数据匿名化
config = {
    'anonymize_personal_data': True,
    'retain_ip_addresses': False,
    'data_retention_days': 365
}
```

### 3. 访问控制
```bash
# 设置访问控制
export STREAMLIT_SERVER_ENABLE_CORS=false
export STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true
```

## 🤝 获取帮助

### 技术支持
- 📧 **邮箱**: support@kgclir.edu
- 🐛 **问题反馈**: [GitHub Issues](https://github.com/your-repo/kgclir/issues)
- 📚 **文档**: [项目文档](https://kgclir-docs.example.com)

### 社区交流
- 💬 **讨论组**: [GitHub Discussions](https://github.com/your-repo/kgclir/discussions)
- 🐦 **Twitter**: [@KG_CLIR](https://twitter.com/KG_CLIR)
- 📱 **微信群**: 扫描二维码加入

### 学习资源
- 📖 **用户手册**: [详细文档](docs/USER_MANUAL.md)
- 🎓 **教程视频**: [Bilibili频道](https://space.bilibili.com/kgclir)
- 📝 **博客文章**: [技术博客](https://blog.kgclir.edu)

---

**更新时间**: 2025-12-04
**版本**: v1.0.0
**维护团队**: KG-CLIR 开发组

祝您使用愉快！🎉