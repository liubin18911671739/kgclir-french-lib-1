#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest

from src.align.gcn_align import GCNAlign
from src.align.mtrans_e import AlignmentPair


def test_gcn_align_minimal_training():
    # 两个小图 + 一个对齐
    kg1 = [("a1", "rel", "a2"), ("a2", "rel", "a3")]
    kg2 = [("b1", "rel", "b2"), ("b2", "rel", "b3")]
    seeds = [AlignmentPair(entity1="a1", entity2="b1", confidence=1.0, source="seed")]

    model = GCNAlign(embedding_dim=16, hidden_dim=16, num_layers=2, margin=0.5, hard_negative_top_k=0, device="cpu")
    hist = model.train(kg1, kg2, seeds, validation_alignments=None, epochs=1, batch_size=2, neg_ratio=0.5)
    assert "loss" in hist and len(hist["loss"]) >= 1

    res = model.predict(["a1"], ["b1", "b2"], top_k=2)
    assert isinstance(res, list)

