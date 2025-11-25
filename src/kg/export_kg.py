#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Knowledge Graph Export Module
知识图谱导出模块

支持多种格式导出：
- JSON (完整图谱)
- RDF/Turtle (语义网标准)
- Neo4j (图数据库)
- NetworkX (内存图，用于分析)
"""

from pathlib import Path
from typing import Dict, Optional
import json

from ..utils.logger import logger
from ..utils.io import save_json, ensure_dir
from .ontology import FLOOntology


def export_to_json(ontology: FLOOntology, output_path: str) -> None:
    """
    导出为JSON格式
    
    Args:
        ontology: FLO本体
        output_path: 输出路径
    """
    # 构建JSON结构
    kg_data = {
        "version": ontology.version,
        "base_uri": ontology.base_uri,
        "entities": [],
        "relations": []
    }
    
    # 导出实体
    for entity_id, entity in ontology.entities.items():
        kg_data["entities"].append({
            "id": entity.entity_id,
            "name": entity.name,
            "type": entity.entity_type.value,
            "language": entity.language,
            "description": entity.description,
            "aliases": entity.aliases,
            "metadata": entity.metadata
        })
    
    # 导出关系
    for relation in ontology.relations:
        kg_data["relations"].append({
            "source": relation.source_id,
            "target": relation.target_id,
            "type": relation.relation_type.value,
            "confidence": relation.confidence,
            "metadata": relation.metadata
        })
    
    # 保存
    ensure_dir(Path(output_path).parent)
    save_json(kg_data, output_path)
    
    logger.info(f"Exported {len(kg_data['entities'])} entities and {len(kg_data['relations'])} relations to JSON")


def export_to_rdf(ontology: FLOOntology, output_path: str, format: str = "turtle") -> None:
    """
    导出为RDF格式
    
    Args:
        ontology: FLO本体
        output_path: 输出路径
        format: RDF序列化格式 (turtle/xml/n3)
    """
    try:
        from rdflib import Graph, Namespace, Literal, URIRef
        from rdflib.namespace import RDF, RDFS, OWL
    except ImportError:
        logger.error("rdflib not installed. Cannot export to RDF.")
        return
    
    # 创建RDF图
    g = Graph()
    
    # 定义命名空间
    FLO = Namespace(ontology.base_uri)
    g.bind("flo", FLO)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("owl", OWL)
    
    # 添加本体声明
    ontology_uri = URIRef(ontology.base_uri)
    g.add((ontology_uri, RDF.type, OWL.Ontology))
    g.add((ontology_uri, RDFS.label, Literal("French Learning Ontology")))
    g.add((ontology_uri, OWL.versionInfo, Literal(ontology.version)))
    
    # 添加实体
    for entity_id, entity in ontology.entities.items():
        entity_uri = FLO[entity_id]
        
        # 类型声明
        g.add((entity_uri, RDF.type, FLO[entity.entity_type.value]))
        
        # 属性
        g.add((entity_uri, RDFS.label, Literal(entity.name, lang=entity.language)))
        
        if entity.description:
            g.add((entity_uri, RDFS.comment, Literal(entity.description, lang=entity.language)))
        
        # 别名
        for alias in entity.aliases:
            g.add((entity_uri, FLO.alias, Literal(alias, lang=entity.language)))
    
    # 添加关系
    for relation in ontology.relations:
        source_uri = FLO[relation.source_id]
        target_uri = FLO[relation.target_id]
        relation_uri = FLO[relation.relation_type.value]
        
        g.add((source_uri, relation_uri, target_uri))
    
    # 序列化保存
    ensure_dir(Path(output_path).parent)
    g.serialize(destination=output_path, format=format)
    
    logger.info(f"Exported RDF graph with {len(g)} triples")


def export_to_neo4j(ontology: FLOOntology, config: Dict) -> None:
    """
    导出到Neo4j图数据库
    
    Args:
        ontology: FLO本体
        config: Neo4j配置
    """
    try:
        from neo4j import GraphDatabase
    except ImportError:
        logger.error("neo4j driver not installed. Cannot export to Neo4j.")
        return
    
    uri = config.get("uri", "bolt://localhost:7687")
    auth = config.get("auth", {})
    username = auth.get("username", "neo4j")
    password = auth.get("password", "password")
    database = config.get("database", "neo4j")
    
    try:
        # 连接Neo4j
        driver = GraphDatabase.driver(uri, auth=(username, password))
        
        with driver.session(database=database) as session:
            # 清空数据库（可选）
            logger.info("Clearing existing data...")
            session.run("MATCH (n) DETACH DELETE n")
            
            # 创建实体节点
            logger.info("Creating entity nodes...")
            for entity_id, entity in ontology.entities.items():
                session.run(
                    """
                    CREATE (n:Entity {
                        id: $id,
                        name: $name,
                        type: $type,
                        language: $language,
                        description: $description
                    })
                    """,
                    id=entity.entity_id,
                    name=entity.name,
                    type=entity.entity_type.value,
                    language=entity.language,
                    description=entity.description or ""
                )
            
            # 创建关系
            logger.info("Creating relationships...")
            for relation in ontology.relations:
                rel_type = relation.relation_type.value.upper()
                session.run(
                    f"""
                    MATCH (a:Entity {{id: $source_id}})
                    MATCH (b:Entity {{id: $target_id}})
                    CREATE (a)-[r:{rel_type} {{confidence: $confidence}}]->(b)
                    """,
                    source_id=relation.source_id,
                    target_id=relation.target_id,
                    confidence=relation.confidence
                )
            
            # 创建索引
            logger.info("Creating indexes...")
            session.run("CREATE INDEX entity_id IF NOT EXISTS FOR (n:Entity) ON (n.id)")
            session.run("CREATE INDEX entity_name IF NOT EXISTS FOR (n:Entity) ON (n.name)")
            session.run("CREATE INDEX entity_type IF NOT EXISTS FOR (n:Entity) ON (n.type)")
            session.run("CREATE INDEX entity_language IF NOT EXISTS FOR (n:Entity) ON (n.language)")
        
        driver.close()
        logger.info(f"Successfully exported to Neo4j: {len(ontology.entities)} nodes, {len(ontology.relations)} relationships")
    
    except Exception as e:
        logger.error(f"Failed to export to Neo4j: {e}")
        logger.info("Tip: Make sure Neo4j is running and credentials are correct")


def export_to_networkx(ontology: FLOOntology, output_path: Optional[str] = None):
    """
    导出为NetworkX图（内存图或pickle文件）
    
    Args:
        ontology: FLO本体
        output_path: 可选的pickle输出路径
    
    Returns:
        NetworkX图对象
    """
    try:
        import networkx as nx
    except ImportError:
        logger.error("networkx not installed. Cannot export to NetworkX.")
        return None
    
    # 创建有向图
    G = nx.DiGraph()
    
    # 添加节点
    for entity_id, entity in ontology.entities.items():
        G.add_node(
            entity_id,
            name=entity.name,
            type=entity.entity_type.value,
            language=entity.language,
            description=entity.description
        )
    
    # 添加边
    for relation in ontology.relations:
        G.add_edge(
            relation.source_id,
            relation.target_id,
            type=relation.relation_type.value,
            confidence=relation.confidence
        )
    
    logger.info(f"Created NetworkX graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    
    # 保存为pickle
    if output_path:
        import pickle
        ensure_dir(Path(output_path).parent)
        with open(output_path, "wb") as f:
            pickle.dump(G, f)
        logger.info(f"Saved NetworkX graph to {output_path}")
    
    return G
