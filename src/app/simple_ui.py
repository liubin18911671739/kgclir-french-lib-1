#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
极简界面选项

为不熟悉复杂界面的用户提供简单的单页面应用。
包含搜索框、结果展示、基本设置和帮助文档。

Author: KG-CLIR Team
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import streamlit as st
import pandas as pd
import time

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 项目内部模块
from src.app.data_manager import create_data_manager
from src.app.knowledge_viewer import load_default_knowledge_graph
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SimpleUI:
    """极简界面类"""

    def __init__(self):
        self.data_storage = None
        self.kg_viewer = None
        self.init_components()

    def init_components(self):
        """初始化组件"""
        try:
            self.data_storage = create_data_manager()
            self.kg_viewer = load_default_knowledge_graph()
        except Exception as e:
            logger.error(f"组件初始化失败: {e}")

    def render(self):
        """渲染极简界面"""
        # 页面配置
        st.set_page_config(
            page_title="KG-CLIR 简易搜索",
            page_icon="🔍",
            layout="centered",
            initial_sidebar_state="collapsed"
        )

        # 自定义CSS - 移动端友好
        st.markdown("""
        <style>
            .simple-header {
                text-align: center;
                color: #2c3e50;
                margin-bottom: 2rem;
            }
            .search-container {
                max-width: 600px;
                margin: 0 auto;
                padding: 1rem;
            }
            .result-card {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 1rem;
                margin-bottom: 1rem;
                background-color: #fafafa;
            }
            .help-section {
                background-color: #f0f8ff;
                border-left: 4px solid #3498db;
                padding: 1rem;
                margin: 1rem 0;
                border-radius: 4px;
            }
            @media (max-width: 768px) {
                .search-container {
                    padding: 0.5rem;
                }
                .result-card {
                    padding: 0.75rem;
                }
            }
        </style>
        """, unsafe_allow_html=True)

        # 标题
        st.markdown("""
        <div class="simple-header">
            <h1>🔍 KG-CLIR 简易搜索</h1>
            <p>多语种知识图谱跨语言检索系统</p>
        </div>
        """, unsafe_allow_html=True)

        # 主内容区域
        self.render_main_content()

        # 页脚
        self.render_footer()

    def render_main_content(self):
        """渲染主内容"""
        # 搜索区域
        self.render_search_section()

        # 快速统计
        self.render_quick_stats()

        # 帮助区域
        self.render_help_section()

    def render_search_section(self):
        """渲染搜索区域"""
        st.markdown('<div class="search-container">', unsafe_allow_html=True)

        # 搜索框
        col1, col2 = st.columns([4, 1])

        with col1:
            query = st.text_input(
                "输入您要搜索的内容",
                placeholder="例如：法语虚拟式用法、French grammar、语法学习...",
                value="法语虚拟式",
                help="支持中文、法语、英语搜索"
            )

        with col2:
            search_button = st.button("🔍 搜索", type="primary", use_container_width=True)

        # 隐藏的高级选项（可折叠）
        with st.expander("🔧 高级选项", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                language = st.selectbox(
                    "搜索语言",
                    ["自动检测", "中文", "法语", "英语"],
                    index=0,
                    help="选择查询语言或自动检测"
                )
                result_count = st.slider("结果数量", 1, 20, 5)

            with col2:
                search_mode = st.selectbox(
                    "搜索模式",
                    ["综合搜索", "仅知识图谱", "仅文本搜索"],
                    index=0
                )
                include_translations = st.checkbox("包含翻译结果", value=True)

        # 执行搜索
        if search_button or query:
            if query.strip():
                self.perform_simple_search(query, {
                    "language": language,
                    "result_count": result_count,
                    "search_mode": search_mode,
                    "include_translations": include_translations
                })
            else:
                st.warning("请输入搜索内容")

        st.markdown('</div>', unsafe_allow_html=True)

    def perform_simple_search(self, query: str, options: Dict[str, Any]):
        """执行简易搜索"""
        with st.spinner("🔍 正在搜索，请稍候..."):
            try:
                # 生成模拟搜索结果
                results = self.generate_simple_results(query, options)

                # 显示结果
                self.render_simple_results(results)

            except Exception as e:
                st.error(f"搜索失败: {e}")
                logger.error(f"简易搜索异常: {e}")

    def generate_simple_results(self, query: str, options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成简易搜索结果"""
        # 模拟搜索结果
        mock_results = [
            {
                "title": "法语虚拟式的完整用法指南",
                "content": "法语虚拟式（le subjonctif）是法语语法中的重要组成部分，主要用于表达主观、不确定、愿望、情感等内容。虚拟式的构成通常由助动词avoir或être的虚拟式现在时加上动词的过去分词构成。",
                "language": "zh",
                "type": "语法讲解",
                "relevance": 0.95,
                "url": "#"
            },
            {
                "title": "Le subjonctif français - Usage complet",
                "content": "Le subjonctif est un mode verbal essentiel en français. Il s'emploie pour exprimer des sentiments, des doutes, des souhaits, des nécessités. On l'utilise après des verbes comme vouloir, falloir, devoir.",
                "language": "fr",
                "type": "讲解",
                "relevance": 0.92,
                "url": "#"
            },
            {
                "title": "French Subjunctive Mood - Complete Guide",
                "content": "The French subjunctive mood is used to express subjective states, doubts, wishes, emotions, and necessities. It typically follows verbs of volition, emotion, doubt, and necessity.",
                "language": "en",
                "type": "Guide",
                "relevance": 0.88,
                "url": "#"
            },
            {
                "title": "虚拟式练习题集",
                "content": "练习1：选择正确的虚拟式形式\n1. Il faut que tu (aller) à l'école.\n2. Je veux que tu (venir) demain.\n3. Il est important que nous (étudier) le français.",
                "language": "zh",
                "type": "练习",
                "relevance": 0.85,
                "url": "#"
            }
        ]

        # 根据选项过滤结果
        filtered_results = mock_results

        # 语言过滤
        if options.get("language") != "自动检测":
            lang_map = {"中文": "zh", "法语": "fr", "英语": "en"}
            target_lang = lang_map.get(options.get("language"))
            if target_lang:
                filtered_results = [r for r in filtered_results if r["language"] == target_lang]

        # 结果数量限制
        max_results = options.get("result_count", 5)
        filtered_results = filtered_results[:max_results]

        return filtered_results

    def render_simple_results(self, results: List[Dict[str, Any]]):
        """渲染简易搜索结果"""
        if not results:
            st.info("没有找到相关结果")
            return

        # 结果统计
        st.write(f"找到 **{len(results)}** 个相关结果")

        # 显示结果
        for i, result in enumerate(results):
            with st.container():
                st.markdown(f'<div class="result-card">', unsafe_allow_html=True)

                # 标题和语言标签
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.subheader(result["title"])
                with col2:
                    language_flag = {"zh": "🇨🇳", "fr": "🇫🇷", "en": "🇬🇧"}
                    st.markdown(f"<h3>{language_flag.get(result['language'], '🌐')}</h3>", unsafe_allow_html=True)

                # 元信息
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**类型**: {result['type']}")
                with col2:
                    st.write(f"**语言**: {result['language']}")
                with col3:
                    st.write(f"**相关度**: {result['relevance']:.2f}")

                # 内容预览
                content_preview = result['content'][:200] + "..." if len(result['content']) > 200 else result['content']
                st.write(content_preview)

                # 操作按钮
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button(f"📖 查看详情", key=f"detail_{i}"):
                        st.session_state[f"expanded_{i}"] = not st.session_state.get(f"expanded_{i}", False)

                with col2:
                    if st.button(f"💾 收藏", key=f"save_{i}"):
                        st.success("已添加到收藏夹")

                with col3:
                    if st.button(f"📤 分享", key=f"share_{i}"):
                        st.info("分享链接已复制")

                # 展开的详细内容
                if st.session_state.get(f"expanded_{i}", False):
                    st.markdown("---")
                    st.write("**完整内容:**")
                    st.write(result['content'])

                    if result.get("url") != "#":
                        st.markdown(f"**链接**: [{result['url']}]({result['url']})")

                st.markdown('</div>', unsafe_allow_html=True)

        # 导出选项
        if st.button("📥 导出结果"):
            self.export_simple_results(results)

    def export_simple_results(self, results: List[Dict[str, Any]]):
        """导出简易搜索结果"""
        try:
            # 准备导出数据
            export_data = []
            for result in results:
                export_item = {
                    "标题": result["title"],
                    "语言": result["language"],
                    "类型": result["type"],
                    "相关度": result["relevance"],
                    "内容预览": result["content"][:300] + "..."
                }
                export_data.append(export_item)

            # 创建DataFrame
            df = pd.DataFrame(export_data)

            # 提供下载
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 下载搜索结果 (CSV)",
                data=csv,
                file_name=f"search_results_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

        except Exception as e:
            st.error(f"导出失败: {e}")

    def render_quick_stats(self):
        """渲染快速统计"""
        st.markdown("---")
        st.subheader("📊 系统概览")

        col1, col2, col3, col4 = st.columns(4)

        try:
            # 获取统计信息
            if self.data_storage:
                stats = self.data_storage.get_statistics()
                doc_count = stats.get("total_documents", 0)
                avg_quality = stats.get("average_quality_score", 0)
            else:
                doc_count = 0
                avg_quality = 0

            if self.kg_viewer and self.kg_viewer.graph:
                kg_stats = self.kg_viewer.get_statistics()
                node_count = kg_stats.get("node_count", 0)
                edge_count = kg_stats.get("edge_count", 0)
            else:
                node_count = 0
                edge_count = 0

            with col1:
                st.metric("📄 文档数量", doc_count)
            with col2:
                st.metric("⭐ 平均质量", f"{avg_quality:.2f}")
            with col3:
                st.metric("🕸️ 知识节点", node_count)
            with col4:
                st.metric("🔗 关系数量", edge_count)

        except Exception as e:
            st.error(f"获取统计信息失败: {e}")

    def render_help_section(self):
        """渲染帮助区域"""
        st.markdown("---")
        st.subheader("❓ 使用帮助")

        # 帮助内容
        help_tabs = st.tabs(["🔍 搜索技巧", "🌐 多语言支持", "⚙️ 高级功能"])

        with help_tabs[0]:
            st.markdown("""
            <div class="help-section">
            <h4>🔍 搜索技巧</h4>
            <ul>
                <li><strong>关键词搜索</strong>: 输入核心关键词，如"虚拟式"、"语法"</li>
                <li><strong>短语搜索</strong>: 使用引号搜索完整短语，如"法语虚拟式"</li>
                <li><strong>多语言搜索</strong>: 系统支持中文、法语、英语</li>
                <li><strong>自动检测</strong>: 系统会自动检测输入语言并匹配相关内容</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)

        with help_tabs[1]:
            st.markdown("""
            <div class="help-section">
            <h4>🌐 多语言支持</h4>
            <ul>
                <li><strong>中文 🇨🇳</strong>: 支持中文搜索和中文内容</li>
                <li><strong>法语 🇫🇷</strong>: 支持法语搜索和法语内容</li>
                <li><strong>英语 🇬🇧</strong>: 支持英语搜索和英语内容</li>
                <li><strong>跨语言</strong>: 可以用一种语言搜索另一种语言的内容</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)

        with help_tabs[2]:
            st.markdown("""
            <div class="help-section">
            <h4>⚙️ 高级功能</h4>
            <ul>
                <li><strong>搜索模式</strong>: 选择综合搜索、知识图谱搜索或纯文本搜索</li>
                <li><strong>结果过滤</strong>: 按语言、类型过滤搜索结果</li>
                <li><strong>结果导出</strong>: 将搜索结果导出为CSV文件</li>
                <li><strong>收藏功能</strong>: 收藏有用的搜索结果</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)

        # 常见问题
        with st.expander("🤔 常见问题"):
            st.markdown("""
            **Q: 如何获得更好的搜索结果？**
            A: 使用具体的关键词，避免过于宽泛的术语。

            **Q: 为什么搜索不到某些内容？**
            A: 可能是数据库中没有相关内容，或者关键词不够精确。

            **Q: 如何上传自己的文档？**
            A: 请使用完整版界面的"数据获取与管理"功能。

            **Q: 支持哪些文件格式？**
            A: 支持PDF、Word、Excel、CSV、文本文件等格式。
            """)

    def render_footer(self):
        """渲染页脚"""
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: #666; padding: 1rem;'>
            <p>📚 KG-CLIR - 多语种知识图谱跨语言检索系统</p>
            <p>
                <a href='#' style='color: #666;'>使用完整版</a> |
                <a href='#' style='color: #666;'>帮助文档</a> |
                <a href='#' style='color: #666;'>联系我们</a>
            </p>
        </div>
        """, unsafe_allow_html=True)


def main():
    """主函数"""
    # 创建极简界面实例
    simple_ui = SimpleUI()

    # 渲染界面
    simple_ui.render()


if __name__ == "__main__":
    main()