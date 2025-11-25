# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KG-CLIR is a multilingual knowledge graph and French learning support system for university library cross-lingual knowledge services. The system builds a trilingual (Chinese-French-English) knowledge graph using the FLO (French Learning Ontology) to enable enhanced cross-lingual information retrieval and adaptive learning support.

**Current Status**: ~25% complete. Core infrastructure and utilities are implemented. Knowledge graph module is partially complete. Cross-lingual alignment, retrieval, and learning modules are under development.

## Development Commands

### Environment Setup

```bash
# Create and activate virtual environment
conda create -n kgclir python=3.10
conda activate kgclir

# Install dependencies
pip install -r requirements.txt

# Download spaCy models (required for entity extraction)
python -m spacy download fr_core_news_sm
python -m spacy download en_core_web_sm
python -m spacy download zh_core_web_sm

# Configure environment
cp .env.example .env
# Edit .env with your API keys and database credentials
```

### Testing

```bash
# Run all tests
pytest tests/

# Run specific test module
pytest tests/test_kg.py -v

# Run with coverage
pytest --cov=src tests/

# Quick smoke test (minimal dependencies)
bash scripts/quick_test.sh
```

### Building and Running

```bash
# Build knowledge graph (demo mode with small dataset)
python -m src.kg.build_kg --config config/kg.yaml --demo

# Build full knowledge graph
python -m src.kg.build_kg --config config/kg.yaml

# Start Neo4j database (Docker)
docker run -d --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/kgclir2024 \
  neo4j:4.4

# Run application (when implemented)
bash scripts/run_app.sh
```

### Development Workflow

```bash
# Add project root to PYTHONPATH (if import issues occur)
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Format code with black
black src/ tests/

# Lint with flake8
flake8 src/ tests/

# Type checking with mypy
mypy src/
```

## Architecture and Structure

### Core System Architecture (5 Layers)

The system follows a layered architecture from bottom to top:

1. **Knowledge Layer** (`src/kg/`): FLO Knowledge Graph construction
   - Entity extraction (spaCy + jieba + regex patterns)
   - Relation extraction (dependency parsing + pattern matching)
   - Knowledge fusion and quality filtering
   - Export to Neo4j/JSON/RDF formats

2. **Alignment Layer** (`src/align/`): Cross-lingual entity alignment
   - MTransE embedding-based alignment
   - GCN-Align refinement using graph neural networks
   - Confidence scoring and validation

3. **Retrieval Layer** (`src/retrieval/`): KG-enhanced CLIR
   - Dense vector index (sentence-transformers)
   - BM25 sparse index (rank-bm25)
   - KG query expansion and joint reranking
   - Formula: `Score = α·Dense + β·BM25 + γ·KG`

4. **Learning Support Layer** (`src/learning/`): Adaptive learning system
   - Learner modeling and knowledge mastery estimation
   - Learning path recommendation using knowledge graph paths
   - RAG-based exercise generation (Claude/GPT APIs)
   - Feedback loop for continuous adaptation

5. **Application Layer** (`src/app/`): User-facing services
   - FastAPI backend with Pydantic schemas
   - Gradio web interface for demos
   - RESTful APIs for retrieval and learning support

### Key Module Responsibilities

**`src/utils/`** - Shared utilities (complete)
- `io.py`: File I/O (JSONL, YAML, TSV)
- `text_norm.py`: Text normalization and stopword removal
- `lang_detect.py`: Language detection (langdetect + pycld2)
- `metrics.py`: Evaluation metrics (nDCG, MRR, Recall@K)
- `stats.py`: Statistical analysis (Cohen's d, significance tests)
- `logger.py`: Structured logging with loguru

**`src/kg/ontology.py`** - Core data model (complete)
- `EntityType`: 17 entity types organized into 4 super-classes (Concept/Activity/Outcome/Resource)
- `RelationType`: 7 core relation types (belongsTo, supports, tests, covers, hasPrereq, translatedAs, sameAs)
- `Entity`: Entity data class with validation
- `Relation`: Relation data class with confidence scores
- `FLOOntology`: Main graph structure with neighbor queries and validation

**`src/kg/extract_entities.py`** - Entity extraction (implemented)
- Multi-strategy extraction: spaCy NER + jieba segmentation + regex patterns
- Language-specific processing for Chinese/French/English
- Entity deduplication and normalization

**`src/kg/extract_relations.py`** - Relation extraction (implemented)
- Dependency parsing patterns
- Regex-based pattern matching
- Co-occurrence statistics

**`src/kg/fuse_kg.py`** - Knowledge fusion (implemented)
- Entity merging with similarity threshold
- Conflict resolution (majority vote / latest / highest confidence)
- Quality filtering by frequency and confidence

**`src/kg/build_kg.py`** - Main KG construction pipeline (implemented)
- `KnowledgeGraphBuilder` orchestrates full workflow
- Processes corpus in batches
- Exports to multiple formats

**`src/kg/export_kg.py`** - Export functions (implemented)
- Neo4j Cypher import with batch processing
- JSON serialization
- RDF Turtle format
- NetworkX fallback if Neo4j unavailable

### Configuration System

All modules use YAML configuration files in `config/`:

- **`kg.yaml`**: Knowledge graph construction (entity types, extraction strategies, Neo4j connection)
- **`align.yaml`**: Cross-lingual alignment parameters (embedding dim, training epochs)
- **`retrieval.yaml`**: Retrieval configuration (index paths, ranking weights α/β/γ)
- **`learning.yaml`**: Learning support settings (difficulty levels, RAG prompts)
- **`app.yaml`**: Application server settings (ports, API keys)

Load configurations using: `from src.utils.io import load_yaml; config = load_yaml("config/kg.yaml")`

### Data Organization

```
data/
├── processed/          # Processed corpus files
│   ├── textbooks_fr.jsonl
│   ├── alignment_seeds.jsonl
│   ├── academic_resources.jsonl
│   └── exercises_fr.jsonl
├── demo/              # Small demo dataset (~1000 samples)
│   └── demo_corpus.jsonl
└── README.md          # Data format documentation

outputs/
├── kg/                # Knowledge graph outputs
│   ├── knowledge_graph.json
│   ├── kg_statistics.json
│   └── kg_visualization.html
├── align/             # Alignment results
├── retrieval/         # Retrieval evaluation results
└── learning/          # Learning experiment results

models/
├── transformers/      # HuggingFace model cache
├── faiss_index/       # FAISS vector indexes
└── huggingface/       # HuggingFace cache
```

### External Dependencies

**Required Services**:
- Neo4j 4.4+ for graph storage (fallback: networkx in-memory graph)
- Elasticsearch 8.10+ for BM25 indexing (fallback: rank-bm25 library)

**Key Python Libraries**:
- PyTorch 2.0.1 with CUDA support (or CPU-only)
- transformers 4.34.0 for multilingual embeddings
- sentence-transformers 2.2.2 for dense retrieval
- torch-geometric 2.4.0 for GCN alignment
- spacy 3.7.2 for NLP (with language models)
- jieba 0.42.1 for Chinese segmentation
- neo4j 5.14.0 for graph database
- faiss-gpu 1.7.4 for vector similarity (or faiss-cpu)
- anthropic 0.7.1 and openai 1.3.7 for RAG

## Important Implementation Details

### Entity and Relation Handling

- **Entity IDs**: Auto-generated as `{type}_{lang}_{uuid}` (e.g., `grammar_fr_abc123`)
- **Deduplication**: Based on `(name.lower(), type, language)` tuple
- **Language Codes**: Strictly validated to `zh`, `fr`, or `en`
- **Confidence Scores**: All relations have confidence ∈ [0.0, 1.0]

### Batch Processing

Large corpus processing uses batches to avoid memory issues:
- Default batch size: 1000 documents (configurable in YAML)
- Neo4j import batch size: 1000 nodes/relationships
- Progress tracking with tqdm progress bars

### Error Handling Strategy

- **Graceful Degradation**: If Neo4j unavailable, fall back to networkx
- **Partial Failures**: Log errors but continue processing remaining items
- **Validation**: Validate inputs early with descriptive error messages
- **Retry Logic**: Database operations retry 3 times with exponential backoff

### Testing Patterns

Tests follow these conventions:
- Test files named `test_*.py` in `tests/` directory
- Use pytest fixtures for shared setup (ontology, sample data)
- Mock external services (Neo4j, APIs) in unit tests
- Integration tests use demo data subset
- Example test: `tests/test_kg.py` covers ontology operations

### Academic Standards

Code includes academic citations in docstrings:
- Algorithm references in module headers
- Evaluation metrics cite original papers (nDCG, MRR)
- Ontology design references Guarino & Welty (2002)
- MTransE alignment cites Chen et al. (2017)
- GCN-Align cites Wang et al. (2018)

## Development Priorities

Per PROJECT_STATUS.md, remaining work (75%) prioritized as:

1. **Complete KG Module** (Phase 3 remaining): Integrate all extraction and fusion components
2. **Implement Alignment** (Phase 4): MTransE and GCN-Align algorithms
3. **Build Retrieval System** (Phase 5): Dense+BM25+KG joint ranking
4. **Learning Support** (Phase 6): RAG exercise generation and learner modeling
5. **Application Layer** (Phase 7): FastAPI backend and Gradio frontend
6. **Scripts & Docs** (Phase 8-9): Deployment scripts and documentation

## Common Pitfalls

- **Import Errors**: Always run from project root with proper PYTHONPATH
- **spaCy Models**: Must download language models before entity extraction
- **Neo4j Auth**: Default password is `kgclir2024` (check .env.example)
- **CUDA/CPU**: Set `DEVICE=cpu` in .env if no GPU available
- **FAISS**: Use `faiss-cpu` instead of `faiss-gpu` if no CUDA

## Key Files for Context

- `README.md`: Full project description and installation guide
- `QUICKSTART.md`: Step-by-step getting started with code examples
- `PROJECT_STATUS.md`: Detailed completion status and next steps
- `construction.md`: Original system design document (if exists)
- `requirements.txt`: Exact dependency versions for reproducibility
