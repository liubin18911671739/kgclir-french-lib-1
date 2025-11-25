#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Language Detection Utilities
语言检测工具

提供语言检测和验证功能。
"""

from typing import Optional, List


SUPPORTED_LANGUAGES = {"zh", "fr", "en"}
LANGUAGE_NAMES = {
    "zh": "Chinese",
    "fr": "French",
    "en": "English"
}


def detect_language(text: str, method: str = "langdetect") -> Optional[str]:
    """
    检测文本语言
    
    Args:
        text: 输入文本
        method: 检测方法 (langdetect|pycld2)
    
    Returns:
        语言代码 (zh/fr/en) 或 None（检测失败）
    
    Examples:
        >>> detect_language("Bonjour le monde")
        'fr'
        >>> detect_language("你好世界")
        'zh'
    
    学术注意：
        语言检测基于n-gram统计模型，准确率随文本长度增加而提升。
        短文本（<50字符）可能检测不准确。
    """
    if not text or len(text.strip()) < 3:
        return None
    
    if method == "langdetect":
        try:
            import langdetect
            
            # langdetect返回ISO 639-1代码
            lang = langdetect.detect(text)
            
            # 映射到支持的语言
            lang_map = {
                "zh-cn": "zh",
                "zh-tw": "zh",
                "zh": "zh",
                "fr": "fr",
                "en": "en"
            }
            
            return lang_map.get(lang)
        
        except ImportError:
            print("Warning: langdetect not installed. Trying pycld2.")
            method = "pycld2"
        except Exception as e:
            print(f"Language detection failed: {e}")
            return None
    
    if method == "pycld2":
        try:
            import pycld2 as cld2
            
            is_reliable, text_bytes_found, details = cld2.detect(text)
            
            if is_reliable:
                lang_code = details[0][1]  # ISO 639-1 code
                
                # 映射到支持的语言
                lang_map = {
                    "zh": "zh",
                    "zh-Hant": "zh",
                    "fr": "fr",
                    "en": "en"
                }
                
                return lang_map.get(lang_code)
        
        except ImportError:
            print("Warning: pycld2 not installed.")
            return None
        except Exception as e:
            print(f"Language detection failed: {e}")
            return None
    
    # 降级：简单启发式检测
    return _heuristic_detect(text)


def _heuristic_detect(text: str) -> Optional[str]:
    """
    启发式语言检测（降级方案）
    
    基于字符集特征进行简单判断。
    
    Args:
        text: 输入文本
    
    Returns:
        语言代码或None
    """
    # 统计不同字符集的字符数
    zh_count = 0
    latin_count = 0
    
    for char in text:
        code_point = ord(char)
        
        # 中文字符范围（简化）
        if 0x4E00 <= code_point <= 0x9FFF:
            zh_count += 1
        # 拉丁字符
        elif (0x0041 <= code_point <= 0x005A) or (0x0061 <= code_point <= 0x007A):
            latin_count += 1
    
    # 判断主要字符集
    if zh_count > latin_count:
        return "zh"
    elif latin_count > 0:
        # 无法区分法语和英语，默认返回英语
        # TODO: 可以通过特征词汇进一步区分
        return "en"
    
    return None


def is_valid_language(lang: str) -> bool:
    """
    检查语言代码是否有效
    
    Args:
        lang: 语言代码
    
    Returns:
        有效返回True
    
    Examples:
        >>> is_valid_language("fr")
        True
        >>> is_valid_language("de")
        False
    """
    return lang in SUPPORTED_LANGUAGES


def get_language_name(lang: str) -> Optional[str]:
    """
    获取语言全名
    
    Args:
        lang: 语言代码
    
    Returns:
        语言全名
    
    Examples:
        >>> get_language_name("fr")
        'French'
    """
    return LANGUAGE_NAMES.get(lang)


def detect_languages_batch(texts: List[str]) -> List[Optional[str]]:
    """
    批量检测文本语言
    
    Args:
        texts: 文本列表
    
    Returns:
        语言代码列表
    """
    return [detect_language(text) for text in texts]


def filter_by_language(
    texts: List[str],
    target_lang: str
) -> List[str]:
    """
    按语言过滤文本
    
    Args:
        texts: 文本列表
        target_lang: 目标语言代码
    
    Returns:
        过滤后的文本列表
    """
    filtered = []
    
    for text in texts:
        detected_lang = detect_language(text)
        if detected_lang == target_lang:
            filtered.append(text)
    
    return filtered
