#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Text Normalization Utilities
文本规范化工具

提供文本预处理功能：
- 文本清洗
- 停用词移除
- 词形还原（Lemmatization）
- 分词
"""

import re
import string
from typing import List, Optional, Set
import unicodedata


# 停用词列表（简化版，实际应从文件加载）
STOPWORDS = {
    "zh": {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个"},
    "fr": {"le", "la", "les", "un", "une", "des", "de", "du", "à", "au", "aux", "et", "ou", "mais", "donc", "car", "ni", "que", "qui", "quoi", "dont", "où"},
    "en": {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from", "as", "is", "was", "are", "be", "been", "being"}
}


def normalize_text(
    text: str,
    lowercase: bool = True,
    remove_punctuation: bool = False,
    remove_extra_spaces: bool = True,
    normalize_unicode: bool = True
) -> str:
    """
    文本规范化
    
    Args:
        text: 输入文本
        lowercase: 是否转小写
        remove_punctuation: 是否移除标点符号
        remove_extra_spaces: 是否移除多余空格
        normalize_unicode: 是否规范化Unicode字符
    
    Returns:
        规范化后的文本
    
    Examples:
        >>> normalize_text("  Hello,  World!  ", lowercase=True, remove_punctuation=True)
        'hello world'
    
    学术注意：
        文本规范化是NLP预处理的标准步骤，参考：
        - Manning & Schütze (1999). Foundations of Statistical NLP
    """
    if not text:
        return ""
    
    # Unicode规范化（NFKC: 兼容性分解+组合）
    if normalize_unicode:
        text = unicodedata.normalize('NFKC', text)
    
    # 转小写
    if lowercase:
        text = text.lower()
    
    # 移除标点符号
    if remove_punctuation:
        # 保留中文标点
        text = re.sub(r'[{}]'.format(re.escape(string.punctuation)), ' ', text)
    
    # 移除多余空格
    if remove_extra_spaces:
        text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def remove_stopwords(
    tokens: List[str],
    language: str = "en",
    custom_stopwords: Optional[Set[str]] = None
) -> List[str]:
    """
    移除停用词
    
    Args:
        tokens: 分词列表
        language: 语言代码 (zh/fr/en)
        custom_stopwords: 自定义停用词集合
    
    Returns:
        过滤后的分词列表
    
    Examples:
        >>> tokens = ["the", "cat", "is", "sleeping"]
        >>> remove_stopwords(tokens, language="en")
        ['cat', 'sleeping']
    """
    if language not in STOPWORDS:
        # 不支持的语言，返回原始tokens
        return tokens
    
    stopwords = STOPWORDS[language]
    
    # 合并自定义停用词
    if custom_stopwords:
        stopwords = stopwords | custom_stopwords
    
    return [token for token in tokens if token.lower() not in stopwords]


def lemmatize(
    text: str,
    language: str = "en"
) -> str:
    """
    词形还原
    
    使用spaCy进行词形还原（Lemmatization）
    
    Args:
        text: 输入文本
        language: 语言代码
    
    Returns:
        词形还原后的文本
    
    Examples:
        >>> lemmatize("running cats", language="en")
        'run cat'
    
    注意：
        需要安装对应语言的spaCy模型
    """
    try:
        import spacy
        
        # 加载spaCy模型
        model_map = {
            "en": "en_core_web_sm",
            "fr": "fr_core_news_sm",
            "zh": "zh_core_web_sm"
        }
        
        if language not in model_map:
            return text
        
        try:
            nlp = spacy.load(model_map[language])
        except OSError:
            print(f"Warning: spaCy model {model_map[language]} not found. Returning original text.")
            return text
        
        doc = nlp(text)
        lemmas = [token.lemma_ for token in doc]
        
        return " ".join(lemmas)
    
    except ImportError:
        print("Warning: spaCy not installed. Returning original text.")
        return text


def clean_text(text: str, language: str = "en") -> str:
    """
    综合文本清洗
    
    执行完整的文本清洗流程：
    1. 规范化
    2. 移除URL
    3. 移除HTML标签
    4. 移除特殊字符
    
    Args:
        text: 输入文本
        language: 语言代码
    
    Returns:
        清洗后的文本
    """
    if not text:
        return ""
    
    # 移除URL
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 移除邮箱
    text = re.sub(r'\S+@\S+', '', text)
    
    # 移除多余的换行符
    text = re.sub(r'\n+', ' ', text)
    
    # 基本规范化
    text = normalize_text(text, lowercase=True, remove_extra_spaces=True)
    
    return text


def tokenize_simple(text: str, language: str = "en") -> List[str]:
    """
    简单分词（基于空格和标点）
    
    Args:
        text: 输入文本
        language: 语言代码
    
    Returns:
        分词列表
    
    注意：
        中文需要使用jieba分词，此函数仅适用于西方语言
    """
    if language == "zh":
        # 中文分词需要jieba
        try:
            import jieba
            return list(jieba.cut(text))
        except ImportError:
            print("Warning: jieba not installed for Chinese tokenization.")
            return text.split()
    
    # 西方语言：基于空格和标点分词
    text = normalize_text(text, lowercase=True)
    tokens = re.findall(r'\b\w+\b', text)
    
    return tokens


def truncate_text(text: str, max_length: int, strategy: str = "head") -> str:
    """
    截断文本到指定长度
    
    Args:
        text: 输入文本
        max_length: 最大字符数
        strategy: 截断策略 (head|tail|middle)
    
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    
    if strategy == "head":
        return text[:max_length]
    elif strategy == "tail":
        return text[-max_length:]
    elif strategy == "middle":
        half = max_length // 2
        return text[:half] + text[-half:]
    else:
        return text[:max_length]


def remove_accents(text: str) -> str:
    """
    移除重音符号
    
    Args:
        text: 输入文本（如法语、西班牙语等）
    
    Returns:
        移除重音后的文本
    
    Examples:
        >>> remove_accents("français")
        'francais'
    """
    nfkd_form = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])
