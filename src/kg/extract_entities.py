#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Entity Extraction Module
实体抽取模块

混合策略：规则（正则表达式）+ NLP模型（spaCy + jieba）

支持中法英三语处理：
- 中文：jieba分词 + 词性标注
- 法语/英语：spaCy NER + 依存句法

学术注意：
混合策略提升召回率（rule: 精确率高；NLP: 召回率高）
参考：Named Entity Recognition in Low-Resource Languages (ACL 2020)
"""

import re
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass

from ..utils.logger import logger
from ..utils.text_norm import normalize_text, clean_text
from .ontology import Entity, EntityType


@dataclass
class ExtractedEntity:
    """抽取的实体（临时结构，用于后续去重和规范化）"""
    name: str
    entity_type: EntityType
    language: str
    confidence: float = 1.0
    context: Optional[str] = None  # 出现的上下文
    source: str = "unknown"  # 抽取来源：spacy/jieba/rule


class EntityExtractor:
    """
    实体抽取器
    
    使用混合策略从文本中抽取实体：
    1. 基于规则的模式匹配（高精确率）
    2. 基于NLP模型的抽取（高召回率）
    3. 去重和规范化
    
    Examples:
        >>> extractor = EntityExtractor(languages=["zh", "fr", "en"])
        >>> entities = extractor.extract_from_text("法语虚拟式subjonctif是重要的语法概念", language="zh")
    """
    
    def __init__(self, languages: List[str] = ["zh", "fr", "en"], load_models: bool = True):
        """
        初始化实体抽取器
        
        Args:
            languages: 支持的语言列表
            load_models: 是否加载NLP模型
        """
        self.languages = languages
        self.spacy_models = {}
        self.jieba_loaded = False
        
        if load_models:
            self._load_models()
        
        # 编译正则模式
        self.patterns = self._compile_patterns()
        
        # 停用词（过滤低质量实体）
        self.stopwords = {
            "zh": {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "个"},
            "fr": {"le", "la", "les", "un", "une", "des", "de", "du", "à", "et", "ou", "est"},
            "en": {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "is", "are"}
        }
    
    def _load_models(self):
        """加载NLP模型"""
        # 加载spaCy模型
        try:
            import spacy
            
            model_map = {
                "fr": "fr_core_news_sm",
                "en": "en_core_web_sm",
                "zh": "zh_core_web_sm"
            }
            
            for lang in self.languages:
                if lang in model_map:
                    try:
                        self.spacy_models[lang] = spacy.load(model_map[lang])
                        logger.info(f"Loaded spaCy model: {model_map[lang]}")
                    except OSError:
                        logger.warning(f"spaCy model {model_map[lang]} not found. Please install: python -m spacy download {model_map[lang]}")
        
        except ImportError:
            logger.warning("spaCy not installed. NLP-based extraction will be disabled.")
        
        # 加载jieba（中文）
        if "zh" in self.languages:
            try:
                import jieba
                import jieba.posseg as pseg
                self.jieba_loaded = True
                logger.info("Loaded jieba for Chinese tokenization")
            except ImportError:
                logger.warning("jieba not installed. Chinese extraction will be limited.")
    
    def _compile_patterns(self) -> Dict[str, List[Tuple[re.Pattern, EntityType]]]:
        """
        编译正则表达式模式
        
        Returns:
            {language: [(pattern, entity_type), ...]}
        """
        patterns = {
            "fr": [
                # 语法概念
                (re.compile(r'\b(subjonctif|conditionnel|impératif|participe|infinitif|indicatif|gérondif)\b', re.I), EntityType.GRAMMAR),
                (re.compile(r'\b(passé composé|imparfait|plus-que-parfait|futur simple|futur antérieur)\b', re.I), EntityType.GRAMMAR),
                
                # 课程章节
                (re.compile(r'\b(chapitre|leçon|unité)\s+(\d+|[IVX]+)\b', re.I), EntityType.COURSE),
                
                # CEFR等级
                (re.compile(r'\b([ABC][12])\b'), EntityType.LEVEL),
            ],
            
            "en": [
                # 语法概念
                (re.compile(r'\b(subjunctive|conditional|imperative|participle|infinitive|indicative|gerund)\b', re.I), EntityType.GRAMMAR),
                (re.compile(r'\b(present perfect|past perfect|future perfect|present continuous)\b', re.I), EntityType.GRAMMAR),
                
                # 课程章节
                (re.compile(r'\b(chapter|lesson|unit)\s+(\d+|[IVX]+)\b', re.I), EntityType.COURSE),
                
                # CEFR等级
                (re.compile(r'\b([ABC][12])\b'), EntityType.LEVEL),
            ],
            
            "zh": [
                # 语法概念
                (re.compile(r'(虚拟式|条件式|命令式|分词|不定式|陈述式|副动词)'), EntityType.GRAMMAR),
                (re.compile(r'(复合过去时|未完成过去时|愈过去时|简单将来时|先将来时)'), EntityType.GRAMMAR),
                
                # 课程章节
                (re.compile(r'(第\s*[一二三四五六七八九十\d]+\s*[章课节])'), EntityType.COURSE),
                
                # 水平等级
                (re.compile(r'([ABC][12]|初级|中级|高级)'), EntityType.LEVEL),
            ]
        }
        
        return patterns
    
    def extract_from_text(
        self,
        text: str,
        language: str,
        min_length: int = 2
    ) -> List[ExtractedEntity]:
        """
        从文本中抽取实体
        
        Args:
            text: 输入文本
            language: 语言代码
            min_length: 最小实体长度（字符）
        
        Returns:
            抽取的实体列表
        """
        if not text or language not in self.languages:
            return []
        
        # 文本清洗
        text = clean_text(text, language)
        
        entities = []
        
        # 1. 基于规则的抽取
        rule_entities = self._extract_by_rules(text, language)
        entities.extend(rule_entities)
        
        # 2. 基于NLP模型的抽取
        if language in self.spacy_models:
            nlp_entities = self._extract_by_spacy(text, language)
            entities.extend(nlp_entities)
        
        if language == "zh" and self.jieba_loaded:
            jieba_entities = self._extract_by_jieba(text)
            entities.extend(jieba_entities)
        
        # 3. 过滤和去重
        entities = self._filter_entities(entities, min_length)
        entities = self._deduplicate_entities(entities)
        
        logger.info(f"Extracted {len(entities)} entities from {language} text (length: {len(text)})")
        
        return entities
    
    def _extract_by_rules(self, text: str, language: str) -> List[ExtractedEntity]:
        """基于规则的实体抽取"""
        entities = []
        
        if language not in self.patterns:
            return entities
        
        for pattern, entity_type in self.patterns[language]:
            for match in pattern.finditer(text):
                name = match.group(0).strip()
                
                entities.append(ExtractedEntity(
                    name=name,
                    entity_type=entity_type,
                    language=language,
                    confidence=0.95,  # 规则抽取高置信度
                    context=text[max(0, match.start()-20):min(len(text), match.end()+20)],
                    source="rule"
                ))
        
        return entities
    
    def _extract_by_spacy(self, text: str, language: str) -> List[ExtractedEntity]:
        """基于spaCy的实体抽取"""
        entities = []
        
        nlp = self.spacy_models[language]
        doc = nlp(text)
        
        # 抽取命名实体
        for ent in doc.ents:
            # 映射spaCy实体类型到FLO实体类型
            entity_type = self._map_spacy_label(ent.label_)
            
            if entity_type:
                entities.append(ExtractedEntity(
                    name=ent.text,
                    entity_type=entity_type,
                    language=language,
                    confidence=0.8,
                    context=ent.sent.text if ent.sent else None,
                    source="spacy"
                ))
        
        # 抽取名词和动词（作为潜在的词汇实体）
        for token in doc:
            if token.pos_ in ["NOUN", "VERB", "ADJ"] and len(token.text) >= 3:
                # 词形还原
                lemma = token.lemma_
                
                # 判断是否为专业术语（简单启发式）
                if self._is_technical_term(lemma, language):
                    entities.append(ExtractedEntity(
                        name=lemma,
                        entity_type=EntityType.WORD,
                        language=language,
                        confidence=0.6,
                        source="spacy"
                    ))
        
        return entities
    
    def _extract_by_jieba(self, text: str) -> List[ExtractedEntity]:
        """基于jieba的实体抽取（中文）"""
        import jieba.posseg as pseg
        
        entities = []
        
        # 词性标注
        words = pseg.cut(text)
        
        for word, flag in words:
            # 保留名词、动词、形容词
            if flag.startswith(('n', 'v', 'a')) and len(word) >= 2:
                # 过滤停用词
                if word.lower() not in self.stopwords.get("zh", set()):
                    entities.append(ExtractedEntity(
                        name=word,
                        entity_type=EntityType.WORD,
                        language="zh",
                        confidence=0.7,
                        source="jieba"
                    ))
        
        return entities
    
    def _map_spacy_label(self, label: str) -> Optional[EntityType]:
        """映射spaCy实体标签到FLO实体类型"""
        mapping = {
            "ORG": EntityType.REFERENCE,  # 组织 -> 参考资料
            "PERSON": None,  # 人名暂不保留
            "GPE": EntityType.CULTURE,  # 地理政治实体 -> 文化
            "PRODUCT": EntityType.MEDIA,  # 产品 -> 媒体
            "WORK_OF_ART": EntityType.MEDIA,  # 艺术作品 -> 媒体
            "EVENT": EntityType.CULTURE,  # 事件 -> 文化
        }
        
        return mapping.get(label)
    
    def _is_technical_term(self, term: str, language: str) -> bool:
        """
        判断是否为专业术语（简单启发式）
        
        启发式规则：
        1. 长度适中（3-20字符）
        2. 非停用词
        3. 可选：包含特定后缀/前缀
        """
        if len(term) < 3 or len(term) > 20:
            return False
        
        if term.lower() in self.stopwords.get(language, set()):
            return False
        
        # 法语专业术语特征（示例）
        if language == "fr":
            technical_suffixes = ["-tion", "-ment", "-isme", "-ique"]
            if any(term.endswith(suffix) for suffix in technical_suffixes):
                return True
        
        return False
    
    def _filter_entities(
        self,
        entities: List[ExtractedEntity],
        min_length: int
    ) -> List[ExtractedEntity]:
        """过滤低质量实体"""
        filtered = []
        
        for entity in entities:
            # 长度过滤
            if len(entity.name) < min_length:
                continue
            
            # 停用词过滤
            if entity.name.lower() in self.stopwords.get(entity.language, set()):
                continue
            
            # 纯数字过滤
            if entity.name.isdigit():
                continue
            
            # 纯标点过滤
            if all(not c.isalnum() for c in entity.name):
                continue
            
            filtered.append(entity)
        
        return filtered
    
    def _deduplicate_entities(
        self,
        entities: List[ExtractedEntity]
    ) -> List[ExtractedEntity]:
        """
        去重实体
        
        策略：基于(name.lower(), entity_type, language)三元组去重
        保留置信度最高的
        """
        entity_dict = {}
        
        for entity in entities:
            key = (entity.name.lower(), entity.entity_type, entity.language)
            
            if key not in entity_dict:
                entity_dict[key] = entity
            else:
                # 保留置信度更高的
                if entity.confidence > entity_dict[key].confidence:
                    entity_dict[key] = entity
        
        return list(entity_dict.values())
    
    def extract_from_corpus(
        self,
        corpus: List[Dict[str, str]],
        text_field: str = "text",
        language_field: str = "language"
    ) -> List[ExtractedEntity]:
        """
        从语料库批量抽取实体
        
        Args:
            corpus: 语料列表，每个元素为字典
            text_field: 文本字段名
            language_field: 语言字段名
        
        Returns:
            所有抽取的实体
        """
        all_entities = []
        
        for i, doc in enumerate(corpus):
            text = doc.get(text_field, "")
            language = doc.get(language_field, "en")
            
            entities = self.extract_from_text(text, language)
            all_entities.extend(entities)
            
            if (i + 1) % 100 == 0:
                logger.info(f"Processed {i+1}/{len(corpus)} documents")
        
        # 全局去重
        all_entities = self._deduplicate_entities(all_entities)
        
        logger.info(f"Total extracted entities: {len(all_entities)}")
        
        return all_entities


def convert_to_ontology_entities(
    extracted_entities: List[ExtractedEntity]
) -> List[Entity]:
    """
    将抽取的实体转换为本体实体
    
    Args:
        extracted_entities: 抽取的实体列表
    
    Returns:
        本体实体列表
    """
    from .ontology import Entity
    import uuid
    
    ontology_entities = []
    
    for ext_entity in extracted_entities:
        # 生成实体ID
        entity_id = f"{ext_entity.entity_type.value.lower()}_{ext_entity.language}_{str(uuid.uuid4())[:8]}"
        
        # 创建本体实体
        entity = Entity(
            entity_id=entity_id,
            name=ext_entity.name,
            entity_type=ext_entity.entity_type,
            language=ext_entity.language,
            metadata={
                "confidence": ext_entity.confidence,
                "source": ext_entity.source,
                "context": ext_entity.context
            }
        )
        
        ontology_entities.append(entity)
    
    return ontology_entities
