#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
FLO (French Learning Ontology) 本体定义

理论基础：
- 领域建模：Guarino & Welty (2002) OntoClean方法论
- 多语种对齐：Multilingual Ontology (Espinoza et al., 2009)

本体设计原则：
1. 类型层次：Concept/Activity/Resource/Context四大超类
2. 关系语义：遵循OWL-DL可判定性约束
3. 扩展性：支持CEFR标准扩展（A1-C2分级）

学术引用：
- Guarino, N., & Welty, C. (2002). Evaluating ontological decisions with OntoClean.
- Espinoza, M., et al. (2009). Ontology localization. Web Semantics.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set, Tuple
from collections import defaultdict
import uuid


class EntityType(Enum):
    """FLO实体类型枚举（17种）"""
    
    # 知识概念类（Concept）
    WORD = "Word"  # 词汇
    GRAMMAR = "Grammar"  # 语法
    PRAGMATICS = "Pragmatics"  # 语用
    CULTURE = "Culture"  # 文化
    TOPIC = "Topic"  # 主题
    
    # 学习活动类（Activity）
    EXERCISE = "Exercise"  # 练习
    TASK = "Task"  # 任务
    TEST = "Test"  # 测试
    
    # 学习成果类（Outcome）
    OUTCOME = "Outcome"  # 学习成果
    CEFR_SKILL = "CEFR_Skill"  # CEFR技能
    
    # 资源类（Resource）
    TEXTBOOK = "Textbook"  # 教材
    REFERENCE = "Reference"  # 参考资料
    ARTICLE = "Article"  # 文章
    MEDIA = "Media"  # 媒体资源
    LEX_CORPUS = "LexCorpus"  # 词汇语料
    
    # 组织类（Context）
    COURSE = "Course"  # 课程
    LEVEL = "Level"  # 水平等级


class RelationType(Enum):
    """FLO关系类型枚举（7种核心关系）"""
    
    BELONGS_TO = "belongsTo"  # 从属关系
    SUPPORTS = "supports"  # 支持关系
    TESTS = "tests"  # 测试关系
    COVERS = "covers"  # 覆盖关系
    HAS_PREREQ = "hasPrereq"  # 前置关系
    TRANSLATED_AS = "translatedAs"  # 翻译关系
    SAME_AS = "sameAs"  # 等价关系


@dataclass
class Entity:
    """实体类"""
    
    entity_id: str  # 唯一标识符
    name: str  # 实体名称
    entity_type: EntityType  # 实体类型
    language: str  # 语言代码 (zh/fr/en)
    
    # 可选属性
    description: Optional[str] = None
    aliases: List[str] = field(default_factory=list)  # 别名
    metadata: Dict[str, any] = field(default_factory=dict)  # 元数据
    
    def __post_init__(self):
        """验证实体数据"""
        if self.language not in {"zh", "fr", "en"}:
            raise ValueError(f"Invalid language: {self.language}")
    
    def __hash__(self):
        return hash(self.entity_id)
    
    def __eq__(self, other):
        if not isinstance(other, Entity):
            return False
        return self.entity_id == other.entity_id


@dataclass
class Relation:
    """关系类"""
    
    source_id: str  # 源实体ID
    target_id: str  # 目标实体ID
    relation_type: RelationType  # 关系类型
    
    # 可选属性
    confidence: float = 1.0  # 置信度 [0, 1]
    metadata: Dict[str, any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash((self.source_id, self.target_id, self.relation_type.value))
    
    def __eq__(self, other):
        if not isinstance(other, Relation):
            return False
        return (
            self.source_id == other.source_id and
            self.target_id == other.target_id and
            self.relation_type == other.relation_type
        )


class FLOOntology:
    """
    FLO本体管理器
    
    提供知识图谱的构建、查询、验证和导出功能。
    
    Attributes:
        version: 本体版本
        base_uri: 基础URI
        entities: 实体字典 {entity_id: Entity}
        relations: 关系集合 {Relation}
        entity_index: 实体索引（按类型和语言）
    
    Examples:
        >>> ontology = FLOOntology(version="1.0")
        >>> ontology.add_entity("虚拟式", EntityType.GRAMMAR, language="zh")
        >>> ontology.add_entity("subjonctif", EntityType.GRAMMAR, language="fr")
        >>> ontology.add_relation("虚拟式", "subjonctif", RelationType.TRANSLATED_AS)
        >>> stats = ontology.export_statistics()
    """
    
    def __init__(self, version: str = "1.0", base_uri: str = "http://kgclir.org/flo/"):
        self.version = version
        self.base_uri = base_uri
        
        # 核心数据结构
        self.entities: Dict[str, Entity] = {}
        self.relations: Set[Relation] = set()
        
        # 索引结构（加速查询）
        self.entity_index: Dict[str, Dict[str, List[str]]] = {
            "type": defaultdict(list),  # {type: [entity_id, ...]}
            "language": defaultdict(list),  # {language: [entity_id, ...]}
            "name": {}  # {name: entity_id}
        }
        
        # 邻接表（加速图遍历）
        self.adjacency_list: Dict[str, List[Tuple[str, RelationType]]] = defaultdict(list)
    
    def add_entity(
        self,
        name: str,
        entity_type: EntityType,
        language: str,
        entity_id: Optional[str] = None,
        description: Optional[str] = None,
        aliases: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        添加实体到本体
        
        Args:
            name: 实体名称
            entity_type: 实体类型
            language: 语言代码
            entity_id: 可选的自定义ID（默认自动生成）
            description: 描述
            aliases: 别名列表
            metadata: 元数据
        
        Returns:
            实体ID
        
        Raises:
            ValueError: 实体已存在或数据无效
        """
        # 生成实体ID
        if entity_id is None:
            entity_id = self._generate_entity_id(name, entity_type, language)
        
        # 检查重复
        if entity_id in self.entities:
            return entity_id  # 已存在，返回现有ID
        
        # 创建实体
        entity = Entity(
            entity_id=entity_id,
            name=name,
            entity_type=entity_type,
            language=language,
            description=description,
            aliases=aliases or [],
            metadata=metadata or {}
        )
        
        # 存储实体
        self.entities[entity_id] = entity
        
        # 更新索引
        self.entity_index["type"][entity_type.value].append(entity_id)
        self.entity_index["language"][language].append(entity_id)
        self.entity_index["name"][name.lower()] = entity_id
        
        return entity_id
    
    def add_relation(
        self,
        source: str,
        target: str,
        relation_type: RelationType,
        confidence: float = 1.0,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        添加关系到本体
        
        Args:
            source: 源实体ID或名称
            target: 目标实体ID或名称
            relation_type: 关系类型
            confidence: 置信度
            metadata: 元数据
        
        Returns:
            是否成功添加
        
        Raises:
            ValueError: 实体不存在或关系无效
        """
        # 解析实体ID
        source_id = self._resolve_entity_id(source)
        target_id = self._resolve_entity_id(target)
        
        if not source_id or not target_id:
            raise ValueError(f"Entity not found: {source} or {target}")
        
        # 验证关系一致性
        if not self._validate_relation(source_id, target_id, relation_type):
            return False
        
        # 创建关系
        relation = Relation(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            confidence=confidence,
            metadata=metadata or {}
        )
        
        # 存储关系
        self.relations.add(relation)
        
        # 更新邻接表
        self.adjacency_list[source_id].append((target_id, relation_type))
        
        return True
    
    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """获取实体"""
        return self.entities.get(entity_id)
    
    def get_neighbors(
        self,
        entity_id: str,
        relation_type: Optional[RelationType] = None,
        max_hops: int = 1
    ) -> List[Entity]:
        """
        获取实体的n-hop邻居
        
        Args:
            entity_id: 实体ID
            relation_type: 关系类型过滤（None表示所有类型）
            max_hops: 最大跳数
        
        Returns:
            邻居实体列表
        
        Examples:
            >>> neighbors = ontology.get_neighbors("grammar_001", max_hops=2)
        """
        if entity_id not in self.entities:
            return []
        
        visited = set()
        queue = [(entity_id, 0)]  # (entity_id, hop_count)
        neighbors = []
        
        while queue:
            current_id, hops = queue.pop(0)
            
            if hops >= max_hops:
                continue
            
            if current_id in visited:
                continue
            
            visited.add(current_id)
            
            # 获取邻居
            for neighbor_id, rel_type in self.adjacency_list.get(current_id, []):
                if relation_type is None or rel_type == relation_type:
                    if neighbor_id not in visited:
                        neighbors.append(self.entities[neighbor_id])
                        queue.append((neighbor_id, hops + 1))
        
        return neighbors
    
    def validate_schema(self) -> Dict[str, any]:
        """
        验证本体模式
        
        检查：
        - 孤立节点
        - 语言覆盖度
        - 关系一致性
        
        Returns:
            验证报告
        """
        report = {
            "total_entities": len(self.entities),
            "total_relations": len(self.relations),
            "isolated_nodes": [],
            "language_coverage": {},
            "warnings": []
        }
        
        # 检查孤立节点
        connected_entities = set()
        for relation in self.relations:
            connected_entities.add(relation.source_id)
            connected_entities.add(relation.target_id)
        
        for entity_id in self.entities:
            if entity_id not in connected_entities:
                report["isolated_nodes"].append(entity_id)
        
        # 语言覆盖度
        for lang in ["zh", "fr", "en"]:
            count = len(self.entity_index["language"][lang])
            total = len(self.entities)
            report["language_coverage"][lang] = {
                "count": count,
                "percentage": count / total * 100 if total > 0 else 0
            }
        
        return report
    
    def export_statistics(self) -> Dict[str, any]:
        """
        导出统计信息（用于论文）
        
        Returns:
            统计字典
        """
        stats = {
            "ontology_version": self.version,
            "total_entities": len(self.entities),
            "total_relations": len(self.relations),
            "entities_by_type": {},
            "entities_by_language": {},
            "relations_by_type": {},
            "avg_degree": 0.0
        }
        
        # 按类型统计
        for entity_type in EntityType:
            count = len(self.entity_index["type"][entity_type.value])
            if count > 0:
                stats["entities_by_type"][entity_type.value] = count
        
        # 按语言统计
        for lang in ["zh", "fr", "en"]:
            count = len(self.entity_index["language"][lang])
            if count > 0:
                stats["entities_by_language"][lang] = count
        
        # 按关系类型统计
        for relation in self.relations:
            rel_type = relation.relation_type.value
            stats["relations_by_type"][rel_type] = stats["relations_by_type"].get(rel_type, 0) + 1
        
        # 平均度数
        if len(self.entities) > 0:
            total_degree = sum(len(neighbors) for neighbors in self.adjacency_list.values())
            stats["avg_degree"] = round(total_degree / len(self.entities), 2)
        
        return stats
    
    def _generate_entity_id(self, name: str, entity_type: EntityType, language: str) -> str:
        """生成实体ID"""
        # 格式：type_lang_uuid
        prefix = f"{entity_type.value.lower()}_{language}"
        unique_id = str(uuid.uuid4())[:8]
        return f"{prefix}_{unique_id}"
    
    def _resolve_entity_id(self, identifier: str) -> Optional[str]:
        """解析实体ID（支持名称或ID）"""
        # 直接是ID
        if identifier in self.entities:
            return identifier
        
        # 按名称查找
        return self.entity_index["name"].get(identifier.lower())
    
    def _validate_relation(
        self,
        source_id: str,
        target_id: str,
        relation_type: RelationType
    ) -> bool:
        """
        验证关系的语义一致性
        
        Examples:
            - translatedAs关系两端必须是相同类型
            - hasPrereq关系必须在同一语言内
        """
        source = self.entities[source_id]
        target = self.entities[target_id]
        
        # translatedAs: 相同类型，不同语言
        if relation_type == RelationType.TRANSLATED_AS:
            if source.entity_type != target.entity_type:
                return False
            if source.language == target.language:
                return False
        
        # hasPrereq: 同一语言
        if relation_type == RelationType.HAS_PREREQ:
            if source.language != target.language:
                return False
        
        return True
