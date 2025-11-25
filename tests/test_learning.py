#!/usr/bin/env python
# -*- coding: utf-8 -*-

from src.learning.learner_model import LearnerModel
from src.learning.rag_exercise import RAGExerciseGenerator
from src.kg.ontology import FLOOntology, EntityType
from src.retrieval.kg_expansion import KGQueryExpander


def test_learner_mastery_update():
    lm = LearnerModel(learner_id="u1")
    m0 = lm.compute_mastery("c1")
    lm.update_progress("c1", success=True, question_id="q1", difficulty=0.5, response_time=1.2)
    m1 = lm.compute_mastery("c1")
    assert m1 >= m0


def test_rag_generator_fallback():
    ont = FLOOntology()
    c = ont.add_entity("subjonctif", EntityType.GRAMMAR, language="fr")
    expander = KGQueryExpander(ontology=ont)
    gen = RAGExerciseGenerator(ontology=ont, kg_expander=expander, provider=None)
    data = gen.generate_exercises("subjonctif", num_questions=3)
    assert "exercises" in data and len(data["exercises"]) <= 3

