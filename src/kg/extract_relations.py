#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Relation Extraction Module
关系抽取模块

使用多种策略抽取实体间的关系：
1. 依存句法规则
2. 模式匹配
3. 共现关系

学术参考：
- Dependency-based relation extraction: Fundel et al. (2007)
- Pattern-based methods: Hearst patterns (1992)
"""

import re
from typing import List, Dict, Tuple, Optional, Set
from collections import defaultdict
from dataclasses import dataclass

from ..utils.logger import logger
from .ontology import Relation, RelationType, EntityType


@dataclass
class ExtractedRelation:
    """抽取的关系（临时结构）"""
    source_name: str
    target_name: str
    relation_type: RelationType
    confidence: float = 1.0
    evidence: Optional[str] = None  # 证据文本
    source_method: str = "unknown"  # 抽取方法


class RelationExtractor:
    """
    关系抽取器
    
    从文本中抽取实体间的语义关系。
    
    Examples:
        >>> extractor = RelationExtractor()
        >>> text = "虚拟式翻译为法语subjonctif，属于语法范畴"
        >>> relations = extractor.extract_from_text(text, entities, language="zh")
    """
    
    def __init__(self, load_spacy: bool = True):
        """
        初始化关系抽取器
        
        Args:
            load_spacy: 是否加载spaCy模型（用于依存句法）
        """
        self.spacy_models = {}
        
        if load_spacy:
            self._load_spacy_models()
        
        # 编译关系模式
        self.patterns = self._compile_relation_patterns()
    
    def _load_spacy_models(self):
        """加载spaCy模型"""
        try:
            import spacy
            
            model_map = {
                "fr": "fr_core_news_sm",
                "en": "en_core_web_sm",
                "zh": "zh_core_web_sm"
            }
            
            for lang, model_name in model_map.items():
                try:
                    self.spacy_models[lang] = spacy.load(model_name)
                    logger.info(f"Loaded spaCy model for relation extraction: {model_name}")
                except OSError:
                    logger.warning(f"spaCy model {model_name} not found")
        
        except ImportError:
            logger.warning("spaCy not installed. Dependency-based extraction disabled.")
    
    def _compile_relation_patterns(self) -> Dict[str, List[Tuple[re.Pattern, RelationType]]]:
        """
        编译关系模式
        
        使用正则表达式捕获实体间的关系表达。
        
        Returns:
            {language: [(pattern, relation_type), ...]}
        """
        patterns = {
            "zh": [
                # translatedAs 翻译关系
                (re.compile(r'(.+?)\s*(?:翻译为|译为|对应|等同于)\s*(.+?)(?:[，。；]|$)'), RelationType.TRANSLATED_AS),
                (re.compile(r'(.+?)\s*即\s*(.+?)(?:[，。；]|$)'), RelationType.SAME_AS),
                
                # belongsTo 从属关系
                (re.compile(r'(.+?)\s*(?:属于|归属于|是|为)\s*(.+?)(?:[，。；]|$)'), RelationType.BELONGS_TO),
                (re.compile(r'(.+?)\s*(?:的|之)\s*(.+?)'), RelationType.BELONGS_TO),
                
                # hasPrereq 前置关系
                (re.compile(r'(?:学习|掌握)\s*(.+?)\s*(?:之前|前).*?(?:需要|应该|必须).*?(.+?)(?:[，。；]|$)'), RelationType.HAS_PREREQ),
                (re.compile(r'(.+?)\s*是\s*(.+?)\s*的基础'), RelationType.HAS_PREREQ),
                
                # covers 覆盖关系
                (re.compile(r'(.+?)\s*(?:包含|涵盖|包括)\s*(.+?)(?:[，。；]|$)'), RelationType.COVERS),
                
                # tests 测试关系
                (re.compile(r'(.+?)\s*(?:测试|检验|考查)\s*(.+?)(?:[，。；]|$)'), RelationType.TESTS),
            ],
            
            "fr": [
                # translatedAs
                (re.compile(r'(.+?)\s+(?:se traduit par|signifie|correspond à|équivaut à)\s+(.+?)(?:[,\.\;]|$)', re.I), RelationType.TRANSLATED_AS),
                (re.compile(r'(.+?)\s+(?:c\'est-à-dire|soit)\s+(.+?)(?:[,\.\;]|$)', re.I), RelationType.SAME_AS),
                
                # belongsTo
                (re.compile(r'(.+?)\s+(?:appartient à|est un|fait partie de)\s+(.+?)(?:[,\.\;]|$)', re.I), RelationType.BELONGS_TO),
                (re.compile(r'(.+?)\s+de\s+(.+?)(?:[,\.\;]|$)'), RelationType.BELONGS_TO),
                
                # hasPrereq
                (re.compile(r'avant\s+(?:de\s+)?(.+?),\s*(?:il faut|on doit)\s+(.+?)(?:[,\.\;]|$)', re.I), RelationType.HAS_PREREQ),
                (re.compile(r'(.+?)\s+(?:nécessite|requiert|exige)\s+(.+?)(?:[,\.\;]|$)', re.I), RelationType.HAS_PREREQ),
                
                # covers
                (re.compile(r'(.+?)\s+(?:comprend|inclut|contient)\s+(.+?)(?:[,\.\;]|$)', re.I), RelationType.COVERS),
                
                # tests
                (re.compile(r'(.+?)\s+(?:teste|évalue|vérifie)\s+(.+?)(?:[,\.\;]|$)', re.I), RelationType.TESTS),
            ],
            
            "en": [
                # translatedAs
                (re.compile(r'(.+?)\s+(?:translates to|means|corresponds to|is equivalent to)\s+(.+?)(?:[,\.\;]|$)', re.I), RelationType.TRANSLATED_AS),
                (re.compile(r'(.+?)\s+(?:i\.e\.|that is)\s+(.+?)(?:[,\.\;]|$)', re.I), RelationType.SAME_AS),
                
                # belongsTo
                (re.compile(r'(.+?)\s+(?:belongs to|is a|is part of)\s+(.+?)(?:[,\.\;]|$)', re.I), RelationType.BELONGS_TO),
                (re.compile(r'(.+?)\s+of\s+(.+?)(?:[,\.\;]|$)'), RelationType.BELONGS_TO),
                
                # hasPrereq
                (re.compile(r'before\s+(.+?),\s*(?:you must|one must|you should)\s+(.+?)(?:[,\.\;]|$)', re.I), RelationType.HAS_PREREQ),
                (re.compile(r'(.+?)\s+(?:requires|needs|presupposes)\s+(.+?)(?:[,\.\;]|$)', re.I), RelationType.HAS_PREREQ),
                
                # covers
                (re.compile(r'(.+?)\s+(?:includes|contains|comprises)\s+(.+?)(?:[,\.\;]|$)', re.I), RelationType.COVERS),
                
                # tests
                (re.compile(r'(.+?)\s+(?:tests|evaluates|assesses)\s+(.+?)(?:[,\.\;]|$)', re.I), RelationType.TESTS),
            ]
        }
        
        return patterns
    
    def extract_from_text(
        self,
        text: str,
        entities: List[str],  # 已知实体名称列表
        language: str = "en"
    ) -> List[ExtractedRelation]:
        """
        从文本中抽取关系
        
        Args:
            text: 输入文本
            entities: 已知实体名称列表（用于匹配）
            language: 语言代码
        
        Returns:
            抽取的关系列表
        """
        relations = []
        
        # 1. 基于模式的关系抽取
        pattern_relations = self._extract_by_patterns(text, entities, language)
        relations.extend(pattern_relations)
        
        # 2. 基于依存句法的关系抽取
        if language in self.spacy_models:
            dep_relations = self._extract_by_dependency(text, entities, language)
            relations.extend(dep_relations)
        
        # 3. 基于共现的关系抽取
        cooccur_relations = self._extract_by_cooccurrence(text, entities, language)
        relations.extend(cooccur_relations)
        
        # 去重
        relations = self._deduplicate_relations(relations)
        
        logger.info(f"Extracted {len(relations)} relations from {language} text")
        
        return relations
    
    def _extract_by_patterns(
        self,
        text: str,
        entities: List[str],
        language: str
    ) -> List[ExtractedRelation]:
        """基于模式匹配的关系抽取"""
        relations = []
        
        if language not in self.patterns:
            return relations
        
        # 创建实体到位置的映射（用于快速查找）
        entity_positions = {}
        for entity in entities:
            for match in re.finditer(re.escape(entity), text, re.I):
                entity_positions[match.span()] = entity
        
        # 应用关系模式
        for pattern, relation_type in self.patterns[language]:
            for match in pattern.finditer(text):
                source_text = match.group(1).strip()
                target_text = match.group(2).strip()
                
                # 匹配到已知实体
                source_entity = self._find_matching_entity(source_text, entities)
                target_entity = self._find_matching_entity(target_text, entities)
                
                if source_entity and target_entity:
                    relations.append(ExtractedRelation(
                        source_name=source_entity,
                        target_name=target_entity,
                        relation_type=relation_type,
                        confidence=0.85,
                        evidence=match.group(0),
                        source_method="pattern"
                    ))
        
        return relations
    
    def _extract_by_dependency(
        self,
        text: str,
        entities: List[str],
        language: str
    ) -> List[ExtractedRelation]:
        """
        基于依存句法的关系抽取
        
        使用依存关系路径识别实体间的语义关系。
        
        学术参考：
        Fundel et al. (2007). RelEx—Relation extraction using dependency parse trees.
        """
        relations = []
        
        nlp = self.spacy_models[language]
        doc = nlp(text)
        
        # 构建实体到token的映射
        entity_tokens = {}
        for ent_name in entities:
            for token in doc:
                if token.text.lower() == ent_name.lower():
                    entity_tokens[token.i] = ent_name
        
        # 分析依存关系
        for token in doc:
            if token.i not in entity_tokens:
                continue
            
            source_entity = entity_tokens[token.i]
            
            # 查找依存关系路径
            for child in token.children:
                if child.i in entity_tokens:
                    target_entity = entity_tokens[child.i]
                    
                    # 根据依存关系类型推断语义关系
                    relation_type = self._infer_relation_from_dep(token.dep_, child.dep_)
                    
                    if relation_type:
                        relations.append(ExtractedRelation(
                            source_name=source_entity,
                            target_name=target_entity,
                            relation_type=relation_type,
                            confidence=0.7,
                            evidence=token.sent.text if token.sent else None,
                            source_method="dependency"
                        ))
        
        return relations
    
    def _extract_by_cooccurrence(
        self,
        text: str,
        entities: List[str],
        language: str,
        window_size: int = 50
    ) -> List[ExtractedRelation]:
        """
        基于共现的关系抽取
        
        在指定窗口内共现的实体可能存在关系。
        
        Args:
            text: 文本
            entities: 实体列表
            language: 语言
            window_size: 词窗口大小
        """
        relations = []
        
        # 查找所有实体在文本中的位置
        entity_occurrences = defaultdict(list)
        for entity in entities:
            for match in re.finditer(re.escape(entity), text, re.I):
                entity_occurrences[entity].append(match.start())
        
        # 检查共现
        for entity1 in entities:
            for pos1 in entity_occurrences[entity1]:
                for entity2 in entities:
                    if entity1 == entity2:
                        continue
                    
                    for pos2 in entity_occurrences[entity2]:
                        # 检查是否在窗口内
                        if abs(pos1 - pos2) <= window_size:
                            # 推断为belongsTo关系（低置信度）
                            relations.append(ExtractedRelation(
                                source_name=entity1,
                                target_name=entity2,
                                relation_type=RelationType.BELONGS_TO,
                                confidence=0.3,  # 低置信度
                                evidence=text[min(pos1, pos2):max(pos1, pos2) + len(entity2)],
                                source_method="cooccurrence"
                            ))
        
        return relations
    
    def _find_matching_entity(self, text: str, entities: List[str]) -> Optional[str]:
        """在实体列表中查找匹配的实体"""
        text_lower = text.lower().strip()
        
        for entity in entities:
            if entity.lower() == text_lower:
                return entity
            
            # 部分匹配
            if text_lower in entity.lower() or entity.lower() in text_lower:
                return entity
        
        return None
    
    def _infer_relation_from_dep(self, dep1: str, dep2: str) -> Optional[RelationType]:
        """
        从依存关系推断语义关系
        
        Args:
            dep1: 第一个token的依存标签
            dep2: 第二个token的依存标签
        
        Returns:
            推断的关系类型
        """
        # 简化的映射规则（实际应用中需要更复杂的规则）
        if dep1 in ["nsubj", "nsubjpass"] and dep2 in ["dobj", "pobj"]:
            return RelationType.BELONGS_TO
        
        if dep1 == "prep" and dep2 == "pobj":
            return RelationType.BELONGS_TO
        
        return None
    
    def _deduplicate_relations(
        self,
        relations: List[ExtractedRelation]
    ) -> List[ExtractedRelation]:
        """
        去重关系
        
        策略：基于(source, target, relation_type)三元组
        保留置信度最高的
        """
        relation_dict = {}
        
        for relation in relations:
            key = (
                relation.source_name.lower(),
                relation.target_name.lower(),
                relation.relation_type
            )
            
            if key not in relation_dict:
                relation_dict[key] = relation
            else:
                # 保留置信度更高的
                if relation.confidence > relation_dict[key].confidence:
                    relation_dict[key] = relation
        
        return list(relation_dict.values())
    
    def extract_from_corpus(
        self,
        corpus: List[Dict[str, any]],
        entities: List[str],
        text_field: str = "text",
        language_field: str = "language"
    ) -> List[ExtractedRelation]:
        """从语料库批量抽取关系"""
        all_relations = []
        
        for i, doc in enumerate(corpus):
            text = doc.get(text_field, "")
            language = doc.get(language_field, "en")
            
            relations = self.extract_from_text(text, entities, language)
            all_relations.extend(relations)
            
            if (i + 1) % 100 == 0:
                logger.info(f"Processed {i+1}/{len(corpus)} documents for relation extraction")
        
        # 全局去重
        all_relations = self._deduplicate_relations(all_relations)
        
        logger.info(f"Total extracted relations: {len(all_relations)}")
        
        return all_relations
