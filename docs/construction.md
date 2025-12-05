
你是一位资深的科研工程师 + 图书情报学/跨语言信息检索专家。

请在当前 VSCode 工作区生成一个**可复现、模块化、符合学术规范**的完整项目，用于论文《面向大学图书馆跨语言知识服务的多语种知识图谱与法语学习支持系统研究》的实验代码实现。

## 📋 项目背景（Academic Context）
 
**研究问题**：大学图书馆如何通过多语种知识图谱（mKG）+ 图谱增强跨语言检索（KG-CLIR）+ 学习分析，实现面向法语学习者的跨语言知识服务？

**核心贡献**：
1. 构建法语学习领域的中法英三语知识图谱（FLO Ontology）
2. 提出知识图谱增强的跨语言检索方法（Dense + BM25 + KG联合排序）
3. 实现"检索-学习-反馈"闭环的自适应学习支持

**技术栈要求**：
- Python 3.10 + PyTorch 2.0.1（CUDA 11.8）
- Neo4j 4.4（图数据库）+ ElasticSearch 8.5（检索引擎）
- Transformers 4.34.0 + Sentence-Transformers 2.2.2 + FAISS-GPU 1.7.4
- FastAPI 0.103.1 + Gradio 4.4.0（应用层）

**学术规范要求**：
- 代码必须包含完整的Docstrings（Google Style）
- 关键算法需注明参考文献（如MTransE、GCN-Align等）
- 实验脚本需支持完整可复现（固定随机种子、环境导出）
- 输出结果需符合论文表格格式（JSON/CSV统计数据）

---

## 🏗️ 项目结构（严格按此生成）

```plaintext
kgclir-french-lib/
├── README.md                          # 学术项目说明（含引用格式）
├── requirements.txt                   # 精确版本依赖（可复现）
├── setup.py                           # 安装脚本
├── .env.example                       # 环境变量模板
├── config/                            # 配置文件（YAML格式）
│   ├── kg.yaml                        # 知识图谱构建配置
│   ├── align.yaml                     # 跨语言对齐配置
│   ├── retrieval.yaml                 # 检索实验配置
│   ├── learning.yaml                  # 学习支持配置
│   └── app.yaml                       # 应用服务配置
├── data/                              # 数据目录
│   ├── raw/                           # 原始语料（HuggingFace下载）
│   ├── processed/                     # 预处理后语料（JSONL格式）
│   ├── seeds/                         # 人工对齐种子（TSV格式）
│   ├── qrels/                         # 检索标注数据（TREC格式）
│   └── demo/                          # 小规模演示数据
├── models/                            # 模型缓存目录
├── outputs/                           # 实验输出目录
│   ├── kg/                            # 知识图谱构建输出
│   ├── alignment/                     # 对齐结果
│   ├── retrieval/                     # 检索评测结果
│   └── learning/                      # 学习评估结果
├── src/                               # 源代码目录
│   ├── __init__.py
│   ├── utils/                         # 工具模块
│   │   ├── __init__.py
│   │   ├── io.py                      # 文件读写
│   │   ├── text_norm.py               # 文本规范化
│   │   ├── lang_detect.py             # 语言检测
│   │   ├── metrics.py                 # 评价指标
│   │   ├── stats.py                   # 统计分析
│   │   └── logger.py                  # 日志系统
│   ├── kg/                            # 知识图谱模块
│   │   ├── __init__.py
│   │   ├── ontology.py                # FLO本体定义（dataclass + Enum）
│   │   ├── build_kg.py                # 图谱构建主流程
│   │   ├── extract_entities.py        # 实体抽取（spaCy + jieba + 规则）
│   │   ├── extract_relations.py       # 关系抽取（模式匹配 + 依存句法）
│   │   ├── fuse_kg.py                 # 知识融合（去重 + 冲突解决）
│   │   └── export_kg.py               # 导出（JSON + RDF + Neo4j）
│   ├── align/                         # 跨语言对齐模块
│   │   ├── __init__.py
│   │   ├── mtranse_align.py           # MTransE算法（引用：Chen et al., IJCAI 2017）
│   │   ├── gcn_align.py               # GCN-Align算法（引用：Wang et al., EMNLP 2018）
│   │   ├── align_pipeline.py          # 对齐流水线（两阶段）
│   │   └── evaluate_align.py          # 对齐评测（Precision@k, Recall@k, F1@k）
│   ├── retrieval/                     # 检索模块
│   │   ├── __init__.py
│   │   ├── bm25_index.py              # BM25索引（ElasticSearch + rank-bm25降级）
│   │   ├── dense_index.py             # 密集向量索引（FAISS-GPU）
│   │   ├── kg_expansion.py            # 知识图谱查询扩展（n-hop邻域）
│   │   ├── kg_rerank.py               # 联合重排序（α·dense + β·BM25 + γ·KG）
│   │   ├── kg_clir.py                 # KG-CLIR主流程
│   │   └── evaluate_clir.py           # 检索评测（nDCG@10, MRR, Recall@50）
│   ├── learning/                      # 学习支持模块
│   │   ├── __init__.py
│   │   ├── learner_model.py           # 学习者建模（知识掌握度估计）
│   │   ├── path_recommend.py          # 学习路径推荐（基于KG先修关系）
│   │   ├── rag_exercise.py            # RAG练习生成（Claude/GPT + 知识证据）
│   │   ├── feedback_loop.py           # 学习反馈闭环
│   │   └── evaluate_learning.py       # 学习效果评估（对照实验 + t-test）
│   └── app/                           # 应用层
│       ├── __init__.py
│       ├── api.py                     # FastAPI后端（4个核心接口）
│       ├── gradio_ui.py               # Gradio前端
│       └── schemas.py                 # Pydantic数据模型
├── scripts/                           # 脚本目录
│   ├── prepare_corpus.py              # 数据准备（HuggingFace下载 + 预处理）
│   ├── validate_corpus.py             # 数据质量验证
│   ├── check_environment.py           # 环境检查（10项验证清单）
│   ├── run_build_kg.sh                # 知识图谱构建脚本
│   ├── run_align.sh                   # 跨语言对齐脚本
│   ├── run_index.sh                   # 索引构建脚本
│   ├── run_eval_clir.sh               # 检索评测脚本
│   ├── run_app.sh                     # 应用启动脚本
│   └── run_full_experiment.sh         # 完整实验流程（6步）
├── tests/                             # 单元测试（pytest）
│   ├── __init__.py
│   ├── test_kg.py
│   ├── test_align.py
│   ├── test_retrieval.py
│   └── test_learning.py
├── notebooks/                         # Jupyter分析笔记本
│   ├── 01_data_exploration.ipynb
│   ├── 02_kg_visualization.ipynb
│   └── 03_result_analysis.ipynb
├── docker/                            # Docker部署
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .dockerignore
└── docs/                              # 文档目录
    ├── API.md                         # API文档
    ├── REPRODUCIBILITY.md             # 可复现指南
    └── CITATION.bib                   # BibTeX引用

```

---

## 📐 核心模块实现要求（Critical Requirements）

### 1. FLO本体定义 (src/kg/ontology.py)

**要求**：

- 使用Python `dataclass` + `Enum` 定义本体类和关系类型
- 包含17种实体类型（Word/Grammar/Pragmatics/Culture/Topic/Exercise/Task/Test/Outcome/Textbook/Reference/Article/Media/LexCorpus/Course/Level/CEFR_Skill）
- 包含7种核心关系（belongsTo/supports/tests/covers/hasPrereq/translatedAs/sameAs）
- 实现`FLOOntology`管理器类：
    - `add_entity()` / `add_relation()`（含一致性检查）
    - `get_neighbors(entity_id, relation_type)`（n-hop查询）
    - `validate_schema()`（孤立节点检测 + 语言覆盖度统计）
    - `export_statistics()`（输出论文表格数据：实体数/关系数/平均度数等）

**学术注释示例**：

```python
"""
FLO (French Learning Ontology) 本体定义

理论基础：
- 领域建模：Guarino & Welty (2002) OntoClean方法论
- 多语种对齐：Multilingual Ontology文献（Espinoza et al., 2009）

本体设计原则：
1. 类型层次：Concept/Activity/Resource/Context四大超类
2. 关系语义：遵循OWL-DL可判定性约束
3. 扩展性：支持CEFR标准扩展（A1-C2分级）
"""

```

---

### 2. 实体抽取模块 (src/kg/extract_entities.py)

**要求**：

- 混合策略：规则（正则表达式）+ NLP模型（spaCy + jieba）
- 支持中法英三语处理：
    - 中文：jieba分词 + 词性标注（保留名词/动词，≥2字）
    - 法语/英语：spaCy NER + 依存句法（保留NOUN/VERB/ADJ，≥3字符）
- 实体规范化：lemmatization（法英）/ 去停用词
- 去重策略：基于(name.lower(), entity_type, language)三元组

**关键方法**：

```python
def extract_from_text(text: str, language: str) -> List[Entity]:
    """
    Args:
        text: 输入文本
        language: zh/fr/en

    Returns:
        去重后的实体列表

    学术注意：
    - 混合策略提升召回率（rule: 精确率高；NLP: 召回率高）
    - 参考：Named Entity Recognition in Low-Resource Languages (ACL 2020)
    """

```

---

### 3. 跨语言对齐模块 (src/align/)

**关键文件**：

### 3.1 MTransE算法 (mtranse_align.py)

**要求**：

- 实现TransE的多语言扩展版本（不依赖OpenKE）
- 输入：中法英三个子图 + 人工种子对齐（data/seeds/align_seeds.tsv）
- 训练：
    - 损失函数：margin-based ranking loss
    - 优化器：Adam（lr=0.001）
    - 训练轮次：1000 epochs
- 输出：对齐候选对 + 置信度（Top-k=100，阈值>0.8保留）

**学术引用**：

```python
"""
MTransE: Multilingual Knowledge Graph Embeddings for Cross-lingual Knowledge Alignment

Reference:
Chen, M., Tian, Y., Yang, M., & Zaniolo, C. (2017).
Multilingual knowledge graph embeddings for cross-lingual knowledge alignment.
In Proceedings of IJCAI (pp. 1511-1517).

算法核心：
1. 每个语言的实体嵌入到d维向量空间
2. 学习语言间的线性变换矩阵
3. 通过向量空间对齐实现跨语言实体匹配
"""

```

### 3.2 GCN-Align算法 (gcn_align.py)

**要求**：

- 使用PyTorch Geometric实现图卷积对齐网络
- 输入：MTransE初始对齐 + 子图邻接矩阵
- 架构：2层GCN（hidden_dim=256）+ 余弦相似度
- 训练：对比损失（positive pairs vs. hard negatives）
- 输出：重排序后的对齐结果

**学术引用**：

```python
"""
GCN-Align: Cross-lingual Knowledge Graph Alignment via Graph Convolutional Networks

Reference:
Wang, Z., Lv, Q., Lan, X., & Zhang, Y. (2018).
Cross-lingual knowledge graph alignment via graph convolutional networks.
In Proceedings of EMNLP (pp. 349-357).

创新点：
1. 利用图结构邻域信息校正MTransE初始对齐
2. 端到端训练，无需手工特征工程
"""

```

---

### 4. KG-CLIR检索模块 (src/retrieval/)

**核心流程**：

### 4.1 联合排序函数 (kg_rerank.py)

**要求**：

```python
def compute_score(query: str, doc: Dict, kg: FLOOntology) -> float:
    """
    联合排序函数（论文核心贡献）

    Formula:
        Score(d, q) = α · sim_dense(d, q) + β · score_BM25(d, q) + γ · score_KG(d, q)

    其中：
    - sim_dense: 多语言向量模型（LaBSE/mMiniLM）余弦相似度
    - score_BM25: ElasticSearch BM25得分
    - score_KG: 基于知识图谱的语义得分：
        score_KG = Σ path_score(q, d) / (1 + path_length)
        考虑因素：路径长度、关系类型权重、对齐置信度

    超参数（通过验证集优化）：
    - α = 0.4 (dense权重)
    - β = 0.3 (BM25权重)
    - γ = 0.3 (KG权重)

    学术意义：
    - 融合稀疏（BM25）、稠密（向量）、结构（KG）三种信号
    - KG提供可解释性（返回知识路径作为解释）
    """

```

### 4.2 评测脚本 (evaluate_clir.py)

**要求**：

- 指标：nDCG@10, MRR, Recall@50, Precision@10
- 显著性检验：Bootstrap抽样（n=1000）+ t-test（p<0.05）
- 输出格式：

```json
{
  "method": "KG-CLIR",
  "metrics": {
    "nDCG@10": 0.589,
    "MRR": 0.521,
    "Recall@50": 0.832
  },
  "significance_test": {
    "baseline": "Dense+BM25",
    "p_value": 0.012,
    "effect_size": 0.097
  }
}

```

---

### 5. 学习支持模块 (src/learning/)

### 5.1 知识掌握度模型 (learner_model.py)

**要求**：

```python
def estimate_mastery(concept_id: str, user_id: str) -> float:
    """
    知识掌握度估计

    Formula:
        M(c) = n_c / N_c * w1 + coverage_rate(c) * w2

    其中：
    - n_c: 用户在概念c上做对的练习题数
    - N_c: 概念c的总练习题数
    - coverage_rate: 用户已学习的前置概念覆盖率
    - w1=0.7, w2=0.3（权重）

    返回值：0-1范围，表示掌握程度

    学术依据：
    - 知识追踪模型（Knowledge Tracing）
    - 参考：Bayesian Knowledge Tracing (Corbett & Anderson, 1995)
    """

```

### 5.2 RAG练习生成 (rag_exercise.py)

**要求**：

```python
def generate_exercise(concept: str, kg: FLOOntology, llm_client) -> Dict:
    """
    检索增强生成练习题

    Pipeline:
    1. 从KG检索concept的相关知识片段（支撑证据）
    2. 构造Prompt：
       "基于以下知识内容，生成一道关于{concept}的选择题：
        知识内容：{retrieved_evidence}
        要求：题目用法语，解析用中文，难度适合{user_level}"
    3. 调用LLM（Claude/GPT-3.5-turbo）生成
    4. 解析返回结果（question/options/answer/explanation）

    防幻觉策略：
    - 强制引用检索到的证据
    - 后验一致性检查（答案是否在证据中可验证）

    学术价值：
    - RAG范式：Retrieval-Augmented Generation (Lewis et al., NeurIPS 2020)
    - 教育应用：减少LLM幻觉，提升内容可信度
    """

```

---

### 6. 应用层 (src/app/)

### 6.1 FastAPI后端 (api.py)

**要求**：

- 4个核心接口：

```python
@app.post("/search")
async def search(request: QueryRequest) -> SearchResponse:
    """
    跨语言检索接口

    Input:
        {
          "query": "法语虚拟式用法",
          "language": "zh",
          "top_k": 10
        }

    Output:
        {
          "results": [
            {
              "doc_id": "article_123",
              "title": "Le subjonctif en français",
              "score": 0.89,
              "language": "fr",
              "explanation": {
                "kg_path": "虚拟式 -> translatedAs -> subjonctif -> belongsTo -> Grammaire",
                "path_score": 0.32
              }
            }
          ],
          "query_expansion": ["subjonctif", "conditionnel"]
        }
    """

@app.get("/health")
async def health_check():
    """健康检查（验证Neo4j、ES连接）"""

@app.post("/recommend")
async def recommend_learning_path(user_id: str, target_concept: str):
    """学习路径推荐"""

@app.post("/exercise")
async def generate_exercise(concept: str, user_level: str):
    """生成练习题"""

```

### 6.2 Gradio前端 (gradio_ui.py)

**要求**：

- 三个Tab页：
    1. **检索界面**：查询框 + 语言选择 + 结果展示（含知识路径可视化）
    2. **学习路径**：输入目标概念 → 显示推荐路径（DAG图）
    3. **练习生成**：选择概念 → 生成题目 → 提交答案 → 查看解析

---

## 🔧 配置文件示例

### config/kg.yaml

```yaml
# 知识图谱构建配置
ontology:
  version: "1.0"
  base_uri: "http://kgclir.org/flo/"

data_sources:
  textbooks:
    path: "data/processed/textbooks_fr.jsonl"
  parallel_corpus:
    path: "data/processed/alignment_seeds.jsonl"
  academic:
    path: "data/processed/academic_resources.jsonl"
  exercises:
    path: "data/processed/exercises_fr.jsonl"

entity_extraction:
  methods:
    spacy:
      enabled: true
      models:
        fr: "fr_core_news_sm"
        en: "en_core_web_sm"
        zh: "zh_core_web_sm"
    rules:
      enabled: true
      patterns:
        - name: "course_pattern"
          regex: "(?i)chapitre|leçon|unité\\s+\\d+"

neo4j:
  uri: "bolt://localhost:7687"
  auth:
    username: "neo4j"
    password: "kgclir2024"
  database: "kgclir"

output:
  formats: ["json", "rdf", "neo4j"]
  paths:
    json: "outputs/kg/knowledge_graph.json"
    statistics: "outputs/kg/kg_statistics.json"

```

### config/retrieval.yaml

```yaml
# 检索实验配置
dense_model:
  name: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
  device: "cuda"
  max_seq_length: 128

bm25:
  elasticsearch:
    host: "localhost"
    port: 9200
  fallback: "rank-bm25"  # ES不可用时降级

kg_expansion:
  max_hops: 2
  relation_types: ["translatedAs", "sameAs", "belongsTo"]

reranking:
  alpha: 0.4  # dense weight
  beta: 0.3   # BM25 weight
  gamma: 0.3  # KG weight

evaluation:
  qrels_path: "data/qrels/test.qrels"
  metrics: ["nDCG@10", "MRR", "Recall@50"]
  output_path: "outputs/retrieval/clir_results.json"

```

---

## 🚀 实验脚本示例

### scripts/run_full_experiment.sh

```bash
#!/bin/bash
# 完整实验流程（6步）

set -e  # 遇到错误立即退出

echo "========== Step 1: 环境检查 =========="
python scripts/check_environment.py || exit 1

echo "========== Step 2: 数据准备 =========="
python scripts/prepare_corpus.py

echo "========== Step 3: 知识图谱构建 =========="
python -m src.kg.build_kg --config config/kg.yaml

echo "========== Step 4: 跨语言对齐 =========="
python -m src.align.align_pipeline --config config/align.yaml

echo "========== Step 5: 索引构建 =========="
bash scripts/run_index.sh

echo "========== Step 6: 检索评测 =========="
python -m src.retrieval.evaluate_clir --config config/retrieval.yaml

echo "========== Step 7: 学习支持评估 =========="
python -m src.learning.evaluate_learning --config config/learning.yaml

echo "========== 实验完成！结果位于 outputs/ 目录 =========="

```

---

## 📊 输出要求（Output Specifications）

### 1. 知识图谱统计 (outputs/kg/kg_statistics.json)

```json
{
  "ontology_version": "1.0",
  "total_entities": 28230,
  "total_relations": 246600,
  "entities_by_type": {
    "Word": 12500,
    "Grammar": 450,
    "Topic": 2300,
    "Course": 42,
    "Resource": 14440
  },
  "entities_by_language": {
    "zh": 9850,
    "fr": 10420,
    "en": 7960
  },
  "relations_by_type": {
    "belongsTo": 45000,
    "translatedAs": 18500,
    "sameAs": 15600
  },
  "avg_degree": 17.47,
  "construction_time_seconds": 3245
}

```

### 2. 检索评测结果 (outputs/retrieval/clir_results.json)

```json
{
  "experiment_id": "exp_20250126_001",
  "methods": [
    {
      "name": "Translate+BM25",
      "metrics": {
        "nDCG@10": 0.412,
        "MRR": 0.361,
        "Recall@50": 0.684
      }
    },
    {
      "name": "Dense Only",
      "metrics": {
        "nDCG@10": 0.503,
        "MRR": 0.447,
        "Recall@50": 0.742
      }
    },
    {
      "name": "Dense+BM25",
      "metrics": {
        "nDCG@10": 0.537,
        "MRR": 0.472,
        "Recall@50": 0.781
      }
    },
    {
      "name": "KG-CLIR (Ours)",
      "metrics": {
        "nDCG@10": 0.589,
        "MRR": 0.521,
        "Recall@50": 0.832
      },
      "improvements_over_baseline": {
        "nDCG@10": "+9.7%",
        "MRR": "+10.4%",
        "Recall@50": "+6.5%"
      },
      "significance_test": {
        "baseline": "Dense+BM25",
        "method": "paired t-test",
        "p_value": 0.018,
        "significant": true
      }
    }
  ]
}

```

---

## ✅ 代码质量要求（Quality Checklist）

1. **Docstrings**：所有类和函数必须包含Google Style文档字符串
2. **Type Hints**：所有函数签名必须包含类型注解
3. **Logging**：使用Python logging模块（DEBUG/INFO/WARNING/ERROR级别）
4. **Error Handling**：关键操作必须有try-except + 降级策略
5. **可复现性**：
    - 固定随机种子（`random.seed(42)`, `torch.manual_seed(42)`）
    - 导出conda环境（`conda env export > environment.yml`）
    - 记录系统信息（`outputs/system_info.json`）
6. **测试覆盖**：每个模块至少包含1个单元测试（pytest）
7. **学术规范**：
    - 关键算法注明参考文献
    - 评测结果包含显著性检验
    - 输出格式符合论文表格要求

---

## 🎯 生成指令（执行步骤）

**请按以下顺序逐步生成代码**：

1. **Phase 1: 基础设施**（20分钟）
    - 生成项目结构（所有目录和空文件）
    - 生成 requirements.txt + setup.py + README.md
    - 生成所有配置文件（config/*.yaml）
2. **Phase 2: 工具模块**（15分钟）
    - src/utils/ 下所有工具函数
3. **Phase 3: 知识图谱模块**（40分钟）
    - src/kg/ontology.py（完整本体定义）
    - src/kg/extract_entities.py（实体抽取）
    - src/kg/extract_relations.py（关系抽取）
    - src/kg/fuse_kg.py（知识融合）
    - src/kg/build_kg.py（主流程）
    - src/kg/export_kg.py（导出）
4. **Phase 4: 跨语言对齐模块**（30分钟）
    - src/align/mtranse_align.py（MTransE算法）
    - src/align/gcn_align.py（GCN-Align算法）
    - src/align/align_pipeline.py（两阶段流水线）
    - src/align/evaluate_align.py（评测）
5. **Phase 5: 检索模块**（35分钟）
    - src/retrieval/bm25_index.py
    - src/retrieval/dense_index.py
    - src/retrieval/kg_expansion.py
    - src/retrieval/kg_rerank.py（核心联合排序）
    - src/retrieval/kg_clir.py（主流程）
    - src/retrieval/evaluate_clir.py（评测）
6. **Phase 6: 学习支持模块**（25分钟）
    - src/learning/learner_model.py
    - src/learning/path_recommend.py
    - src/learning/rag_exercise.py
    - src/learning/evaluate_learning.py
7. **Phase 7: 应用层**（20分钟）
    - src/app/schemas.py（Pydantic模型）
    - src/app/api.py（FastAPI后端）
    - src/app/gradio_ui.py（Gradio前端）
8. **Phase 8: 脚本与测试**（20分钟）
    - scripts/ 下所有脚本
    - tests/ 下所有测试文件
9. **Phase 9: 文档与部署**（15分钟）
    - docs/REPRODUCIBILITY.md
    - docker/Dockerfile + docker-compose.yml
    - notebooks/ 三个分析笔记本

---

## 💡 特殊注意事项（Critical Notes）

1. **不要使用外部OpenKE库**：MTransE算法需自行实现简化版
2. **FAISS-GPU版本**：必须使用`faiss-gpu`而非`faiss-cpu`
3. **Neo4j连接**：提供降级策略（无法连接时使用networkx内存图）
4. **ElasticSearch降级**：无法连接时使用`rank-bm25`本地BM25
5. **LLM API调用**：
    - 优先使用Claude（ANTHROPIC_API_KEY环境变量）
    - 降级使用OpenAI（OPENAI_API_KEY环境变量）
    - 无API key时禁用RAG功能但不报错
6. **spaCy模型**：生成下载检查逻辑，模型未安装时给出友好提示
7. **随机种子固定**：所有实验必须在脚本开头设置
    
    ```python
    import randomimport numpy as npimport torchrandom.seed(42)np.random.seed(42)torch.manual_seed(42)if torch.cuda.is_available():    torch.cuda.manual_seed_all(42)
    
    ```
    

---

## 📚 学术规范模板

### Docstring示例

```python
def align_entities(
    source_kg: FLOOntology,
    target_kg: FLOOntology,
    seed_alignments: List[Tuple[str, str]],
    method: str = "mtranse"
) -> List[Tuple[str, str, float]]:
    """
    跨语言实体对齐

    Args:
        source_kg: 源语言知识图谱
        target_kg: 目标语言知识图谱
        seed_alignments: 人工标注的种子对齐对 [(src_id, tgt_id), ...]
        method: 对齐方法 ("mtranse" | "gcn" | "hybrid")

    Returns:
        对齐结果列表 [(src_id, tgt_id, confidence), ...]
        按置信度降序排列

    学术背景：
        本方法结合嵌入映射（MTransE）和图卷积网络（GCN-Align）
        进行两阶段跨语言实体对齐：
        1. MTransE快速扩展种子对齐（高召回率）
        2. GCN利用结构信息精化对齐（高精确率）

    参考文献：
        - Chen et al. (2017). MTransE. IJCAI.
        - Wang et al. (2018). GCN-Align. EMNLP.

    实验注意：
        - 种子对齐数量建议≥500对以保证训练效果
        - 输出结果需经人工抽样验证（建议验证Top-100）

    时间复杂度：
        O(|E_src| × d + |E_tgt| × d + k × |E_src| × |E_tgt|)
        其中d为嵌入维度，k为GCN层数
    """

```

### 评测输出注释

```python
# 学术写作提示：
# 以下评测结果可直接用于论文表格，格式符合ACM/IEEE规范
#
# 表X：跨语言检索性能对比（300条查询，中法英混合）
# | Method         | nDCG@10 | MRR   | R@50  | 显著性 |
# |----------------|---------|-------|-------|-------|
# | Translate+BM25 | 0.412   | 0.361 | 0.684 | —     |
# | Dense Only     | 0.503   | 0.447 | 0.742 | *     |
# | Dense+BM25     | 0.537   | 0.472 | 0.781 | **    |
# | KG-CLIR (Ours) | 0.589   | 0.521 | 0.832 | **    |
#
# 注：* p<0.05, ** p<0.01 (paired t-test vs. Translate+BM25)

```

---

## 🎓 学术论文对应关系（Paper-Code Mapping）

| 论文章节 | 对应代码模块 | 输出文件 |
| --- | --- | --- |
| 4.1 FLO本体设计 | `src/kg/ontology.py` | `outputs/kg/ontology_diagram.png` |
| 4.2 知识图谱构建 | `src/kg/build_kg.py` | `outputs/kg/kg_statistics.json` |
| 4.3 跨语言对齐 | `src/align/` | `outputs/alignment/align_results.json` |
| 5.2 多阶段检索策略 | `src/retrieval/kg_clir.py` | 代码注释中的公式 |
| 表2：检索性能对比 | `outputs/retrieval/clir_results.json` | 直接作为表格数据 |
| 表4：学习效果评估 | `outputs/learning/learning_results.csv` | 转换为LaTeX表格 |
| 附录A：环境配置 | `README.md` + `requirements.txt` | 实验可复现说明 |

---

## 📝 生成后验证清单（Post-Generation Checklist）

生成完成后，请确认以下10项：

- [ ]  1. 所有Python文件包含`__init__.py`和import语句
- [ ]  2. 关键算法包含学术引用注释
- [ ]  3. 配置文件格式正确（YAML语法无误）
- [ ]  4. 所有脚本包含shebang（`#!/bin/bash`）和执行权限
- [ ]  5. README.md包含BibTeX引用格式
- [ ]  6. requirements.txt版本号精确（使用==而非>=）
- [ ]  7. 评测脚本输出JSON格式（可直接转LaTeX表格）
- [ ]  8. 环境检查脚本包含10项验证（GPU/CUDA/FAISS/Neo4j/ES/spaCy等）
- [ ]  9. Docker配置包含所有服务（Neo4j/ES/API/Gradio）
- [ ]  10. 文档包含可复现指南（详细步骤 + 预期耗时）

---

## 🏁 最终输出（Final Deliverable）

执行完毕后，您将获得：

1. **完整代码库**：约15,000行Python代码 + 配置文件
2. **实验脚本**：一键运行完整实验（`bash scripts/run_full_experiment.sh`）
3. **学术文档**：
    - README.md（项目说明 + BibTeX引用）
    - docs/REPRODUCIBILITY.md（可复现指南）
    - docs/API.md（接口文档）
4. **Docker镜像**：可直接部署的容器化方案
5. **单元测试**：pytest可执行的测试套件

---

**现在，请开始按Phase 1-9的顺序逐步生成所有代码！**

如遇到任何不确定的地方，请：

1. 优先参考本提示词中的学术引用和公式
2. 添加TODO注释标记需要后续完善的部分
3. 确保代码语法正确、可运行（即使功能未完全实现）
