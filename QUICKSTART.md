# KG-CLIR 快速开始指南

## 🚀 5分钟快速体验

### 前置要求
- Python 3.10+
- 稳定的网络连接

### 一键启动
```bash
# 1. 克隆项目
git clone <repository-url>
cd kgclir-french-lib-1

# 2. 一键启动
bash scripts/start_demo.sh
```

启动后访问: http://localhost:8501

## 📦 完整安装

### 1. 环境准备
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows
```

### 2. 安装依赖
```bash
# 基础依赖
pip install -r requirements.txt

# 下载NLP模型
python -m spacy download en_core_web_sm
python -m spacy download zh_core_web_sm
python -m spacy download fr_core_news_sm
```

### 3. 配置环境
```bash
# 复制环境配置
cp .env.example .env

# 编辑配置文件（可选）
nano .env
```

### 4. 启动系统
```bash
# 启动Web界面
bash scripts/run_streamlit.sh

# 或者直接运行
streamlit run src/app/streamlit_ui.py
```

## 🎯 核心功能

### 1. 跨语言检索
- 🔍 支持中文、法语、英语搜索
- 📚 多数据源：学术文献、教材、网络资源
- 🧠 智能排序：语义检索 + BM25 + 知识图谱

### 2. 知识图谱
- 🕸️ 可视化知识网络
- 🔗 实体关系探索
- 📊 统计分析

### 3. 法语学习
- 🎓 智能练习生成
- 📈 学习进度跟踪
- 🎯 个性化推荐

### 4. 数据管理
- 📄 多格式文件上传
- 🌐 网页内容抓取
- 📊 质量控制

## 💡 使用示例

### Python API使用
```python
from src.retrieval.cross_lingual_retriever import CrossLingualRetriever

# 创建检索器
retriever = CrossLingualRetriever()

# 跨语言搜索
results = retriever.search(
    query="机器学习",
    source_lang="zh",
    target_lang="fr",
    max_results=10
)

for result in results:
    print(f"标题: {result.title}")
    print(f"相关度: {result.score:.3f}")
```

### 命令行工具
```bash
# 构建知识图谱
python -m src.kg.build_kg --demo

# 数据获取演示
python scripts/demo_data_acquisition.py

# 运行测试
pytest tests/test_data_acquisition_simple.py
```

## 🔧 常用配置

### 环境变量 (.env)
```bash
# 数据库配置
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=your_password

# API密钥（可选）
OPENAI_API_KEY=your_key
HUGGINGFACE_TOKEN=your_token
```

### 检索权重调整
```python
# config/retrieval.yaml
ranking:
  weights:
    dense: 0.5        # 语义检索
    bm25: 0.3         # 关键词检索
    knowledge_graph: 0.2  # 知识图谱
```

## 🛠️ 故障排除

### 常见问题

**Q: 模块导入错误**
```bash
export PYTHONPATH="${PWD}:${PYTHONPATH}"
```

**Q: 端口被占用**
```bash
streamlit run src/app/streamlit_ui.py --server.port 8502
```

**Q: 内存不足**
```bash
export DEVICE=cpu  # 使用CPU
export BATCH_SIZE=16  # 减少批大小
```

**Q: 模型下载失败**
```bash
# 设置镜像
export HF_ENDPOINT=https://hf-mirror.com
```

### 性能优化
- 使用SSD存储
- 增加内存到8GB+
- 启用GPU加速（可选）
- 使用Redis缓存

## 📚 更多资源

- 📖 [完整系统指南](docs/SYSTEM_GUIDE.md)
- 📊 [数据获取指南](docs/DATA_ACQUISITION_GUIDE.md)
- 🌐 [Streamlit界面指南](docs/STREAMLIT_GUIDE.md)
- 🐛 [问题反馈](https://github.com/your-repo/kgclir/issues)

## 🆘 获取帮助

- 📧 技术支持: support@kgclir.edu
- 💬 在线讨论: [GitHub Discussions](https://github.com/your-repo/kgclir/discussions)
- 📱 微信群: 扫描项目README二维码

---

🎉 开始您的跨语言知识检索之旅！

**版本**: v1.0.0 | **更新**: 2025-12-04