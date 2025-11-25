#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test Script for Knowledge Graph Construction
知识图谱构建测试脚本

快速测试KG构建流程的各个模块。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import logger, setup_logging
from src.kg.ontology import FLOOntology, EntityType, RelationType
from src.kg.extract_entities import EntityExtractor
from src.kg.extract_relations import RelationExtractor
from src.kg.fuse_kg import fuse_knowledge_graph
from src.kg.export_kg import export_to_json, export_to_networkx


def test_ontology():
    """测试本体基本功能"""
    logger.info("=" * 60)
    logger.info("Testing FLO Ontology")
    logger.info("=" * 60)
    
    # 创建本体
    ontology = FLOOntology(version="1.0", base_uri="http://example.org/flo/")
    
    # 添加实体
    ontology.add_entity("être", EntityType.WORD, "fr", "动词：是、在")
    ontology.add_entity("avoir", EntityType.WORD, "fr", "动词：有")
    ontology.add_entity("présent", EntityType.GRAMMAR, "fr", "现在时")
    ontology.add_entity("A1", EntityType.CEFR_LEVEL, "fr", "CEFR A1级别")
    
    # 添加关系
    ontology.add_relation("être", "présent", RelationType.COVERS, confidence=0.9)
    ontology.add_relation("avoir", "présent", RelationType.COVERS, confidence=0.9)
    ontology.add_relation("être", "A1", RelationType.BELONGS_TO, confidence=1.0)
    
    logger.info(f"Created ontology with {len(ontology.entities)} entities, {len(ontology.relations)} relations")
    
    # 测试邻居查询
    neighbors = ontology.get_neighbors("être", max_hops=1)
    logger.info(f"Neighbors of 'être': {len(neighbors)}")
    for neighbor_id, rel_type, hops in neighbors:
        neighbor = ontology.entities[neighbor_id]
        logger.info(f"  - {neighbor.name} ({rel_type.value}, distance={hops})")
    
    # 验证schema
    report = ontology.validate_schema()
    logger.info(f"Validation report: {report['total_entities']} entities, {report['total_relations']} relations")
    
    return ontology


def test_entity_extraction():
    """测试实体抽取"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Entity Extraction")
    logger.info("=" * 60)
    
    # 创建抽取器
    extractor = EntityExtractor(load_models=False)  # 演示模式不加载模型
    
    # 测试文本
    texts = [
        {
            "text": "Le verbe être au présent: je suis, tu es, il est.",
            "language": "fr"
        },
        {
            "text": "法语的现在时动词变位包括être和avoir。",
            "language": "zh"
        }
    ]
    
    # 抽取实体
    entities = extractor.extract_from_corpus(texts, text_field="text", language_field="language")
    
    logger.info(f"Extracted {len(entities)} entities:")
    for entity in entities[:10]:  # 显示前10个
        logger.info(f"  - {entity.name} ({entity.entity_type.value}, {entity.language}, confidence={entity.confidence:.2f})")
    
    return entities


def test_relation_extraction():
    """测试关系抽取"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Relation Extraction")
    logger.info("=" * 60)
    
    # 创建抽取器
    extractor = RelationExtractor(load_spacy=False)  # 演示模式
    
    # 测试文本
    texts = [
        {
            "text": "Le passé composé nécessite l'auxiliaire avoir ou être.",
            "language": "fr"
        }
    ]
    
    entities = ["passé composé", "avoir", "être"]
    
    # 抽取关系
    relations = extractor.extract_from_corpus(texts, entities, text_field="text", language_field="language")
    
    logger.info(f"Extracted {len(relations)} relations:")
    for relation in relations[:10]:
        logger.info(f"  - {relation.source_name} --[{relation.relation_type.value}]--> {relation.target_name} (confidence={relation.confidence:.2f})")
    
    return relations


def test_knowledge_fusion():
    """测试知识融合"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Knowledge Fusion")
    logger.info("=" * 60)
    
    # 创建本体并添加重复实体
    ontology = FLOOntology()
    
    # 添加相似实体
    ontology.add_entity("être", EntityType.WORD, "fr")
    ontology.add_entity("etre", EntityType.WORD, "fr")  # 无重音，应该被识别为重复
    ontology.add_entity("avoir", EntityType.WORD, "fr")
    ontology.add_entity("Avoir", EntityType.WORD, "fr")  # 大小写不同
    
    # 添加重复关系
    ontology.add_relation("être", "avoir", RelationType.SAME_AS)
    ontology.add_relation("être", "avoir", RelationType.SAME_AS)  # 完全重复
    
    logger.info(f"Before fusion: {len(ontology.entities)} entities, {len(ontology.relations)} relations")
    
    # 执行融合
    stats = fuse_knowledge_graph(ontology, entity_similarity_threshold=0.8)
    
    logger.info(f"After fusion: {len(ontology.entities)} entities, {len(ontology.relations)} relations")
    logger.info(f"Fusion stats: {stats}")
    
    return ontology


def test_export():
    """测试导出功能"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Export")
    logger.info("=" * 60)
    
    # 创建简单本体
    ontology = FLOOntology()
    ontology.add_entity("test1", EntityType.WORD, "fr")
    ontology.add_entity("test2", EntityType.WORD, "fr")
    ontology.add_relation("test1", "test2", RelationType.SAME_AS)
    
    # 导出JSON
    output_dir = project_root / "outputs" / "test"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    json_path = output_dir / "test_kg.json"
    export_to_json(ontology, str(json_path))
    logger.info(f"✓ Exported to JSON: {json_path}")
    
    # 导出NetworkX
    try:
        G = export_to_networkx(ontology)
        logger.info(f"✓ Exported to NetworkX: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    except ImportError:
        logger.warning("NetworkX not installed, skipping")
    
    return ontology


def main():
    """运行所有测试"""
    # 设置日志
    setup_logging(log_file="logs/test_kg.log", level="INFO")
    
    logger.info("Starting Knowledge Graph Tests")
    logger.info("=" * 80)
    
    try:
        # 运行测试
        test_ontology()
        test_entity_extraction()
        test_relation_extraction()
        test_knowledge_fusion()
        test_export()
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ All tests completed successfully!")
        logger.info("=" * 80)
    
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
