#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Knowledge Graph Builder
知识图谱构建主流程

完整的KG构建流程：
1. 加载配置
2. 加载语料
3. 实体抽取
4. 关系抽取
5. 知识融合
6. 质量验证
7. 导出KG

学术流程参考：
- Knowledge Graph Construction: Paulheim (2017). Knowledge graph refinement: A survey.
"""

import time
from pathlib import Path
from typing import Dict, List, Optional
import argparse

from ..utils.io import load_yaml, load_jsonl, save_json
from ..utils.logger import logger, setup_logging
from .ontology import FLOOntology, EntityType, RelationType
from .extract_entities import EntityExtractor, convert_to_ontology_entities
from .extract_relations import RelationExtractor
from .export_kg import export_to_neo4j, export_to_json, export_to_rdf


class KnowledgeGraphBuilder:
    """
    知识图谱构建器
    
    协调整个KG构建流程。
    
    Examples:
        >>> builder = KnowledgeGraphBuilder(config_path="config/kg.yaml")
        >>> ontology = builder.build()
        >>> builder.export_all(ontology)
    """
    
    def __init__(self, config_path: str = "config/kg.yaml"):
        """
        初始化构建器
        
        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        self.config = load_yaml(config_path)
        logger.info(f"Loaded configuration from {config_path}")
        
        # 初始化本体
        ontology_config = self.config.get("ontology", {})
        self.ontology = FLOOntology(
            version=ontology_config.get("version", "1.0"),
            base_uri=ontology_config.get("base_uri", "http://kgclir.org/flo/")
        )
        
        # 初始化抽取器
        self.entity_extractor = EntityExtractor(load_models=True)
        self.relation_extractor = RelationExtractor(load_spacy=True)
        
        # 统计信息
        self.stats = {
            "start_time": None,
            "end_time": None,
            "corpus_size": 0,
            "entities_extracted": 0,
            "relations_extracted": 0,
            "entities_added": 0,
            "relations_added": 0
        }
    
    def build(self, demo_mode: bool = False) -> FLOOntology:
        """
        执行完整的KG构建流程
        
        Args:
            demo_mode: 是否使用演示数据（小规模）
        
        Returns:
            构建完成的本体
        """
        logger.info("=" * 60)
        logger.info("Starting Knowledge Graph Construction")
        logger.info("=" * 60)
        
        self.stats["start_time"] = time.time()
        
        # 1. 加载语料
        corpus = self._load_corpus(demo_mode)
        self.stats["corpus_size"] = len(corpus)
        logger.info(f"Loaded {len(corpus)} documents")
        
        # 2. 实体抽取
        logger.info("\n[Step 1/4] Extracting entities...")
        extracted_entities = self._extract_entities(corpus)
        self.stats["entities_extracted"] = len(extracted_entities)
        
        # 3. 添加实体到本体
        logger.info("\n[Step 2/4] Adding entities to ontology...")
        entity_names = self._add_entities_to_ontology(extracted_entities)
        self.stats["entities_added"] = len(entity_names)
        
        # 4. 关系抽取
        logger.info("\n[Step 3/4] Extracting relations...")
        extracted_relations = self._extract_relations(corpus, entity_names)
        self.stats["relations_extracted"] = len(extracted_relations)
        
        # 5. 添加关系到本体
        logger.info("\n[Step 4/4] Adding relations to ontology...")
        self._add_relations_to_ontology(extracted_relations)
        self.stats["relations_added"] = len(self.ontology.relations)
        
        # 6. 验证本体
        logger.info("\n[Validation] Validating ontology schema...")
        validation_report = self.ontology.validate_schema()
        self._log_validation_report(validation_report)
        
        self.stats["end_time"] = time.time()
        self.stats["construction_time_seconds"] = int(self.stats["end_time"] - self.stats["start_time"])
        
        logger.info("\n" + "=" * 60)
        logger.info("Knowledge Graph Construction Completed!")
        logger.info("=" * 60)
        self._log_statistics()
        
        return self.ontology
    
    def _load_corpus(self, demo_mode: bool) -> List[Dict]:
        """加载语料"""
        data_sources = self.config.get("data_sources", {})
        corpus = []
        
        if demo_mode:
            # 演示模式：使用小规模数据
            demo_config = data_sources.get("demo", {})
            if demo_config.get("enabled", False):
                demo_path = demo_config.get("path", "data/demo/demo_corpus.jsonl")
                max_samples = demo_config.get("max_samples", 1000)
                
                if Path(demo_path).exists():
                    data = load_jsonl(demo_path, max_lines=max_samples)
                    corpus.extend(data)
                    logger.info(f"Loaded demo corpus: {len(data)} samples")
                else:
                    logger.warning(f"Demo corpus not found: {demo_path}")
        else:
            # 正常模式：加载所有数据源
            for source_name, source_config in data_sources.items():
                if source_name == "demo":
                    continue
                
                path = source_config.get("path")
                if path and Path(path).exists():
                    data = load_jsonl(path)
                    corpus.extend(data)
                    logger.info(f"Loaded {source_name}: {len(data)} documents")
                else:
                    logger.warning(f"Data source not found: {path}")
        
        return corpus
    
    def _extract_entities(self, corpus: List[Dict]) -> List:
        """批量抽取实体"""
        extracted_entities = self.entity_extractor.extract_from_corpus(
            corpus=corpus,
            text_field="text",
            language_field="language"
        )
        
        logger.info(f"Extracted {len(extracted_entities)} unique entities")
        
        # 按类型统计
        type_counts = {}
        for entity in extracted_entities:
            entity_type = entity.entity_type.value
            type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
        
        logger.info("Entities by type:")
        for entity_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            logger.info(f"  {entity_type}: {count}")
        
        return extracted_entities
    
    def _add_entities_to_ontology(self, extracted_entities: List) -> List[str]:
        """添加实体到本体"""
        entity_names = []
        
        for ext_entity in extracted_entities:
            entity_id = self.ontology.add_entity(
                name=ext_entity.name,
                entity_type=ext_entity.entity_type,
                language=ext_entity.language,
                metadata={
                    "confidence": ext_entity.confidence,
                    "source": ext_entity.source,
                    "context": ext_entity.context
                }
            )
            
            entity_names.append(ext_entity.name)
        
        logger.info(f"Added {len(entity_names)} entities to ontology")
        
        return entity_names
    
    def _extract_relations(self, corpus: List[Dict], entity_names: List[str]) -> List:
        """批量抽取关系"""
        extracted_relations = self.relation_extractor.extract_from_corpus(
            corpus=corpus,
            entities=entity_names,
            text_field="text",
            language_field="language"
        )
        
        logger.info(f"Extracted {len(extracted_relations)} unique relations")
        
        # 按类型统计
        type_counts = {}
        for relation in extracted_relations:
            rel_type = relation.relation_type.value
            type_counts[rel_type] = type_counts.get(rel_type, 0) + 1
        
        logger.info("Relations by type:")
        for rel_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            logger.info(f"  {rel_type}: {count}")
        
        return extracted_relations
    
    def _add_relations_to_ontology(self, extracted_relations: List):
        """添加关系到本体"""
        added_count = 0
        
        for ext_relation in extracted_relations:
            try:
                success = self.ontology.add_relation(
                    source=ext_relation.source_name,
                    target=ext_relation.target_name,
                    relation_type=ext_relation.relation_type,
                    confidence=ext_relation.confidence,
                    metadata={
                        "evidence": ext_relation.evidence,
                        "source_method": ext_relation.source_method
                    }
                )
                
                if success:
                    added_count += 1
            
            except Exception as e:
                # 跳过无效关系
                logger.debug(f"Failed to add relation: {e}")
                continue
        
        logger.info(f"Added {added_count} relations to ontology")
    
    def _log_validation_report(self, report: Dict):
        """记录验证报告"""
        logger.info(f"Total entities: {report['total_entities']}")
        logger.info(f"Total relations: {report['total_relations']}")
        
        if report['isolated_nodes']:
            logger.warning(f"Found {len(report['isolated_nodes'])} isolated nodes")
        
        logger.info("Language coverage:")
        for lang, coverage in report['language_coverage'].items():
            logger.info(f"  {lang}: {coverage['count']} ({coverage['percentage']:.1f}%)")
    
    def _log_statistics(self):
        """记录统计信息"""
        logger.info(f"\nConstruction Statistics:")
        logger.info(f"  Corpus size: {self.stats['corpus_size']} documents")
        logger.info(f"  Entities extracted: {self.stats['entities_extracted']}")
        logger.info(f"  Entities added: {self.stats['entities_added']}")
        logger.info(f"  Relations extracted: {self.stats['relations_extracted']}")
        logger.info(f"  Relations added: {self.stats['relations_added']}")
        logger.info(f"  Time: {self.stats['construction_time_seconds']}s")
    
    def export_all(self, ontology: Optional[FLOOntology] = None):
        """
        导出KG到所有配置的格式
        
        Args:
            ontology: 要导出的本体（默认使用self.ontology）
        """
        if ontology is None:
            ontology = self.ontology
        
        output_config = self.config.get("output", {})
        formats = output_config.get("formats", [])
        paths = output_config.get("paths", {})
        
        logger.info("\n" + "=" * 60)
        logger.info("Exporting Knowledge Graph")
        logger.info("=" * 60)
        
        # 导出统计信息
        if "statistics" in formats:
            stats_path = paths.get("statistics", "outputs/kg/kg_statistics.json")
            stats = ontology.export_statistics()
            stats.update(self.stats)  # 合并构建统计
            save_json(stats, stats_path)
            logger.info(f"✓ Exported statistics to {stats_path}")
        
        # 导出JSON
        if "json" in formats:
            json_path = paths.get("json", "outputs/kg/knowledge_graph.json")
            export_to_json(ontology, json_path)
            logger.info(f"✓ Exported JSON to {json_path}")
        
        # 导出RDF
        if "rdf" in formats:
            rdf_path = paths.get("rdf", "outputs/kg/knowledge_graph.ttl")
            try:
                export_to_rdf(ontology, rdf_path)
                logger.info(f"✓ Exported RDF to {rdf_path}")
            except Exception as e:
                logger.error(f"✗ Failed to export RDF: {e}")
        
        # 导出Neo4j
        if "neo4j" in formats:
            neo4j_config = self.config.get("neo4j", {})
            try:
                export_to_neo4j(ontology, neo4j_config)
                logger.info(f"✓ Exported to Neo4j database")
            except Exception as e:
                logger.error(f"✗ Failed to export to Neo4j: {e}")
        
        logger.info("=" * 60)
        logger.info("Export completed!")
        logger.info("=" * 60)


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="Build FLO Knowledge Graph for French Learning"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/kg.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Use demo dataset (small scale)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default="logs/kg_construction.log",
        help="Log file path"
    )
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging(log_file=args.log_file, level=args.log_level)
    
    # 构建知识图谱
    builder = KnowledgeGraphBuilder(config_path=args.config)
    ontology = builder.build(demo_mode=args.demo)
    
    # 导出
    builder.export_all(ontology)
    
    logger.info("\n✅ Knowledge Graph construction pipeline completed successfully!")


if __name__ == "__main__":
    main()
