"""
数据质量控制模块

提供数据质量检查、验证和清洗功能，包括：
- 自动质量检查和评分
- 数据验证和一致性检查
- 数据清洗和标准化
- 质量报告和改进建议
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
import hashlib
import sqlite3
from datetime import datetime
import re

# 本地导入
from ..utils.io import load_json, save_json
from ..utils.text_norm import TextNormalizer
from ..utils.lang_detect import LanguageDetector
from .processors import ProcessedText, ExtractedMetadata, TextProcessor

# 设置日志
logger = logging.getLogger(__name__)

@dataclass
class QualityMetric:
    """质量指标"""
    name: str
    value: float
    threshold: float
    passed: bool
    description: str
    weight: float = 1.0

@dataclass
class QualityReport:
    """质量报告"""
    record_id: str
    overall_score: float
    metrics: List[QualityMetric]
    issues: List[Dict[str, Any]]
    recommendations: List[str]
    processing_timestamp: str
    data_type: str = "unknown"

@dataclass
class ValidationRule:
    """验证规则"""
    name: str
    description: str
    pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    required_fields: List[str] = None
    custom_validator: Optional[str] = None

    def __post_init__(self):
        if self.required_fields is None:
            self.required_fields = []

class BaseQualityController(ABC):
    """质量控制器基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.rules = self._load_validation_rules()
        self.text_processor = TextProcessor(config.get('text_processing', {}))
        self.quality_thresholds = config.get('quality_thresholds', {
            'overall': 0.7,
            'content': 0.6,
            'metadata': 0.5,
            'structure': 0.6
        })

    def _load_validation_rules(self) -> Dict[str, ValidationRule]:
        """加载验证规则"""
        rules = {}

        # 默认验证规则
        default_rules = {
            'title_length': ValidationRule(
                name='title_length',
                description='标题长度检查',
                min_length=5,
                max_length=200
            ),
            'content_length': ValidationRule(
                name='content_length',
                description='内容长度检查',
                min_length=50,
                max_length=100000
            ),
            'language_detection': ValidationRule(
                name='language_detection',
                description='语言检测置信度',
                pattern=r'^[a-z]{2}$'
            ),
            'email_format': ValidationRule(
                name='email_format',
                description='邮箱格式验证',
                pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            ),
            'doi_format': ValidationRule(
                name='doi_format',
                description='DOI格式验证',
                pattern=r'^10\.\d+/'
            ),
            'url_format': ValidationRule(
                name='url_format',
                description='URL格式验证',
                pattern=r'^https?://'
            )
        }

        rules.update(default_rules)

        # 从配置文件加载自定义规则
        custom_rules = self.config.get('validation_rules', {})
        for rule_name, rule_config in custom_rules.items():
            rules[rule_name] = ValidationRule(**rule_config)

        return rules

    @abstractmethod
    def assess_quality(self, data: Any, **kwargs) -> QualityReport:
        """评估数据质量"""
        pass

    @abstractmethod
    def validate_data(self, data: Any, rules: List[str] = None) -> Tuple[bool, List[Dict[str, Any]]]:
        """验证数据"""
        pass

class QualityValidator(BaseQualityController):
    """数据质量验证器"""

    def assess_quality(self, data: Dict[str, Any], **kwargs) -> QualityReport:
        """全面评估数据质量"""
        record_id = data.get('id', 'unknown')
        metrics = []
        issues = []
        recommendations = []

        # 内容质量指标
        content_metrics = self._assess_content_quality(data)
        metrics.extend(content_metrics)

        # 元数据质量指标
        metadata_metrics = self._assess_metadata_quality(data)
        metrics.extend(metadata_metrics)

        # 结构质量指标
        structure_metrics = self._assess_structure_quality(data)
        metrics.extend(structure_metrics)

        # 一致性质量指标
        consistency_metrics = self._assess_consistency_quality(data)
        metrics.extend(consistency_metrics)

        # 收集问题和建议
        for metric in metrics:
            if not metric.passed:
                issues.append({
                    'type': 'quality_threshold',
                    'metric': metric.name,
                    'value': metric.value,
                    'threshold': metric.threshold,
                    'description': f"{metric.description}: {metric.value:.2f} < {metric.threshold:.2f}"
                })

        # 生成改进建议
        recommendations = self._generate_recommendations(issues, data)

        # 计算总体分数
        overall_score = self._calculate_overall_score(metrics)

        return QualityReport(
            record_id=record_id,
            overall_score=overall_score,
            metrics=metrics,
            issues=issues,
            recommendations=recommendations,
            processing_timestamp=datetime.now().isoformat(),
            data_type=data.get('type', 'unknown')
        )

    def validate_data(self, data: Dict[str, Any], rules: List[str] = None) -> Tuple[bool, List[Dict[str, Any]]]:
        """根据规则验证数据"""
        if rules is None:
            rules = list(self.rules.keys())

        validation_results = []
        is_valid = True

        for rule_name in rules:
            if rule_name not in self.rules:
                logger.warning(f"未知的验证规则: {rule_name}")
                continue

            rule = self.rules[rule_name]
            result = self._apply_validation_rule(data, rule)
            validation_results.append(result)

            if not result['passed']:
                is_valid = False

        return is_valid, validation_results

    def _assess_content_quality(self, data: Dict[str, Any]) -> List[QualityMetric]:
        """评估内容质量"""
        metrics = []

        # 内容长度指标
        content = data.get('content', '') or data.get('abstract', '')
        if content:
            content_length = len(content)
            length_score = min(content_length / 1000, 1.0)  # 标准化到0-1
            metrics.append(QualityMetric(
                name='content_length',
                value=length_score,
                threshold=0.3,
                passed=length_score >= 0.3,
                description='内容长度质量分数',
                weight=0.15
            ))

            # 语言质量指标
            try:
                processed = self.text_processor.process(content)
                language_score = processed.confidence
                metrics.append(QualityMetric(
                    name='language_quality',
                    value=language_score,
                    threshold=0.7,
                    passed=language_score >= 0.7,
                    description='语言检测置信度',
                    weight=0.1
                ))
            except Exception as e:
                logger.error(f"语言质量评估失败: {e}")
                metrics.append(QualityMetric(
                    name='language_quality',
                    value=0.0,
                    threshold=0.7,
                    passed=False,
                    description='语言检测失败',
                    weight=0.1
                ))

            # 结构质量指标（句子和段落）
            sentences = re.split(r'[.!?。！？]+', content)
            if sentences:
                avg_sentence_length = sum(len(s.strip()) for s in sentences) / len(sentences)
                structure_score = min(avg_sentence_length / 50, 1.0)
                metrics.append(QualityMetric(
                    name='content_structure',
                    value=structure_score,
                    threshold=0.4,
                    passed=structure_score >= 0.4,
                    description='内容结构质量分数',
                    weight=0.1
                ))

        # 标题质量指标
        title = data.get('title', '')
        if title:
            title_length = len(title)
            title_score = 1.0 if 5 <= title_length <= 200 else 0.5
            metrics.append(QualityMetric(
                name='title_quality',
                value=title_score,
                threshold=0.8,
                passed=title_score >= 0.8,
                description='标题质量分数',
                weight=0.1
            ))

        return metrics

    def _assess_metadata_quality(self, data: Dict[str, Any]) -> List[QualityMetric]:
        """评估元数据质量"""
        metrics = []

        # 作者信息完整性
        authors = data.get('authors', [])
        if authors:
            author_score = min(len(authors) / 3, 1.0)  # 假设3个或更多作者为完整
        else:
            author_score = 0.0

        metrics.append(QualityMetric(
            name='author_completeness',
            value=author_score,
            threshold=0.3,
            passed=author_score >= 0.3,
            description='作者信息完整性',
            weight=0.08
        ))

        # 关键词质量
        keywords = data.get('keywords', [])
        if keywords:
            keyword_score = min(len(keywords) / 5, 1.0)  # 假设5个或更多关键词为良好
        else:
            keyword_score = 0.0

        metrics.append(QualityMetric(
            name='keyword_quality',
            value=keyword_score,
            threshold=0.2,
            passed=keyword_score >= 0.2,
            description='关键词质量分数',
            weight=0.06
        ))

        # 发表日期质量
        pub_date = data.get('publish_date') or data.get('publish_year')
        date_score = 1.0 if pub_date else 0.0
        metrics.append(QualityMetric(
            name='date_quality',
            value=date_score,
            threshold=0.5,
            passed=date_score >= 0.5,
            description='发表日期质量',
            weight=0.05
        ))

        # DOI和URL质量
        doi = data.get('doi')
        url = data.get('url')
        identifier_score = 0.0

        if doi:
            identifier_score += 0.5
        if url:
            identifier_score += 0.3

        metrics.append(QualityMetric(
            name='identifier_quality',
            value=identifier_score,
            threshold=0.3,
            passed=identifier_score >= 0.3,
            description='标识符质量（DOI/URL）',
            weight=0.06
        ))

        return metrics

    def _assess_structure_quality(self, data: Dict[str, Any]) -> List[QualityMetric]:
        """评估数据结构质量"""
        metrics = []

        # 必需字段完整性
        required_fields = ['id', 'title', 'content']
        missing_fields = [field for field in required_fields if not data.get(field)]
        completeness_score = (len(required_fields) - len(missing_fields)) / len(required_fields)

        metrics.append(QualityMetric(
            name='required_fields_completeness',
            value=completeness_score,
            threshold=0.8,
            passed=completeness_score >= 0.8,
            description='必需字段完整性',
            weight=0.15
        ))

        # 数据类型一致性
        type_consistency_score = self._check_data_type_consistency(data)
        metrics.append(QualityMetric(
            name='type_consistency',
            value=type_consistency_score,
            threshold=0.9,
            passed=type_consistency_score >= 0.9,
            description='数据类型一致性',
            weight=0.1
        ))

        # 字段格式一致性
        format_consistency_score = self._check_format_consistency(data)
        metrics.append(QualityMetric(
            name='format_consistency',
            value=format_consistency_score,
            threshold=0.8,
            passed=format_consistency_score >= 0.8,
            description='字段格式一致性',
            weight=0.05
        ))

        return metrics

    def _assess_consistency_quality(self, data: Dict[str, Any]) -> List[QualityMetric]:
        """评估数据一致性质量"""
        metrics = []

        # 语言一致性
        declared_lang = data.get('language')
        if declared_lang:
            content = data.get('content', '') or data.get('abstract', '')
            if content:
                try:
                    detected_lang, confidence = self.text_processor.language_detector.detect(content)
                    lang_consistency = 1.0 if declared_lang == detected_lang else 0.5
                except:
                    lang_consistency = 0.0
            else:
                lang_consistency = 0.5  # 无法验证
        else:
            lang_consistency = 0.3  # 未声明语言

        metrics.append(QualityMetric(
            name='language_consistency',
            value=lang_consistency,
            threshold=0.7,
            passed=lang_consistency >= 0.7,
            description='语言一致性',
            weight=0.08
        ))

        # 日期一致性
        date_fields = ['publish_date', 'created_date', 'modified_date']
        dates = [data.get(field) for field in date_fields if data.get(field)]
        date_consistency = self._check_date_consistency(dates)

        metrics.append(QualityMetric(
            name='date_consistency',
            value=date_consistency,
            threshold=0.8,
            passed=date_consistency >= 0.8,
            description='日期字段一致性',
            weight=0.05
        ))

        # 长度合理性
        length_consistency = self._check_length_reasonableness(data)
        metrics.append(QualityMetric(
            name='length_reasonableness',
            value=length_consistency,
            threshold=0.6,
            passed=length_consistency >= 0.6,
            description='长度字段合理性',
            weight=0.07
        ))

        return metrics

    def _apply_validation_rule(self, data: Dict[str, Any], rule: ValidationRule) -> Dict[str, Any]:
        """应用单个验证规则"""
        result = {
            'rule_name': rule.name,
            'description': rule.description,
            'passed': True,
            'error': None,
            'field_values': {}
        }

        try:
            # 检查必需字段
            for field in rule.required_fields:
                field_value = data.get(field)
                result['field_values'][field] = field_value

                if field_value is None or field_value == '':
                    result['passed'] = False
                    result['error'] = f"Missing required field: {field}"
                    return result

            # 检查长度限制
            if rule.min_length or rule.max_length:
                for field_name in ['title', 'content', 'abstract']:
                    field_value = data.get(field_name, '')
                    if field_value:
                        length = len(field_value)
                        if rule.min_length and length < rule.min_length:
                            result['passed'] = False
                            result['error'] = f"{field_name} length {length} < minimum {rule.min_length}"
                            return result
                        if rule.max_length and length > rule.max_length:
                            result['passed'] = False
                            result['error'] = f"{field_name} length {length} > maximum {rule.max_length}"
                            return result

            # 检查模式匹配
            if rule.pattern:
                pattern_fields = {
                    'email_format': ['email'],
                    'doi_format': ['doi'],
                    'url_format': ['url'],
                    'language_detection': ['language']
                }

                fields_to_check = pattern_fields.get(rule.name, [])
                for field in fields_to_check:
                    field_value = str(data.get(field, ''))
                    if field_value and not re.match(rule.pattern, field_value):
                        result['passed'] = False
                        result['error'] = f"{field} '{field_value}' does not match pattern {rule.pattern}"
                        return result

        except Exception as e:
            result['passed'] = False
            result['error'] = f"Validation error: {str(e)}"

        return result

    def _check_data_type_consistency(self, data: Dict[str, Any]) -> float:
        """检查数据类型一致性"""
        expected_types = {
            'id': str,
            'title': str,
            'authors': list,
            'keywords': list,
            'publish_date': str,
            'word_count': int,
            'page_count': int
        }

        consistency_count = 0
        total_checks = 0

        for field, expected_type in expected_types.items():
            if field in data:
                total_checks += 1
                if isinstance(data[field], expected_type):
                    consistency_count += 1
                elif expected_type == list and data[field] is None:
                    # None值对于列表字段是可接受的
                    consistency_count += 1

        return consistency_count / total_checks if total_checks > 0 else 1.0

    def _check_format_consistency(self, data: Dict[str, Any]) -> float:
        """检查格式一致性"""
        format_checks = []

        # DOI格式
        doi = data.get('doi')
        if doi:
            format_checks.append(re.match(r'^10\.\d+/', doi) is not None)
        else:
            format_checks.append(True)  # 可选字段

        # URL格式
        url = data.get('url')
        if url:
            format_checks.append(url.startswith(('http://', 'https://')))
        else:
            format_checks.append(True)  # 可选字段

        # 邮箱格式
        email = data.get('email')
        if email:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            format_checks.append(re.match(email_pattern, email) is not None)
        else:
            format_checks.append(True)  # 可选字段

        return sum(format_checks) / len(format_checks) if format_checks else 1.0

    def _check_date_consistency(self, dates: List[str]) -> float:
        """检查日期一致性"""
        if not dates:
            return 1.0

        try:
            parsed_dates = []
            for date_str in dates:
                if date_str:
                    # 尝试解析日期
                    parsed_dates.append(self._parse_date(date_str))

            if len(parsed_dates) < 2:
                return 1.0

            # 检查日期逻辑性
            for i in range(len(parsed_dates) - 1):
                if parsed_dates[i] > parsed_dates[i + 1]:
                    return 0.5  # 日期顺序问题

            return 1.0

        except Exception:
            return 0.5  # 解析失败

    def _check_length_reasonableness(self, data: Dict[str, Any]) -> float:
        """检查长度字段合理性"""
        reasonableness_checks = []

        # 标题长度
        title = data.get('title', '')
        if title:
            reasonableness_checks.append(5 <= len(title) <= 200)

        # 内容长度
        content = data.get('content', '')
        if content:
            reasonableness_checks.append(10 <= len(content) <= 1000000)

        # 作者数量
        authors = data.get('authors', [])
        if authors:
            reasonableness_checks.append(1 <= len(authors) <= 50)

        # 关键词数量
        keywords = data.get('keywords', [])
        if keywords:
            reasonableness_checks.append(1 <= len(keywords) <= 20)

        return sum(reasonableness_checks) / len(reasonableness_checks) if reasonableness_checks else 1.0

    def _parse_date(self, date_str: str) -> datetime:
        """解析日期字符串"""
        date_formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%d/%m/%Y',
            '%Y',
            '%Y-%m',
            '%m/%Y'
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # 如果无法解析，返回当前日期作为默认值
        return datetime.now()

    def _calculate_overall_score(self, metrics: List[QualityMetric]) -> float:
        """计算总体质量分数"""
        if not metrics:
            return 0.0

        total_weight = sum(metric.weight for metric in metrics)
        weighted_score = sum(metric.value * metric.weight for metric in metrics)

        return weighted_score / total_weight if total_weight > 0 else 0.0

    def _generate_recommendations(self, issues: List[Dict[str, Any]], data: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        for issue in issues:
            metric = issue.get('metric', '')

            if metric == 'content_length':
                recommendations.append("建议增加内容长度，提供更详细的信息")
            elif metric == 'language_quality':
                recommendations.append("建议检查文本语言，确保内容清晰可读")
            elif metric == 'content_structure':
                recommendations.append("建议改善内容结构，增加句子和段落的划分")
            elif metric == 'title_quality':
                recommendations.append("建议优化标题长度和描述性")
            elif metric == 'author_completeness':
                recommendations.append("建议补充作者信息，提供完整的作者列表")
            elif metric == 'keyword_quality':
                recommendations.append("建议增加相关关键词，提高内容可发现性")
            elif metric == 'date_quality':
                recommendations.append("建议添加发表日期信息")
            elif metric == 'identifier_quality':
                recommendations.append("建议添加DOI或URL等标识符")
            elif metric == 'required_fields_completeness':
                recommendations.append("请补充缺失的必需字段")
            elif metric == 'language_consistency':
                recommendations.append("建议检查语言声明与实际内容的一致性")

        # 通用建议
        if len(recommendations) == 0:
            recommendations.append("数据质量良好，继续保持")

        return recommendations

class DataCleaner(BaseQualityController):
    """数据清洗器"""

    def assess_quality(self, data: Dict[str, Any], **kwargs) -> QualityReport:
        """评估质量（委托给QualityValidator）"""
        validator = QualityValidator(self.config)
        return validator.assess_quality(data, **kwargs)

    def validate_data(self, data: Dict[str, Any], rules: List[str] = None) -> Tuple[bool, List[Dict[str, Any]]]:
        """验证数据（委托给QualityValidator）"""
        validator = QualityValidator(self.config)
        return validator.validate_data(data, rules)

    def clean_data(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """清洗数据"""
        cleaned_data = data.copy()
        cleaning_actions = []

        # 清洗标题
        if 'title' in cleaned_data:
            original_title = cleaned_data['title']
            cleaned_title = self._clean_text(original_title)
            if cleaned_title != original_title:
                cleaned_data['title'] = cleaned_title
                cleaning_actions.append({
                    'field': 'title',
                    'action': 'text_cleaning',
                    'original': original_title,
                    'cleaned': cleaned_title
                })

        # 清洗内容
        for field in ['content', 'abstract']:
            if field in cleaned_data and cleaned_data[field]:
                original_content = cleaned_data[field]
                cleaned_content = self._clean_text(original_content)
                if cleaned_content != original_content:
                    cleaned_data[field] = cleaned_content
                    cleaning_actions.append({
                        'field': field,
                        'action': 'text_cleaning',
                        'original': original_content[:100] + '...',
                        'cleaned': cleaned_content[:100] + '...'
                    })

        # 清洗作者列表
        if 'authors' in cleaned_data:
            original_authors = cleaned_data['authors']
            cleaned_authors = self._clean_author_list(original_authors)
            if cleaned_authors != original_authors:
                cleaned_data['authors'] = cleaned_authors
                cleaning_actions.append({
                    'field': 'authors',
                    'action': 'list_cleaning',
                    'original': original_authors,
                    'cleaned': cleaned_authors
                })

        # 清洗关键词列表
        if 'keywords' in cleaned_data:
            original_keywords = cleaned_data['keywords']
            cleaned_keywords = self._clean_keyword_list(original_keywords)
            if cleaned_keywords != original_keywords:
                cleaned_data['keywords'] = cleaned_keywords
                cleaning_actions.append({
                    'field': 'keywords',
                    'action': 'list_cleaning',
                    'original': original_keywords,
                    'cleaned': cleaned_keywords
                })

        # 清洗URL
        if 'url' in cleaned_data:
            original_url = cleaned_data['url']
            cleaned_url = self._clean_url(original_url)
            if cleaned_url != original_url:
                cleaned_data['url'] = cleaned_url
                cleaning_actions.append({
                    'field': 'url',
                    'action': 'url_cleaning',
                    'original': original_url,
                    'cleaned': cleaned_url
                })

        # 标准化日期格式
        for date_field in ['publish_date', 'created_date', 'modified_date']:
            if date_field in cleaned_data:
                original_date = cleaned_data[date_field]
                cleaned_date = self._standardize_date(original_date)
                if cleaned_date != original_date:
                    cleaned_data[date_field] = cleaned_date
                    cleaning_actions.append({
                        'field': date_field,
                        'action': 'date_standardization',
                        'original': original_date,
                        'cleaned': cleaned_date
                    })

        # 删除空字段
        cleaned_data, removed_fields = self._remove_empty_fields(cleaned_data)
        for field in removed_fields:
            cleaning_actions.append({
                'field': field,
                'action': 'field_removal',
                'original': None,
                'cleaned': None
            })

        return cleaned_data, cleaning_actions

    def _clean_text(self, text: str) -> str:
        """清洗文本"""
        if not text:
            return text

        # 使用文本规范化器
        normalizer = TextNormalizer()
        cleaned = normalizer.normalize(text)

        # 额外的清洗步骤
        # 移除多余的空白字符
        cleaned = re.sub(r'\s+', ' ', cleaned)

        # 移除特殊字符（保留基本标点）
        cleaned = re.sub(r'[^\w\s\u4e00-\u9fff.,!?;:()[\]{}"\'-]', '', cleaned)

        # 移除首尾空白
        cleaned = cleaned.strip()

        return cleaned

    def _clean_author_list(self, authors: List[str]) -> List[str]:
        """清洗作者列表"""
        if not authors:
            return authors

        cleaned_authors = []
        for author in authors:
            if author and isinstance(author, str):
                # 清洗每个作者名字
                cleaned_author = self._clean_text(author)
                # 移除数字和特殊字符（保留基本标点）
                cleaned_author = re.sub(r'[0-9]', '', cleaned_author)
                cleaned_author = re.sub(r'[^\w\s\u4e00-\u9fff.,\-]', '', cleaned_author)
                cleaned_author = cleaned_author.strip()

                if cleaned_author and len(cleaned_author) > 1:
                    cleaned_authors.append(cleaned_author)

        # 去重
        return list(dict.fromkeys(cleaned_authors))

    def _clean_keyword_list(self, keywords: List[str]) -> List[str]:
        """清洗关键词列表"""
        if not keywords:
            return keywords

        cleaned_keywords = []
        for keyword in keywords:
            if keyword and isinstance(keyword, str):
                # 清洗每个关键词
                cleaned_keyword = self._clean_text(keyword)
                # 移除特殊字符
                cleaned_keyword = re.sub(r'[^\w\s\u4e00-\u9fff\-]', '', cleaned_keyword)
                cleaned_keyword = cleaned_keyword.strip()

                if cleaned_keyword and len(cleaned_keyword) > 1:
                    cleaned_keywords.append(cleaned_keyword)

        # 去重并限制长度
        unique_keywords = list(dict.fromkeys(cleaned_keywords))
        return [kw for kw in unique_keywords if len(kw) <= 50]

    def _clean_url(self, url: str) -> str:
        """清洗URL"""
        if not url:
            return url

        url = url.strip()

        # 确保有协议
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # 移除常见的URL问题
        url = re.sub(r'\s+', '', url)  # 移除空格
        url = url.strip('.,;!?"\'')  # 移除尾随标点

        return url

    def _standardize_date(self, date_str: str) -> str:
        """标准化日期格式"""
        if not date_str:
            return date_str

        try:
            # 尝试解析并标准化为 ISO 格式
            parsed_date = self._parse_date(date_str)
            return parsed_date.strftime('%Y-%m-%d')
        except Exception:
            return date_str  # 如果无法解析，保持原样

    def _remove_empty_fields(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """删除空字段"""
        cleaned_data = {}
        removed_fields = []

        for key, value in data.items():
            if value is None:
                removed_fields.append(key)
            elif isinstance(value, str) and not value.strip():
                removed_fields.append(key)
            elif isinstance(value, list) and not value:
                removed_fields.append(key)
            else:
                cleaned_data[key] = value

        return cleaned_data, removed_fields

class DataQualityController:
    """数据质量控制主控制器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.validator = QualityValidator(config.get('validation', {}))
        self.cleaner = DataCleaner(config.get('cleaning', {}))
        self.db_path = config.get('database_path', 'data/quality_control.db')
        self._init_database()

    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建质量报告表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quality_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT NOT NULL,
                overall_score REAL,
                issues_count INTEGER,
                recommendations_count INTEGER,
                report_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建清洗记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cleaning_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT NOT NULL,
                cleaning_actions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def assess_and_clean(self, data: Dict[str, Any]) -> Tuple[Dict[str, Any], QualityReport, List[Dict[str, Any]]]:
        """评估并清洗数据"""
        # 生成唯一ID
        record_id = data.get('id', f"record_{hashlib.md5(str(data).encode()).hexdigest()[:8]}")

        # 清洗数据
        cleaned_data, cleaning_actions = self.cleaner.clean_data(data)

        # 评估质量
        quality_report = self.validator.assess_quality(cleaned_data)

        # 保存记录
        self._save_quality_report(record_id, quality_report)
        if cleaning_actions:
            self._save_cleaning_record(record_id, cleaning_actions)

        return cleaned_data, quality_report, cleaning_actions

    def batch_assess(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量评估数据质量"""
        results = []

        for i, data in enumerate(data_list):
            try:
                record_id = data.get('id', f"batch_{i}")
                quality_report = self.validator.assess_quality(data)

                result = {
                    'record_id': record_id,
                    'quality_score': quality_report.overall_score,
                    'issues_count': len(quality_report.issues),
                    'passed_threshold': quality_report.overall_score >= self.quality_thresholds['overall'],
                    'recommendations': quality_report.recommendations[:3]  # 取前3个建议
                }
                results.append(result)

                # 保存报告
                self._save_quality_report(record_id, quality_report)

            except Exception as e:
                logger.error(f"批量评估失败 - 记录 {i}: {e}")
                results.append({
                    'record_id': data.get('id', f"batch_{i}"),
                    'quality_score': 0.0,
                    'issues_count': 1,
                    'passed_threshold': False,
                    'recommendations': ["评估过程中发生错误"],
                    'error': str(e)
                })

        return results

    def get_quality_summary(self, limit: int = 100) -> Dict[str, Any]:
        """获取质量摘要统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 基本统计
        cursor.execute('''
            SELECT
                COUNT(*) as total_records,
                AVG(overall_score) as avg_score,
                MIN(overall_score) as min_score,
                MAX(overall_score) as max_score,
                COUNT(CASE WHEN overall_score >= ? THEN 1 END) as high_quality_count
            FROM quality_reports
            ORDER BY created_at DESC
            LIMIT ?
        ''', (self.quality_thresholds['overall'], limit))

        stats = cursor.fetchone()

        # 按分数分布统计
        cursor.execute('''
            SELECT
                CASE
                    WHEN overall_score >= 0.9 THEN '优秀 (≥0.9)'
                    WHEN overall_score >= 0.7 THEN '良好 (0.7-0.9)'
                    WHEN overall_score >= 0.5 THEN '一般 (0.5-0.7)'
                    ELSE '较差 (<0.5)'
                END as quality_level,
                COUNT(*) as count
            FROM quality_reports
            ORDER BY created_at DESC
            LIMIT ?
            GROUP BY quality_level
        ''', (limit,))

        distribution = dict(cursor.fetchall())

        conn.close()

        return {
            'total_records': stats[0] or 0,
            'average_score': round(stats[1] or 0, 3),
            'min_score': round(stats[2] or 0, 3),
            'max_score': round(stats[3] or 0, 3),
            'high_quality_count': stats[4] or 0,
            'quality_distribution': distribution,
            'threshold': self.quality_thresholds['overall']
        }

    def _save_quality_report(self, record_id: str, report: QualityReport):
        """保存质量报告"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        report_data = json.dumps(asdict(report), ensure_ascii=False, indent=2)

        cursor.execute('''
            INSERT INTO quality_reports
            (record_id, overall_score, issues_count, recommendations_count, report_data)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            record_id,
            report.overall_score,
            len(report.issues),
            len(report.recommendations),
            report_data
        ))

        conn.commit()
        conn.close()

    def _save_cleaning_record(self, record_id: str, cleaning_actions: List[Dict[str, Any]]):
        """保存清洗记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        actions_json = json.dumps(cleaning_actions, ensure_ascii=False, indent=2)

        cursor.execute('''
            INSERT INTO cleaning_records (record_id, cleaning_actions)
            VALUES (?, ?)
        ''', (record_id, actions_json))

        conn.commit()
        conn.close()

# 导出主要类
__all__ = [
    'DataQualityController',
    'QualityValidator',
    'DataCleaner',
    'QualityReport',
    'QualityMetric',
    'ValidationRule'
]