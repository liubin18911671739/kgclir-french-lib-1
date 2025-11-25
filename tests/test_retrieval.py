#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest

from src.retrieval.bm25_index import BM25Retriever
from src.retrieval.kg_expansion import KGQueryExpander
from src.kg.ontology import FLOOntology, EntityType, RelationType


def test_bm25_basic():
    docs = ["bonjour le monde", "salut tout le monde", "grammaire française"]
    ids = ["d1", "d2", "d3"]
    bm25 = BM25Retriever(k1=1.2, b=0.75, use_stopwords=False, language="fr")
    bm25.build_index(docs, ids)
    res = bm25.search("monde", top_k=2)
    assert len(res) <= 2


def test_kg_expansion():
    ont = FLOOntology()
    a = ont.add_entity("虚拟式", EntityType.GRAMMAR, language="zh")
    b = ont.add_entity("subjonctif", EntityType.GRAMMAR, language="fr")
    ont.add_relation(a, b, RelationType.TRANSLATED_AS)

    exp = KGQueryExpander(ontology=ont, max_hops=1)
    terms = exp.expand_query("虚拟式", top_k=3)
    assert isinstance(terms, dict)

