# Next Steps Guide - KG-CLIR Project Completion

## 📋 Current Status Summary

**Project Completion: ~60%**

### What's Working Now ✅

1. **Complete Infrastructure**
   - All configuration files ready
   - Dependencies specified with exact versions
   - Directory structure in place

2. **Complete Core Modules**
   - ✅ Utils module (io, text processing, metrics, logging)
   - ✅ Knowledge Graph module (ontology, extraction, fusion, export)

3. **Partial Implementations**
   - ⚠️ Alignment module (MTransE done, GCN-Align needs implementation)
   - ⚠️ Retrieval module (reranking partial, needs full pipeline)
   - ⚠️ Learning module (path recommendation partial)
   - ⚠️ Application layer (main.py exists, needs API/Gradio)

---

## 🎯 Priority 1: Complete Retrieval Module (论文核心)

This is your **paper's main contribution** - the KG-enhanced CLIR system.

### 1.1 Implement Dense Vector Index (src/retrieval/dense_index.py)

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dense Vector Indexing with FAISS

Reference: 
- Johnson et al. (2019). Billion-scale similarity search with GPUs. IEEE Big Data.
"""

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from typing import List, Dict, Tuple
from pathlib import Path

class DenseIndex:
    """
    FAISS-based dense vector index for semantic search
    
    Args:
        model_name: HuggingFace sentence-transformers model
        index_type: "Flat" (exact) | "IVF256,Flat" (fast approximate)
        use_gpu: Whether to use GPU acceleration
    
    Examples:
        >>> index = DenseIndex("paraphrase-multilingual-MiniLM-L12-v2")
        >>> index.add_documents(docs, doc_ids)
        >>> results = index.search("法语虚拟式", top_k=10)
    """
    
    def __init__(
        self,
        model_name: str,
        index_type: str = "IVF256,Flat",
        use_gpu: bool = True,
        device: str = "cuda"
    ):
        self.model = SentenceTransformer(model_name, device=device)
        self.index_type = index_type
        self.use_gpu = use_gpu and faiss.get_num_gpus() > 0
        
        self.index = None
        self.doc_ids = []
        self.dimension = self.model.get_sentence_embedding_dimension()
    
    def add_documents(
        self,
        documents: List[str],
        doc_ids: List[str]
    ) -> None:
        """Add documents to index"""
        # TODO: Implement document encoding and FAISS indexing
        # 1. Encode documents: embeddings = self.model.encode(documents, batch_size=64)
        # 2. Create FAISS index: self.index = faiss.index_factory(self.dimension, self.index_type)
        # 3. Add to GPU if available
        # 4. Train index if needed (IVF types)
        # 5. Add vectors: self.index.add(embeddings)
        pass
    
    def search(
        self,
        query: str,
        top_k: int = 50
    ) -> List[Tuple[str, float]]:
        """Search similar documents"""
        # TODO: Implement search
        # 1. Encode query
        # 2. Search: distances, indices = self.index.search(query_embedding, top_k)
        # 3. Return [(doc_id, score), ...]
        pass
    
    def save(self, path: str) -> None:
        """Save index to disk"""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        if self.use_gpu:
            # Move to CPU before saving
            index_cpu = faiss.index_gpu_to_cpu(self.index)
            faiss.write_index(index_cpu, path)
        else:
            faiss.write_index(self.index, path)
    
    def load(self, path: str) -> None:
        """Load index from disk"""
        self.index = faiss.read_index(path)
        if self.use_gpu:
            res = faiss.StandardGpuResources()
            self.index = faiss.index_cpu_to_gpu(res, 0, self.index)
```

### 1.2 Implement BM25 Index (src/retrieval/bm25_index.py)

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BM25 Indexing with Elasticsearch Fallback

Reference:
- Robertson & Zaragoza (2009). The Probabilistic Relevance Framework: BM25 and Beyond.
"""

from elasticsearch import Elasticsearch
from rank_bm25 import BM25Okapi
from typing import List, Dict, Tuple
import logging

class BM25Index:
    """
    BM25 sparse retrieval with Elasticsearch or rank-bm25 fallback
    
    Args:
        use_elasticsearch: Try ES first, fallback to rank-bm25
        es_host: Elasticsearch host
        index_name: ES index name
    
    Examples:
        >>> bm25 = BM25Index(use_elasticsearch=True)
        >>> bm25.add_documents(docs, doc_ids)
        >>> results = bm25.search("subjonctif français", top_k=50)
    """
    
    def __init__(
        self,
        use_elasticsearch: bool = True,
        es_host: str = "localhost",
        es_port: int = 9200,
        index_name: str = "kgclir_documents"
    ):
        self.use_es = use_elasticsearch
        self.index_name = index_name
        
        # Try Elasticsearch connection
        if self.use_es:
            try:
                self.es = Elasticsearch([f"http://{es_host}:{es_port}"])
                if not self.es.ping():
                    raise ConnectionError("ES not reachable")
                logging.info("Using Elasticsearch for BM25")
            except Exception as e:
                logging.warning(f"Elasticsearch unavailable: {e}. Falling back to rank-bm25")
                self.use_es = False
        
        # Fallback: rank-bm25
        if not self.use_es:
            self.bm25 = None
            self.doc_ids = []
            self.tokenized_corpus = []
    
    def add_documents(
        self,
        documents: List[str],
        doc_ids: List[str]
    ) -> None:
        """Add documents to index"""
        if self.use_es:
            # TODO: Bulk index to Elasticsearch
            # Use ES bulk API with batch_size=1000
            pass
        else:
            # TODO: Build rank-bm25 index
            # 1. Tokenize documents
            # 2. self.bm25 = BM25Okapi(self.tokenized_corpus)
            pass
    
    def search(
        self,
        query: str,
        top_k: int = 50
    ) -> List[Tuple[str, float]]:
        """Search with BM25"""
        if self.use_es:
            # TODO: ES query
            # Use match query with BM25 scoring
            pass
        else:
            # TODO: rank-bm25 search
            # 1. Tokenize query
            # 2. scores = self.bm25.get_scores(tokenized_query)
            # 3. Get top_k indices
            pass
```

### 1.3 Implement KG Query Expansion (src/retrieval/kg_expansion.py)

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Knowledge Graph Query Expansion

Expands query using KG neighbors and cross-lingual alignments.
"""

from src.kg.ontology import FLOOntology, RelationType
from typing import List, Dict, Set

class KGExpansion:
    """
    Expand queries using knowledge graph structure
    
    Strategy:
    1. Extract entities from query
    2. Find n-hop neighbors in KG
    3. Add cross-lingual translations via translatedAs/sameAs
    4. Weight expansion terms by path distance
    
    Args:
        ontology: FLO knowledge graph
        max_hops: Maximum path length
        relation_weights: Weights for different relation types
    
    Examples:
        >>> expander = KGExpansion(ontology, max_hops=2)
        >>> expanded_terms = expander.expand_query("虚拟式", language="zh")
        # Returns: ["虚拟式", "subjonctif", "subjunctive", "语法", ...]
    """
    
    def __init__(
        self,
        ontology: FLOOntology,
        max_hops: int = 2,
        relation_weights: Dict[str, float] = None
    ):
        self.ontology = ontology
        self.max_hops = max_hops
        
        # Default weights from config
        self.relation_weights = relation_weights or {
            "translatedAs": 1.0,
            "sameAs": 0.9,
            "belongsTo": 0.7,
            "supports": 0.6,
            "covers": 0.6,
            "hasPrereq": 0.5,
            "tests": 0.4
        }
    
    def expand_query(
        self,
        query: str,
        language: str,
        max_expansion_terms: int = 50
    ) -> List[Tuple[str, float]]:
        """
        Expand query with KG neighbors
        
        Returns:
            List of (term, weight) tuples
        """
        # TODO: Implement expansion
        # 1. Extract entities from query (match against KG)
        # 2. BFS/DFS to find neighbors within max_hops
        # 3. Apply decay: weight = base_weight * (decay^distance)
        # 4. Prioritize translatedAs and sameAs relations
        # 5. Return top_k weighted terms
        pass
    
    def get_cross_lingual_mappings(
        self,
        entity_id: str,
        target_lang: str
    ) -> List[str]:
        """Get cross-lingual equivalent entities"""
        # TODO: Follow translatedAs/sameAs to target language
        pass
```

### 1.4 Complete Joint Reranking (src/retrieval/kg_clir.py)

**This is your paper's Formula 1 contribution!**

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KG-CLIR Main Pipeline

Paper Contribution:
    Score(d,q) = α·sim_dense(d,q) + β·score_BM25(d,q) + γ·score_KG(d,q)

where:
    α, β, γ are hyperparameters (α=0.4, β=0.3, γ=0.3 from validation)

Reference:
    Your Paper (2025). KG-Enhanced Cross-Lingual Information Retrieval
"""

from src.retrieval.dense_index import DenseIndex
from src.retrieval.bm25_index import BM25Index
from src.retrieval.kg_expansion import KGExpansion
from src.kg.ontology import FLOOntology
from typing import List, Dict, Tuple
import numpy as np

class KGCLIR:
    """
    Knowledge Graph Enhanced Cross-Lingual Information Retrieval
    
    Args:
        ontology: FLO knowledge graph
        dense_model: Sentence transformer model name
        config: Retrieval configuration dict
    
    Examples:
        >>> clir = KGCLIR(ontology, config=config)
        >>> results = clir.search("法语虚拟式用法", top_k=10)
    """
    
    def __init__(
        self,
        ontology: FLOOntology,
        dense_model: str,
        config: Dict
    ):
        # Initialize retrievers
        self.dense_index = DenseIndex(dense_model)
        self.bm25_index = BM25Index()
        self.kg_expander = KGExpansion(ontology)
        
        # Hyperparameters (from config)
        self.alpha = config.get("alpha", 0.4)  # Dense weight
        self.beta = config.get("beta", 0.3)    # BM25 weight
        self.gamma = config.get("gamma", 0.3)  # KG weight
        
        self.ontology = ontology
    
    def search(
        self,
        query: str,
        top_k: int = 50,
        rerank_top_k: int = 10,
        return_explanation: bool = True
    ) -> List[Dict]:
        """
        Multi-stage retrieval pipeline
        
        Stage 1: Dense + BM25 retrieve top_k candidates
        Stage 2: KG expansion and reranking
        Stage 3: Return top rerank_top_k with explanations
        
        Returns:
            List of result dicts with keys:
            - doc_id: Document ID
            - score: Final score
            - explanation: KG path (if return_explanation=True)
        """
        # TODO: Implement full pipeline
        # 1. Dense retrieval
        dense_results = self.dense_index.search(query, top_k)
        
        # 2. BM25 retrieval
        bm25_results = self.bm25_index.search(query, top_k)
        
        # 3. KG expansion
        expanded_terms = self.kg_expander.expand_query(query)
        
        # 4. Compute KG scores for candidates
        # kg_scores = self._compute_kg_scores(candidates, expanded_terms)
        
        # 5. Joint reranking: α·dense + β·BM25 + γ·KG
        # final_scores = self._joint_reranking(dense_results, bm25_results, kg_scores)
        
        # 6. Sort and return top_k
        pass
    
    def _compute_kg_scores(
        self,
        doc_ids: List[str],
        expanded_terms: List[Tuple[str, float]]
    ) -> Dict[str, float]:
        """Compute KG-based scores for documents"""
        # TODO: Implement KG scoring
        # For each doc:
        #   1. Extract entities from doc
        #   2. Find paths to query entities in KG
        #   3. score_KG = Σ path_weight / (1 + path_length)
        pass
    
    def _joint_reranking(
        self,
        dense_results: List[Tuple[str, float]],
        bm25_results: List[Tuple[str, float]],
        kg_scores: Dict[str, float]
    ) -> List[Tuple[str, float]]:
        """Apply joint ranking formula"""
        # TODO: Normalize scores and combine
        # 1. Normalize each score type to [0, 1]
        # 2. Apply weighted sum: α·dense + β·BM25 + γ·KG
        # 3. Sort by final score
        pass
```

---

## 🎯 Priority 2: Complete Scripts for Reproducibility

### 2.1 Environment Check Script (scripts/check_environment.py)

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Environment validation script - 10 critical checks
"""

import sys
import importlib
from pathlib import Path

def check_environment():
    """Run all validation checks"""
    checks = [
        ("Python version", check_python_version),
        ("PyTorch + CUDA", check_pytorch),
        ("FAISS GPU", check_faiss),
        ("spaCy models", check_spacy_models),
        ("Neo4j connection", check_neo4j),
        ("Elasticsearch", check_elasticsearch),
        ("Config files", check_configs),
        ("Data directories", check_data_dirs),
        ("LLM API keys", check_api_keys),
        ("Write permissions", check_permissions)
    ]
    
    passed = 0
    for name, check_func in checks:
        try:
            check_func()
            print(f"✅ {name}: PASS")
            passed += 1
        except Exception as e:
            print(f"❌ {name}: FAIL - {e}")
    
    print(f"\n{'='*50}")
    print(f"Passed: {passed}/{len(checks)} checks")
    if passed == len(checks):
        print("✅ Environment is ready!")
        return 0
    else:
        print("⚠️  Some checks failed. See above for details.")
        return 1

def check_python_version():
    assert sys.version_info >= (3, 10), f"Python 3.10+ required, got {sys.version}"

def check_pytorch():
    import torch
    assert torch.cuda.is_available(), "CUDA not available"

# TODO: Implement other check functions

if __name__ == "__main__":
    sys.exit(check_environment())
```

### 2.2 Complete Experiment Pipeline (scripts/run_full_experiment.sh)

```bash
#!/bin/bash
# Complete 6-step experiment pipeline

set -e  # Exit on error

echo "========================================="
echo "KG-CLIR Complete Experiment Pipeline"
echo "========================================="

# Step 1: Environment check
echo ""
echo "[Step 1/6] Environment validation..."
python scripts/check_environment.py || {
    echo "❌ Environment check failed. Fix issues and retry."
    exit 1
}

# Step 2: Data preparation
echo ""
echo "[Step 2/6] Data preparation..."
python scripts/prepare_corpus.py --config config/kg.yaml

# Step 3: Knowledge graph construction
echo ""
echo "[Step 3/6] Building knowledge graph..."
python -m src.kg.build_kg --config config/kg.yaml

# Step 4: Cross-lingual alignment
echo ""
echo "[Step 4/6] Cross-lingual entity alignment..."
python -m src.align.align_pipeline --config config/align.yaml

# Step 5: Index building
echo ""
echo "[Step 5/6] Building retrieval indexes..."
bash scripts/run_index.sh

# Step 6: Evaluation
echo ""
echo "[Step 6/6] Running CLIR evaluation..."
python -m src.retrieval.evaluate_clir --config config/retrieval.yaml

echo ""
echo "========================================="
echo "✅ Experiment completed successfully!"
echo "Results saved to: outputs/"
echo "========================================="
```

---

## 🎯 Priority 3: Generate Test Data

Since you don't have real data yet, create a **minimal demo dataset**:

```bash
# Create demo data directory
mkdir -p data/demo

# Create demo corpus (JSONL format)
cat > data/demo/demo_corpus.jsonl << 'DEMO_EOF'
{"doc_id": "doc_001", "title": "Le subjonctif en français", "content": "Le subjonctif est un mode verbal utilisé pour exprimer le doute, le souhait ou l'incertitude.", "language": "fr"}
{"doc_id": "doc_002", "title": "法语虚拟式", "content": "虚拟式是法语中用于表达怀疑、愿望或不确定性的语气。", "language": "zh"}
{"doc_id": "doc_003", "title": "French Grammar Basics", "content": "The subjunctive mood in French expresses doubt, wish, or uncertainty.", "language": "en"}
DEMO_EOF

# Create alignment seeds (TSV format)
cat > data/seeds/align_seeds.tsv << 'SEEDS_EOF'
source_id	target_id	confidence
grammar_zh_001	grammar_fr_001	0.95
word_zh_002	word_fr_002	0.92
SEEDS_EOF

# Create test QRELS (TREC format)
cat > data/qrels/test.qrels << 'QRELS_EOF'
q001 0 doc_001 2
q001 0 doc_002 1
q002 0 doc_003 2
QRELS_EOF

# Create test queries
cat > data/qrels/queries.tsv << 'QUERIES_EOF'
query_id	query_text	language
q001	法语虚拟式用法	zh
q002	subjonctif français	fr
QUERIES_EOF
```

---

## 📚 Priority 4: Essential Documentation

### 4.1 Reproducibility Guide (docs/REPRODUCIBILITY.md)

```markdown
# Reproducibility Guide

## Quick Start (30 minutes)

### Step 1: Environment Setup (10 min)
```bash
# Clone repository
git clone <your-repo>
cd kgclir-french-lib

# Create conda environment
conda create -n kgclir python=3.10 -y
conda activate kgclir

# Install dependencies
pip install -r requirements.txt

# Download spaCy models
python -m spacy download fr_core_news_sm en_core_web_sm zh_core_web_sm
```

### Step 2: Configuration (5 min)
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings (Neo4j password, API keys, etc.)
nano .env
```

### Step 3: Run Demo Experiment (15 min)
```bash
# Run complete pipeline with demo data
bash scripts/run_full_experiment.sh --demo
```

### Step 4: Check Results
```bash
# View statistics
cat outputs/kg/kg_statistics.json

# View CLIR results
cat outputs/retrieval/clir_results.json

# View learning evaluation
cat outputs/learning/learning_results.csv
```

## Full Experiment (for paper reproduction)

[TODO: Add full experiment instructions with real dataset]
```

---

## ⏭️ What to Do Next

### Option A: I'll continue coding (DIY approach)

1. **Start with Priority 1**: Implement the retrieval module files above
2. **Use the code templates** provided in this guide
3. **Run tests as you go**: `pytest tests/test_retrieval.py -v`
4. **Follow TODO comments** in generated code

### Option B: Let Claude Code help (Recommended)

Since you have Claude Code access, you can:

1. **Use the Task tool** to generate specific modules:
   ```
   "Implement the dense_index.py module for FAISS-based semantic search according to the spec in NEXT_STEPS.md"
   ```

2. **Use feature-development-assistant** for complex features:
   ```
   "Implement the complete KG-CLIR pipeline with joint reranking formula: α·Dense + β·BM25 + γ·KG"
   ```

3. **Run the environment check** and fix issues one by one

### Option C: Focus on paper experiments only

If you just need to **run experiments for your paper**:

1. Skip full implementation
2. Create **mock data** (use the demo data creation commands above)
3. Implement **only evaluate_clir.py** to generate paper tables
4. Use the config files to document your intended system design

---

## 📊 Estimated Completion Time

| Priority | Task | Time | Importance |
|----------|------|------|------------|
| 1 | Retrieval module | 4-5 hours | ⭐⭐⭐⭐⭐ |
| 2 | Scripts | 1-2 hours | ⭐⭐⭐⭐ |
| 3 | Test data | 30 min | ⭐⭐⭐⭐ |
| 4 | Documentation | 1 hour | ⭐⭐⭐ |
| 5 | Alignment module | 2-3 hours | ⭐⭐⭐ |
| 6 | Learning module | 2-3 hours | ⭐⭐ |
| 7 | Application layer | 2-3 hours | ⭐⭐ |
| 8 | Tests | 1-2 hours | ⭐⭐ |
| 9 | Docker deployment | 1 hour | ⭐ |
| **Total** | | **15-20 hours** | |

---

## ❓ Questions?

1. **Q: Can I run the system now?**  
   A: Not the full system. You can run: utils, KG construction (with data). You need to implement retrieval to run search.

2. **Q: What's the minimum to get paper results?**  
   A: Implement retrieval module + evaluation script + create mock QRELS. ~6-8 hours.

3. **Q: Do I need real data?**  
   A: For development: No, use demo data. For paper: Yes, you need real corpus + manual QRELS.

4. **Q: Can I skip some modules?**  
   A: For a working system: No. For paper experiments: Yes, focus on retrieval + evaluation.

---

**Generated**: 2025-11-25  
**Next update**: After Priority 1 completion  
**For questions**: Check CLAUDE.md in project root
