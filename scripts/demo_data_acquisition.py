#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据获取系统演示脚本

展示核心功能，包括数据记录创建、文本处理、质量控制和任务调度
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Any

# 模拟数据记录类
class DataRecord:
    def __init__(self, id: str, title: str, authors: List[str], abstract: str,
                 content: str, source: str, **kwargs):
        self.id = id
        self.title = title
        self.authors = authors or []
        self.abstract = abstract
        self.content = content
        self.source = source
        self.url = kwargs.get('url')
        self.doi = kwargs.get('doi')
        self.publish_date = kwargs.get('publish_date')
        self.language = kwargs.get('language')
        self.keywords = kwargs.get('keywords', [])
        self.category = kwargs.get('category')
        self.metadata = kwargs.get('metadata', {})

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'authors': self.authors,
            'abstract': self.abstract,
            'content': self.content,
            'source': self.source,
            'url': self.url,
            'doi': self.doi,
            'publish_date': self.publish_date,
            'language': self.language,
            'keywords': self.keywords,
            'category': self.category,
            'metadata': self.metadata
        }

# 模拟连接器
class MockAcademicConnector:
    """模拟学术数据库连接器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = "Mock Academic Connector"

    def search(self, query: str, max_results: int = 10, **kwargs) -> List[DataRecord]:
        """模拟搜索功能"""
        print(f"🔍 搜索查询: {query}")
        print(f"📊 最大结果数: {max_results}")

        # 模拟搜索延迟
        time.sleep(0.5)

        # 生成模拟结果
        mock_results = []
        for i in range(min(max_results, 5)):
            record = DataRecord(
                id=f"mock_{query}_{i+1:03d}",
                title=f"{query}相关研究 {i+1}",
                authors=[f"研究者{i+1}", f"合作者{i+1}"],
                abstract=f"这是关于{query}的模拟研究摘要。本研究探讨了{query}在现代科技中的应用和挑战。",
                content=f"这是{query}相关研究的详细内容。" * 20,  # 生成较长的内容
                source="模拟学术数据库",
                publish_date=f"202{i}-0{i+1}-01",
                language="zh" if "中文" in query else "en",
                keywords=[query, "研究", "学术"],
                category="计算机科学"
            )
            mock_results.append(record)

        print(f"✅ 找到 {len(mock_results)} 条结果")
        return mock_results

# 模拟文本处理器
class MockTextProcessor:
    """模拟文本处理器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = "Mock Text Processor"

    def process(self, text: str, language: str = None) -> Dict[str, Any]:
        """模拟文本处理"""
        if not text:
            return self._empty_result()

        # 模拟处理延迟
        time.sleep(0.1)

        # 语言检测
        if language is None:
            chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
            language = "zh" if chinese_chars > len(text) * 0.1 else "en"

        # 文本统计
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        words = text.split()

        # 模拟实体提取
        entities = [
            {'text': '机器学习', 'label': 'TECHNOLOGY', 'confidence': 0.9},
            {'text': '深度学习', 'label': 'TECHNOLOGY', 'confidence': 0.85}
        ] if "学习" in text else []

        # 计算质量分数
        quality_score = self._calculate_quality_score(text, language)

        result = {
            'original_text': text,
            'language': language,
            'confidence': 0.9 if language else 0.5,
            'sentence_count': len(sentences),
            'word_count': len(words),
            'entities': entities,
            'quality_score': quality_score,
            'processing_time': '0.1s'
        }

        return result

    def _calculate_quality_score(self, text: str, language: str) -> float:
        """计算质量分数"""
        if not text.strip():
            return 0.0

        score = 0.0

        # 长度分数 (30%)
        length_score = min(len(text) / 1000, 1.0) * 0.3
        score += length_score

        # 结构分数 (25%)
        sentences = text.split('.')
        if sentences:
            avg_sentence_length = sum(len(s.strip()) for s in sentences) / len(sentences)
            structure_score = min(avg_sentence_length / 50, 1.0) * 0.25
            score += structure_score

        # 词汇多样性分数 (25%)
        words = text.split()
        if words:
            unique_words = len(set(word.lower() for word in words))
            diversity_score = min(unique_words / len(words), 1.0) * 0.25
            score += diversity_score

        # 基础分数 (20%)
        score += 0.2

        return min(score, 1.0)

    def _empty_result(self):
        return {
            'original_text': '',
            'language': 'unknown',
            'confidence': 0.0,
            'sentence_count': 0,
            'word_count': 0,
            'entities': [],
            'quality_score': 0.0,
            'processing_time': '0s'
        }

# 模拟质量控制
class MockQualityController:
    """模拟数据质量控制器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.quality_threshold = config.get('quality_threshold', 0.7)

    def assess_and_clean(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """模拟质量评估和清洗"""
        print(f"🔍 评估数据质量...")

        # 模拟处理延迟
        time.sleep(0.2)

        # 计算质量指标
        title = data.get('title', '')
        content = data.get('content', '')
        authors = data.get('authors', [])

        # 标题质量
        title_score = 1.0 if 5 <= len(title) <= 200 else 0.5

        # 内容质量
        content_score = min(len(content) / 500, 1.0)

        # 作者完整性
        author_score = min(len(authors) / 2, 1.0)

        # 语言一致性
        language_score = 0.9  # 假设检测正确

        # 总体分数
        overall_score = (title_score * 0.2 + content_score * 0.4 +
                        author_score * 0.2 + language_score * 0.2)

        # 生成质量报告
        quality_report = {
            'overall_score': overall_score,
            'title_quality': title_score,
            'content_quality': content_score,
            'author_completeness': author_score,
            'language_consistency': language_score,
            'passed_threshold': overall_score >= self.quality_threshold
        }

        # 清洗操作
        cleaning_actions = []
        cleaned_data = data.copy()

        # 标题清洗
        if title.strip() != title:
            cleaned_data['title'] = title.strip()
            cleaning_actions.append('清理标题多余空白')

        # 作者列表清洗
        if any('  ' in str(author) for author in authors):
            cleaned_data['authors'] = [str(author).strip() for author in authors]
            cleaning_actions.append('清理作者姓名空白')

        print(f"📊 质量分数: {overall_score:.2f}")
        print(f"✅ 通过阈值: {quality_report['passed_threshold']}")

        return {
            'cleaned_data': cleaned_data,
            'quality_report': quality_report,
            'cleaning_actions': cleaning_actions
        }

# 模拟任务调度器
class MockTaskScheduler:
    """模拟任务调度器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.tasks = {}
        self.running = False

    def add_task(self, task_id: str, task_func, **kwargs):
        """添加任务"""
        self.tasks[task_id] = {
            'func': task_func,
            'kwargs': kwargs,
            'status': 'pending',
            'created_at': datetime.now()
        }
        print(f"📋 添加任务: {task_id}")

    def run_task(self, task_id: str):
        """运行指定任务"""
        if task_id not in self.tasks:
            print(f"❌ 任务不存在: {task_id}")
            return

        task = self.tasks[task_id]
        print(f"🚀 开始执行任务: {task_id}")

        # 更新状态
        task['status'] = 'running'
        task['started_at'] = datetime.now()

        try:
            # 执行任务
            result = task['func'](**task['kwargs'])

            # 更新状态
            task['status'] = 'completed'
            task['completed_at'] = datetime.now()
            task['result'] = result

            print(f"✅ 任务完成: {task_id}")
            return result

        except Exception as e:
            task['status'] = 'failed'
            task['error'] = str(e)
            print(f"❌ 任务失败: {task_id}, 错误: {e}")
            return None

def demo_data_acquisition():
    """演示数据获取功能"""
    print("=" * 60)
    print("🎯 数据获取系统演示")
    print("=" * 60)

    # 1. 初始化组件
    print("\n📦 1. 初始化组件...")
    connector = MockAcademicConnector({'name': 'Demo Connector'})
    processor = MockTextProcessor({'language_detection': True})
    quality_controller = MockQualityController({'quality_threshold': 0.7})

    # 2. 数据获取
    print("\n🔍 2. 数据获取演示...")
    queries = ["机器学习", "深度学习", "natural language processing"]
    all_records = []

    for query in queries:
        print(f"\n--- 搜索: {query} ---")
        records = connector.search(query, max_results=3)
        all_records.extend(records)

    print(f"\n📊 总共获取 {len(all_records)} 条记录")

    # 3. 文本处理演示
    print("\n⚙️ 3. 文本处理演示...")
    if all_records:
        sample_record = all_records[0]
        processed = processor.process(sample_record.content, sample_record.language)

        print(f"📝 处理示例记录: {sample_record.id}")
        print(f"🌐 检测语言: {processed['language']}")
        print(f"🔤 词汇数量: {processed['word_count']}")
        print(f"📄 句子数量: {processed['sentence_count']}")
        print(f"🏷️  实体数量: {len(processed['entities'])}")
        print(f"⭐ 质量分数: {processed['quality_score']:.2f}")

    # 4. 质量控制演示
    print("\n🛡️ 4. 数据质量控制演示...")
    if all_records:
        sample_data = all_records[0].to_dict()
        quality_result = quality_controller.assess_and_clean(sample_data)

        print(f"📊 质量评估结果:")
        for metric, score in quality_result['quality_report'].items():
            if metric != 'passed_threshold':
                print(f"  {metric}: {score:.2f}")

        if quality_result['cleaning_actions']:
            print(f"🧹 执行的清洗操作:")
            for action in quality_result['cleaning_actions']:
                print(f"  - {action}")

    # 5. 任务调度演示
    print("\n⏰ 5. 任务调度演示...")
    scheduler = MockTaskScheduler({'max_tasks': 3})

    # 定义任务
    def search_task(query: str, max_results: int):
        return connector.search(query, max_results)

    def process_task(records: List[DataRecord]):
        results = []
        for record in records[:2]:  # 只处理前2条
            processed = processor.process(record.content, record.language)
            results.append({
                'id': record.id,
                'quality_score': processed['quality_score']
            })
        return results

    # 添加任务
    scheduler.add_task('search_ai', search_task, query="人工智能", max_results=5)
    scheduler.add_task('process_records', process_task, records=all_records)

    # 执行任务
    print("\n执行任务...")
    search_result = scheduler.run_task('search_ai')
    if search_result:
        print(f"搜索任务返回 {len(search_result)} 条记录")

    process_result = scheduler.run_task('process_records')
    if process_result:
        print(f"处理任务完成，处理了 {len(process_result)} 条记录")

    # 6. 统计总结
    print("\n📈 6. 统计总结...")
    print(f"总获取记录数: {len(all_records)}")

    if all_records:
        languages = {}
        sources = {}

        for record in all_records:
            lang = record.language or 'unknown'
            source = record.source
            languages[lang] = languages.get(lang, 0) + 1
            sources[source] = sources.get(source, 0) + 1

        print(f"语言分布: {languages}")
        print(f"数据源分布: {sources}")

        # 处理所有记录的质量分数
        all_scores = []
        for record in all_records:
            processed = processor.process(record.content, record.language)
            all_scores.append(processed['quality_score'])

        if all_scores:
            avg_quality = sum(all_scores) / len(all_scores)
            high_quality_count = sum(1 for score in all_scores if score >= 0.7)
            print(f"平均质量分数: {avg_quality:.2f}")
            print(f"高质量记录数: {high_quality_count}/{len(all_scores)}")

    print("\n✨ 演示完成！")
    print("=" * 60)

def demo_multilingual_processing():
    """演示多语言处理功能"""
    print("\n🌍 多语言处理演示")
    print("-" * 40)

    processor = MockTextProcessor({'language_detection': True})

    texts = [
        ("机器学习是人工智能的一个重要分支", "zh"),
        ("Machine learning is a subset of artificial intelligence", "en"),
        ("L'apprentissage automatique est un sous-ensemble de l'intelligence artificielle", "fr")
    ]

    for text, expected_lang in texts:
        result = processor.process(text)
        print(f"\n文本: {text}")
        print(f"预期语言: {expected_lang}")
        print(f"检测语言: {result['language']}")
        print(f"置信度: {result['confidence']:.2f}")
        print(f"质量分数: {result['quality_score']:.2f}")

def demo_quality_control_detailed():
    """演示详细的质量控制功能"""
    print("\n🛡️ 详细质量控制演示")
    print("-" * 40)

    controller = MockQualityController({'quality_threshold': 0.7})

    # 测试不同质量的数据
    test_cases = [
        {
            'name': '高质量数据',
            'data': {
                'id': 'high_quality_001',
                'title': '机器学习在教育领域的创新应用研究',
                'content': '本研究探讨了机器学习技术在现代教育系统中的创新应用，包括个性化学习路径推荐、智能评估系统和教学效果分析等多个方面。通过大量的实证研究和数据分析，我们验证了机器学习技术在提升教学质量和学习效率方面的显著效果。' * 3,
                'authors': ['张三', '李四', '王五'],
                'language': 'zh'
            }
        },
        {
            'name': '低质量数据',
            'data': {
                'id': 'low_quality_001',
                'title': '短',
                'content': '内容太少。',
                'authors': [],
                'language': 'zh'
            }
        }
    ]

    for test_case in test_cases:
        print(f"\n--- {test_case['name']} ---")
        result = controller.assess_and_clean(test_case['data'])

        report = result['quality_report']
        print(f"总体分数: {report['overall_score']:.2f}")
        print(f"标题质量: {report['title_quality']:.2f}")
        print(f"内容质量: {report['content_quality']:.2f}")
        print(f"作者完整性: {report['author_completeness']:.2f}")
        print(f"通过阈值: {'是' if report['passed_threshold'] else '否'}")

if __name__ == "__main__":
    print("🎯 KG-CLIR 数据获取系统演示")
    print("本演示展示了数据获取系统的核心功能")
    print("包括数据连接、文本处理、质量控制和任务调度")

    try:
        # 主演示
        demo_data_acquisition()

        # 额外演示
        demo_multilingual_processing()
        demo_quality_control_detailed()

        print("\n🎉 所有演示完成！")

    except KeyboardInterrupt:
        print("\n⏹️  演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()