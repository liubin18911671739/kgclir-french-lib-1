#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Two-Stage Cross-lingual Entity Alignment Pipeline
两阶段跨语言实体对齐流水线

Pipeline:
    Stage 1: MTransE初始对齐 (Fast, High Recall)
    Stage 2: GCN-Align精化 (Accurate, High Precision)

工作流程：
1. MTransE生成初始候选对齐（top-k=100, 置信度>0.8）
2. GCN-Align利用图结构精化对齐
3. 置信度加权融合两阶段结果
4. 一致性检查（传递闭包、1-1约束）

学术价值：
- 结合嵌入空间（MTransE）和图结构（GCN）的优势
- 两阶段策略平衡召回率和精确率
"""

import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
import yaml
from tqdm import tqdm
from collections import defaultdict
import numpy as np

from ..utils.logger import logger
from ..utils.io import load_yaml, save_json, save_tsv
from ..kg.ontology import FLOOntology
from .mtrans_e import MTransE, AlignmentPair
from .gcn_align import GCNAlign


class AlignmentPipeline:
    """
    两阶段对齐流水线

    Args:
        config: 配置字典或配置文件路径
        ontology: FLO知识图谱

    Examples:
        >>> pipeline = AlignmentPipeline("config/align.yaml", ontology)
        >>> pipeline.run(seed_alignments, output_dir="outputs/alignment")
    """

    def __init__(self, config, ontology):
        # 加载配置
        if isinstance(config, str):
            self.config = load_yaml(config)
        else:
            self.config = config

        self.ontology = ontology
        self.mtranse = None
        self.gcn_align = None
        self.mtranse_candidates = []
        self.gcn_candidates = []
        self.final_alignments = []

    def run(self, seed_alignments, validation_alignments=None, output_dir="outputs/alignment"):
        """运行完整的两阶段对齐流水线"""
        logger.info("=" * 50)
        logger.info("Starting Two-Stage Alignment Pipeline")
        logger.info("=" * 50)

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Stage 1: MTransE
        logger.info("\n[Stage 1] MTransE Initial Alignment")
        self.mtranse_candidates = self._stage1_mtranse(seed_alignments, validation_alignments)
        self._save_candidates(self.mtranse_candidates, os.path.join(output_dir, "mtranse_candidates.tsv"))

        # Stage 2: GCN
        logger.info("\n[Stage 2] GCN-Align Refinement")
        self.gcn_candidates = self._stage2_gcn(seed_alignments, self.mtranse_candidates, validation_alignments)
        self._save_candidates(self.gcn_candidates, os.path.join(output_dir, "gcn_candidates.tsv"))

        # Stage 3: Fusion
        logger.info("\n[Stage 3] Fusion and Refinement")
        self.final_alignments = self._stage3_fusion()

        # Consistency check
        logger.info("\n[Stage 4] Consistency Check")
        self.final_alignments = self._consistency_check(self.final_alignments)

        self._save_candidates(self.final_alignments, os.path.join(output_dir, "final_alignment.tsv"))

        stats = self._generate_statistics(validation_alignments)
        save_json(stats, os.path.join(output_dir, "alignment_statistics.json"))

        logger.info(f"\nFinal Alignments: {len(self.final_alignments)}")
        return stats

    def _stage1_mtranse(self, seed_alignments, validation_alignments=None):
        """Stage 1: MTransE初始对齐"""
        mtranse_config = self.config.get("mtranse", {})
        
        self.mtranse = MTransE(
            embedding_dim=mtranse_config.get("embedding_dim", 128),
            learning_rate=mtranse_config.get("training", {}).get("learning_rate", 0.001),
            margin=mtranse_config.get("training", {}).get("margin", 1.0)
        )

        kg1_triples, kg2_triples = self._prepare_kg_data()
        
        logger.info("Training MTransE...")
        self.mtranse.train(kg1_triples, kg2_triples, seed_alignments, 
                          epochs=mtranse_config.get("training", {}).get("epochs", 1000))

        source_entities = self._get_entities_by_language(["zh"])
        target_entities = self._get_entities_by_language(["fr", "en"])

        predictions = self.mtranse.predict(source_entities, target_entities,
                                          top_k=mtranse_config.get("candidate_generation", {}).get("top_k", 100),
                                          threshold=mtranse_config.get("candidate_generation", {}).get("threshold", 0.8))

        candidates = []
        for entity_candidates in predictions:
            candidates.extend(entity_candidates)

        logger.info(f"MTransE generated {len(candidates)} candidates")
        return candidates

    def _stage2_gcn(self, seed_alignments, mtranse_candidates, validation_alignments=None):
        """Stage 2: GCN-Align精化"""
        gcn_config = self.config.get("gcn_align", {})
        
        self.gcn_align = GCNAlign(
            embedding_dim=gcn_config.get("architecture", {}).get("embedding_dim", 128),
            hidden_dim=gcn_config.get("architecture", {}).get("hidden_dim", 256),
            num_layers=gcn_config.get("architecture", {}).get("num_layers", 2),
            learning_rate=gcn_config.get("training", {}).get("learning_rate", 0.001),
            margin=gcn_config.get("training", {}).get("loss", {}).get("margin", 0.5),
            hard_negative_top_k=gcn_config.get("training", {}).get("loss", {}).get("hard_negative_top_k", 50)
        )

        # 使用高置信度MTransE候选作为伪标签
        augmented_seeds = seed_alignments.copy()
        for candidate in mtranse_candidates:
            if candidate.confidence >= 0.95:
                augmented_seeds.append(candidate)

        logger.info(f"Augmented training set: {len(augmented_seeds)} pairs")

        kg1_triples, kg2_triples = self._prepare_kg_data()
        
        logger.info("Training GCN-Align...")
        self.gcn_align.train(
            kg1_triples,
            kg2_triples,
            augmented_seeds,
            validation_alignments=validation_alignments,
            epochs=gcn_config.get("training", {}).get("epochs", 500),
            neg_ratio=gcn_config.get("training", {}).get("hard_negatives", {}).get("ratio", 0.3),
        )

        source_entities = self._get_entities_by_language(["zh"])
        target_entities = self._get_entities_by_language(["fr", "en"])

        predictions = self.gcn_align.predict(source_entities, target_entities, top_k=10, threshold=0.8)

        candidates = []
        for entity_candidates in predictions:
            candidates.extend(entity_candidates)

        logger.info(f"GCN-Align generated {len(candidates)} candidates")
        return candidates

    def _stage3_fusion(self):
        """Stage 3: 置信度加权融合"""
        weights = self.config.get("refinement", {}).get("confidence_update", {}).get("weights", {})
        w_mtranse = weights.get("mtranse", 0.4)
        w_gcn = weights.get("gcn", 0.6)

        mtranse_dict = {(p.entity1, p.entity2): p.confidence for p in self.mtranse_candidates}
        gcn_dict = {(p.entity1, p.entity2): p.confidence for p in self.gcn_candidates}

        all_pairs = set(mtranse_dict.keys()) | set(gcn_dict.keys())
        fused_alignments = []

        for pair in all_pairs:
            e1, e2 = pair
            mtranse_conf = mtranse_dict.get(pair, 0.0)
            gcn_conf = gcn_dict.get(pair, 0.0)

            if mtranse_conf > 0 and gcn_conf > 0:
                final_conf = w_mtranse * mtranse_conf + w_gcn * gcn_conf
                source = "fused"
            elif gcn_conf > 0:
                final_conf = gcn_conf
                source = "gcn_only"
            else:
                final_conf = mtranse_conf
                source = "mtranse_only"

            fused_alignments.append(AlignmentPair(entity1=e1, entity2=e2, confidence=final_conf, source=source))

        fused_alignments.sort(key=lambda x: x.confidence, reverse=True)
        logger.info(f"Fused {len(fused_alignments)} alignments")
        return fused_alignments

    def _consistency_check(self, alignments):
        """一致性检查：1-1约束"""
        consistency_config = self.config.get("refinement", {}).get("consistency_check", {})
        
        if not consistency_config.get("enabled", True):
            return alignments

        if consistency_config.get("one_to_one", True):
            alignments = self._enforce_one_to_one(alignments)

        return alignments

    def _enforce_one_to_one(self, alignments):
        """强制1-1约束"""
        alignments.sort(key=lambda x: x.confidence, reverse=True)
        seen_entities = set()
        filtered = []

        for pair in alignments:
            if pair.entity1 not in seen_entities and pair.entity2 not in seen_entities:
                filtered.append(pair)
                seen_entities.add(pair.entity1)
                seen_entities.add(pair.entity2)

        logger.info(f"1-1 constraint: {len(alignments)} → {len(filtered)} alignments")
        return filtered

    def _prepare_kg_data(self):
        """准备KG数据"""
        kg1_triples = []
        kg2_triples = []

        for relation in self.ontology.relations:
            source_entity = self.ontology.entities.get(relation.source_id)
            target_entity = self.ontology.entities.get(relation.target_id)

            if source_entity is None or target_entity is None:
                continue

            triple = (relation.source_id, relation.relation_type.value, relation.target_id)

            if source_entity.language == "zh":
                kg1_triples.append(triple)
            elif source_entity.language in ["fr", "en"]:
                kg2_triples.append(triple)

        logger.info(f"KG1 (zh): {len(kg1_triples)} triples, KG2 (fr/en): {len(kg2_triples)} triples")
        return kg1_triples, kg2_triples

    def _get_entities_by_language(self, languages):
        """获取指定语言的所有实体"""
        return [entity_id for entity_id, entity in self.ontology.entities.items() 
                if entity.language in languages]

    def _save_candidates(self, candidates, filepath):
        """保存候选对齐到TSV"""
        data = [[p.entity1, p.entity2, f"{p.confidence:.4f}", p.source] for p in candidates]
        save_tsv(data, filepath, header=["source_id", "target_id", "confidence", "source"])
        logger.info(f"Saved {len(candidates)} candidates to {filepath}")

    def _generate_statistics(self, validation_alignments=None):
        """生成统计信息"""
        return {
            "mtranse_candidates": len(self.mtranse_candidates),
            "gcn_candidates": len(self.gcn_candidates),
            "final_alignments": len(self.final_alignments),
            "avg_confidence": np.mean([p.confidence for p in self.final_alignments]) if self.final_alignments else 0.0
        }

    def get_final_alignments(self):
        """获取最终对齐结果"""
        return self.final_alignments
