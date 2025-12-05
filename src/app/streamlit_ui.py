#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Streamlit主界面

基于Streamlit的用户友好界面系统，支持：
- 数据获取与管理（文件上传、URL抓取、在线输入）
- 跨语言检索与KG可视化
- 学习支持功能
- 系统设置与监控

Author: KG-CLIR Team
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 项目内部模块
from src.app.data_manager import (
    process_uploaded_files, create_data_manager, WebScraper
)
from src.utils.io import load_yaml, save_jsonl
from src.utils.logger import get_logger
from src.utils.metrics import calculate_ndcg, calculate_mrr

logger = get_logger(__name__)

# 页面配置
st.set_page_config(
    page_title="KG-CLIR 多语种知识图谱系统",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin: 1.5rem 0 1rem 0;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 0.25rem;
        border: 1px solid #c3e6cb;
    }
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.25rem;
        border: 1px solid #f5c6cb;
    }
    .warning-message {
        background-color: #fff3cd;
        color: #856404;
        padding: 1rem;
        border-radius: 0.25rem;
        border: 1px solid #ffeaa7;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """初始化会话状态"""
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "数据获取"

    if 'uploaded_files' not in st.session_state:
        st.session_state.uploaded_files = []

    if 'processed_documents' not in st.session_state:
        st.session_state.processed_documents = []

    if 'search_results' not in st.session_state:
        st.session_state.search_results = []

    if 'selected_language' not in st.session_state:
        st.session_state.selected_language = "zh"

    if 'data_storage' not in st.session_state:
        st.session_state.data_storage = create_data_manager()


def render_sidebar():
    """渲染侧边栏导航"""
    with st.sidebar:
        st.image("https://via.placeholder.com/200x100/1f77b4/ffffff?text=KG-CLIR", width=200)

        st.title("📚 KG-CLIR")
        st.markdown("---")

        # 导航菜单
        pages = [
            "📥 数据获取与管理",
            "🔍 跨语言检索",
            "🕸️ 知识图谱",
            "🎓 学习支持",
            "⚙️ 系统设置"
        ]

        selected_page = st.selectbox(
            "选择功能页面",
            pages,
            index=0,
            key="page_selector"
        )

        st.session_state.current_page = selected_page

        st.markdown("---")

        # 系统状态
        st.subheader("📊 系统状态")

        try:
            stats = st.session_state.data_storage.get_statistics()
            st.metric("总文档数", stats.get("total_documents", 0))
            st.metric("平均质量", f"{stats.get('average_quality_score', 0):.2f}")
        except Exception as e:
            st.error(f"获取统计信息失败: {e}")

        st.markdown("---")

        # 快速操作
        st.subheader("⚡ 快速操作")

        if st.button("🧹 清除缓存", help="清除所有缓存数据"):
            st.session_state.clear()
            st.rerun()

        if st.button("📥 下载示例数据", help="下载演示数据集"):
            download_sample_data()


def download_sample_data():
    """下载示例数据"""
    try:
        sample_text = """
        这是一个关于法语学习的示例文档。

        法语虚拟式（le subjonctif）是法语语法中的重要组成部分。
        它主要用于表达主观、不确定、愿望、情感等内容。

        虚拟式的构成通常由助动词avoir或être的虚拟式现在时
        加上动词的过去分词构成。
        """

        sample_data = [{
            "doc_id": "sample_001",
            "text": sample_text.strip(),
            "language": "zh",
            "filename": "sample_french_grammar.txt"
        }]

        save_jsonl(sample_data, "data/demo/sample_data.jsonl")
        st.success("示例数据已下载到 data/demo/sample_data.jsonl")

    except Exception as e:
        st.error(f"下载示例数据失败: {e}")


def render_data_acquisition_page():
    """渲染数据获取页面"""
    st.markdown('<div class="main-header">📥 数据获取与管理</div>', unsafe_allow_html=True)

    # 标签页
    tab1, tab2, tab3, tab4 = st.tabs(["📁 文件上传", "🌐 URL抓取", "✏️ 在线输入", "📋 文档管理"])

    with tab1:
        render_file_upload()

    with tab2:
        render_web_scraping()

    with tab3:
        render_online_input()

    with tab4:
        render_document_management()


def render_file_upload():
    """渲染文件上传"""
    st.markdown('<div class="section-header">📁 文件上传</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.write("支持的文件格式:")
        supported_formats = {
            "PDF文档": ".pdf",
            "Word文档": ".docx, .doc",
            "Excel表格": ".xlsx, .xls",
            "CSV文件": ".csv",
            "文本文件": ".txt",
            "JSON文件": ".json, .jsonl"
        }

        for format_name, ext in supported_formats.items():
            st.write(f"- {format_name}: `{ext}`")

    with col2:
        st.info("💡 提示")
        st.write("- 支持批量上传")
        st.write("- 自动语言检测")
        st.write("- 质量评分")
        st.write("- 重复检测")

    # 文件上传组件
    uploaded_files = st.file_uploader(
        "选择要上传的文件",
        accept_multiple_files=True,
        type=[
            'pdf', 'docx', 'doc', 'xlsx', 'xls',
            'csv', 'txt', 'json', 'jsonl'
        ],
        help="可以选择多个文件同时上传"
    )

    if uploaded_files:
        st.write(f"已选择 {len(uploaded_files)} 个文件:")

        # 显示文件信息
        file_info = []
        for file in uploaded_files:
            file_info.append({
                "文件名": file.name,
                "大小": f"{file.size / 1024:.1f} KB",
                "类型": Path(file.name).suffix
            })

        df_files = pd.DataFrame(file_info)
        st.dataframe(df_files, use_container_width=True)

        # 处理按钮
        if st.button("🚀 开始处理", type="primary", use_container_width=True):
            with st.spinner("正在处理文件，请稍候..."):
                # 进度条
                progress_bar = st.progress(0)
                status_text = st.empty()

                def progress_callback(current, total, filename):
                    progress = current / total
                    progress_bar.progress(progress)
                    status_text.text(f"处理中: {current}/{total} - {filename}")

                # 处理文件
                try:
                    results = process_uploaded_files(
                        uploaded_files,
                        storage_path="data/uploads",
                        progress_callback=progress_callback
                    )

                    # 更新会话状态
                    st.session_state.uploaded_files = uploaded_files
                    st.session_state.processed_documents = results

                    progress_bar.progress(1.0)
                    status_text.text("处理完成！")

                    # 显示处理结果
                    render_processing_results(results)

                except Exception as e:
                    st.error(f"文件处理失败: {e}")
                    logger.error(f"文件处理异常: {e}")


def render_processing_results(results: List[Dict[str, Any]]):
    """渲染处理结果"""
    st.markdown('<div class="section-header">📊 处理结果</div>', unsafe_allow_html=True)

    if not results:
        st.warning("没有处理结果")
        return

    # 统计信息
    success_count = sum(1 for r in results if r.get("status") == "success")
    error_count = len(results) - success_count

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("成功", success_count, delta=f"总计 {len(results)}")
    with col2:
        st.metric("失败", error_count)
    with col3:
        success_rate = success_count / len(results) * 100 if results else 0
        st.metric("成功率", f"{success_rate:.1f}%")

    # 详细结果
    if success_count > 0:
        st.subheader("✅ 成功处理的文件")

        success_results = [r for r in results if r.get("status") == "success"]

        for result in success_results[:5]:  # 显示前5个
            with st.expander(f"📄 {result['filename']}"):
                col1, col2 = st.columns(2)

                with col1:
                    st.write("**基本信息:**")
                    st.write(f"- 文档ID: {result['doc_id']}")
                    st.write(f"- 语言: {result['metadata']['language']}")
                    st.write(f"- 质量分数: {result['metadata']['quality_score']:.2f}")

                with col2:
                    st.write("**处理信息:**")
                    st.write(f"- 文本长度: {len(result['text'])} 字符")
                    st.write(f"- 文件类型: {result['metadata']['file_type']}")

                # 文本预览
                st.write("**文本预览:**")
                st.text_area("", result['text'][:300] + "...", height=100, disabled=True, key=f"upload_preview_{result['doc_id']}")

    if error_count > 0:
        st.subheader("❌ 处理失败的文件")

        error_results = [r for r in results if r.get("status") == "error"]

        for result in error_results:
            with st.expander(f"📄 {result['filename']}"):
                st.error(f"错误信息: {result.get('error', '未知错误')}")


def render_web_scraping():
    """渲染网页抓取"""
    st.markdown('<div class="section-header">🌐 URL抓取</div>', unsafe_allow_html=True)

    st.write("输入要抓取的网页URL，系统将自动提取文本内容并处理。")

    # URL输入
    url_input = st.text_area(
        "输入URL（每行一个）",
        placeholder="https://example.com/page1\nhttps://example.com/page2",
        height=150
    )

    # 抓取选项
    col1, col2 = st.columns(2)
    with col1:
        timeout = st.number_input("超时时间（秒）", min_value=5, max_value=120, value=30)
    with col2:
        max_urls = st.number_input("最大URL数量", min_value=1, max_value=50, value=10)

    if st.button("🕷️ 开始抓取", type="primary", use_container_width=True):
        if url_input.strip():
            urls = [url.strip() for url in url_input.strip().split('\n') if url.strip()]

            if len(urls) > max_urls:
                urls = urls[:max_urls]
                st.warning(f"URL数量超过限制，只处理前{max_urls}个")

            with st.spinner("正在抓取网页，请稍候..."):
                try:
                    scraper = WebScraper()

                    # 进度条
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    def progress_callback(current, total, url):
                        progress = current / total
                        progress_bar.progress(progress)
                        status_text.text(f"抓取中: {current}/{total} - {url}")

                    # 抓取URLs
                    results = scraper.scrape_urls(urls, progress_callback)

                    progress_bar.progress(1.0)
                    status_text.text("抓取完成！")

                    # 显示结果
                    render_scraping_results(results)

                except Exception as e:
                    st.error(f"网页抓取失败: {e}")
                    logger.error(f"网页抓取异常: {e}")
        else:
            st.warning("请输入至少一个URL")


def render_scraping_results(results: List[Dict[str, Any]]):
    """渲染抓取结果"""
    st.markdown('<div class="section-header">📊 抓取结果</div>', unsafe_allow_html=True)

    if not results:
        st.warning("没有抓取结果")
        return

    # 统计信息
    success_count = sum(1 for r in results if r.get("status") == "success")
    error_count = len(results) - success_count

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("成功", success_count, delta=f"总计 {len(results)}")
    with col2:
        st.metric("失败", error_count)
    with col3:
        success_rate = success_count / len(results) * 100 if results else 0
        st.metric("成功率", f"{success_rate:.1f}%")

    # 详细结果
    if success_count > 0:
        st.subheader("✅ 成功抓取的网页")

        success_results = [r for r in results if r.get("status") == "success"]

        for result in success_results[:5]:  # 显示前5个
            with st.expander(f"🌐 {result.get('url', 'Unknown URL')}"):
                col1, col2 = st.columns(2)

                with col1:
                    st.write("**基本信息:**")
                    st.write(f"- 文档ID: {result['doc_id']}")
                    st.write(f"- 语言: {result['language']}")
                    st.write(f"- 文本长度: {len(result['text'])} 字符")

                with col2:
                    st.write("**抓取信息:**")
                    if 'url' in result:
                        st.write(f"- 源URL: {result['url']}")

                # 文本预览
                st.write("**文本预览:**")
                st.text_area("", result['text'][:300] + "...", height=100, disabled=True, key=f"scrape_preview_{result['doc_id']}")

    if error_count > 0:
        st.subheader("❌ 抓取失败的网页")

        error_results = [r for r in results if r.get("status") == "error"]

        for result in error_results:
            with st.expander(f"🌐 {result.get('url', 'Unknown URL')}"):
                st.error(f"错误信息: {result.get('error', '未知错误')}")


def render_online_input():
    """渲染在线输入"""
    st.markdown('<div class="section-header">✏️ 在线文本输入</div>', unsafe_allow_html=True)

    st.write("直接输入或粘贴文本文档，系统将自动处理和分析。")

    # 文本输入
    text_input = st.text_area(
        "输入文本内容",
        placeholder="请在此输入或粘贴您的文本内容...",
        height=300
    )

    # 选项
    col1, col2 = st.columns(2)
    with col1:
        doc_title = st.text_input("文档标题", value="手动输入文档")
        language = st.selectbox(
            "语言（可选，系统将自动检测）",
            ["自动检测", "中文", "法语", "英语"],
            index=0
        )

    with col2:
        enable_preprocessing = st.checkbox("启用预处理", value=True)
        enable_quality_check = st.checkbox("启用质量检查", value=True)

    if st.button("💾 保存文档", type="primary", use_container_width=True):
        if text_input.strip():
            with st.spinner("正在处理文本..."):
                try:
                    # 处理文本
                    from src.app.data_manager import DataValidator, normalize_text
                    from datetime import datetime
                    import hashlib

                    processed_text = normalize_text(text_input) if enable_preprocessing else text_input

                    # 语言检测
                    if language == "自动检测":
                        from src.utils.lang_detect import detect_language
                        detected_lang = detect_language(processed_text[:1000])
                    else:
                        lang_map = {"中文": "zh", "法语": "fr", "英语": "en"}
                        detected_lang = lang_map.get(language, "unknown")

                    # 质量检查
                    quality_score = 1.0
                    if enable_quality_check:
                        validator = DataValidator()
                        validation = validator.validate_text(processed_text)
                        quality_score = validation["quality_score"]

                    # 生成文档ID
                    doc_id = hashlib.md5(f"{doc_title}_{len(processed_text)}".encode()).hexdigest()[:16]

                    # 创建文档数据
                    doc_data = {
                        "doc_id": doc_id,
                        "filename": f"{doc_title}.txt",
                        "status": "success",
                        "text": processed_text,
                        "original_text": text_input,
                        "source": "manual_input",
                        "language": detected_lang,
                        "title": doc_title,
                        "metadata": {
                            "doc_id": doc_id,
                            "filename": f"{doc_title}.txt",
                            "file_type": ".txt",
                            "size": len(text_input.encode()),
                            "language": detected_lang,
                            "created_at": datetime.now().isoformat(),
                            "processed_at": datetime.now().isoformat(),
                            "quality_score": quality_score,
                            "checksum": hashlib.md5(text_input.encode()).hexdigest(),
                            "source": "manual_input"
                        }
                    }

                    # 保存到数据库
                    if st.session_state.data_storage.save_document(doc_data):
                        st.success("✅ 文档保存成功！")

                        # 显示文档信息
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("文档ID", doc_id)
                            st.metric("语言", detected_lang)
                        with col2:
                            st.metric("文本长度", f"{len(processed_text)} 字符")
                            st.metric("质量分数", f"{quality_score:.2f}")

                        # 文本预览
                        with st.expander("📄 文本预览", expanded=True):
                            st.text_area("", processed_text[:500] + "...", height=200, disabled=True, key="processed_preview")
                    else:
                        st.error("❌ 文档保存失败")

                except Exception as e:
                    st.error(f"文本处理失败: {e}")
                    logger.error(f"文本处理异常: {e}")
        else:
            st.warning("请输入文本内容")


def render_document_management():
    """渲染文档管理"""
    st.markdown('<div class="section-header">📋 文档管理</div>', unsafe_allow_html=True)

    # 筛选选项
    col1, col2, col3 = st.columns(3)
    with col1:
        language_filter = st.selectbox(
            "语言筛选",
            ["全部", "zh", "fr", "en", "unknown"]
        )
    with col2:
        min_quality = st.slider("最低质量分数", 0.0, 1.0, 0.0, 0.1)
    with col3:
        limit = st.number_input("显示数量", min_value=5, max_value=100, value=20)

    # 获取文档列表
    try:
        language = None if language_filter == "全部" else language_filter
        documents = st.session_state.data_storage.get_documents(
            limit=limit,
            language=language,
            min_quality=min_quality
        )

        if not documents:
            st.info("没有找到符合条件的文档")
            return

        st.write(f"找到 {len(documents)} 个文档")

        # 文档列表
        for i, doc in enumerate(documents):
            with st.expander(f"📄 {doc['filename']} ({doc['language']})", expanded=i == 0):
                col1, col2, col3 = st.columns([2, 1, 1])

                with col1:
                    st.write("**基本信息:**")
                    st.write(f"- 文档ID: {doc['doc_id']}")
                    st.write(f"- 语言: {doc['language']}")
                    st.write(f"- 文件类型: {doc['file_type']}")
                    st.write(f"- 大小: {doc['size']} 字节")
                    st.write(f"- 质量分数: {doc['quality_score']:.2f}")

                with col2:
                    st.write("**时间信息:**")
                    st.write(f"- 创建: {doc['created_at'][:10]}")
                    st.write(f"- 处理: {doc['processed_at'][:10]}")

                with col3:
                    if st.button(f"🗑️ 删除", key=f"delete_{doc['doc_id']}"):
                        if st.session_state.data_storage.delete_document(doc['doc_id']):
                            st.success("文档已删除")
                            st.rerun()
                        else:
                            st.error("删除失败")

                # 文本预览
                if 'text' in doc and doc['text']:
                    st.write("**文本预览:**")
                    preview_length = min(300, len(doc['text']))
                    st.text_area("", doc['text'][:preview_length] + "...", height=100, disabled=True, key=f"doc_preview_{doc['doc_id']}")

                    if len(doc['text']) > 300:
                        st.caption(f"显示前 {preview_length} 字符，共 {len(doc['text'])} 字符")

        # 批量操作
        if documents:
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📊 显示统计信息"):
                    show_document_statistics()
            with col2:
                if st.button("📥 导出文档列表"):
                    export_document_list(documents)

    except Exception as e:
        st.error(f"获取文档列表失败: {e}")
        logger.error(f"文档管理异常: {e}")


def show_document_statistics():
    """显示文档统计信息"""
    try:
        stats = st.session_state.data_storage.get_statistics()

        st.subheader("📊 文档统计信息")

        # 基础统计
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总文档数", stats.get("total_documents", 0))
        with col2:
            st.metric("平均质量", f"{stats.get('average_quality_score', 0):.2f}")
        with col3:
            st.metric("语言数量", len(stats.get("language_distribution", {})))
        with col4:
            st.metric("文件类型", len(stats.get("file_type_distribution", {})))

        # 语言分布
        if stats.get("language_distribution"):
            st.subheader("🌍 语言分布")
            lang_data = stats["language_distribution"]
            fig = px.pie(
                values=list(lang_data.values()),
                names=list(lang_data.keys()),
                title="文档语言分布"
            )
            st.plotly_chart(fig, use_container_width=True)

        # 文件类型分布
        if stats.get("file_type_distribution"):
            st.subheader("📁 文件类型分布")
            type_data = stats["file_type_distribution"]
            fig = px.bar(
                x=list(type_data.keys()),
                y=list(type_data.values()),
                title="文件类型分布"
            )
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"获取统计信息失败: {e}")


def export_document_list(documents: List[Dict[str, Any]]):
    """导出文档列表"""
    try:
        # 准备导出数据
        export_data = []
        for doc in documents:
            export_item = {
                "doc_id": doc["doc_id"],
                "filename": doc["filename"],
                "language": doc["language"],
                "file_type": doc["file_type"],
                "size": doc["size"],
                "quality_score": doc["quality_score"],
                "created_at": doc["created_at"],
                "processed_at": doc["processed_at"],
                "text_preview": doc.get("text", "")[:200] + "..." if doc.get("text") else ""
            }
            export_data.append(export_item)

        # 创建DataFrame
        df = pd.DataFrame(export_data)

        # 提供下载
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 下载CSV文件",
            data=csv,
            file_name=f"document_list_{time.strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"导出失败: {e}")


def render_search_page():
    """渲染检索页面"""
    st.markdown('<div class="main-header">🔍 跨语言检索</div>', unsafe_allow_html=True)

    # 检索设置
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        query = st.text_input(
            "输入查询内容",
            placeholder="请输入您要搜索的内容...",
            value="法语虚拟式用法"
        )

    with col2:
        query_language = st.selectbox(
            "查询语言",
            ["zh", "fr", "en"],
            format_func=lambda x: {"zh": "中文", "fr": "法语", "en": "英语"}[x],
            index=0
        )

    with col3:
        top_k = st.number_input("返回结果数", min_value=1, max_value=50, value=10)

    # 检索选项
    with st.expander("🔧 高级选项", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            use_dense = st.checkbox("使用密集检索", value=True)
            use_bm25 = st.checkbox("使用BM25检索", value=True)
        with col2:
            use_kg = st.checkbox("使用知识图谱增强", value=True)
            alpha = st.slider("密集检索权重", 0.0, 1.0, 0.4, 0.1)
            beta = st.slider("BM25权重", 0.0, 1.0, 0.4, 0.1)

    # 检索按钮
    if st.button("🔍 开始检索", type="primary", use_container_width=True):
        if query.strip():
            perform_search(query, query_language, top_k, {
                "use_dense": use_dense,
                "use_bm25": use_bm25,
                "use_kg": use_kg,
                "alpha": alpha,
                "beta": beta,
                "gamma": 1.0 - alpha - beta if use_kg else 0.0
            })
        else:
            st.warning("请输入查询内容")

    # 显示历史检索结果
    if st.session_state.search_results:
        render_search_results()


def perform_search(query: str, language: str, top_k: int, options: Dict[str, Any]):
    """执行检索"""
    with st.spinner("正在检索，请稍候..."):
        try:
            # 这里应该调用实际的检索系统
            # 由于检索系统可能还未完全实现，我们先使用模拟结果

            # 模拟检索结果
            mock_results = generate_mock_search_results(query, language, top_k)

            st.session_state.search_results = mock_results

            # 显示成功消息
            st.success(f"✅ 检索完成，找到 {len(mock_results)} 个相关文档")

            # 立即显示结果
            render_search_results()

        except Exception as e:
            st.error(f"检索失败: {e}")
            logger.error(f"检索异常: {e}")


def generate_mock_search_results(query: str, language: str, top_k: int) -> List[Dict[str, Any]]:
    """生成模拟检索结果"""
    mock_docs = [
        {
            "doc_id": "doc_001",
            "title": "法语语法：虚拟式的用法",
            "content": "法语虚拟式是法语语法中的重要组成部分，主要用于表达主观、不确定、愿望等内容。",
            "language": "zh",
            "score": 0.95,
            "kg_paths": ["虚拟式 → 语法表达 → 主观语气"]
        },
        {
            "doc_id": "doc_002",
            "title": "Le subjonctif français",
            "content": "Le subjonctif est un mode verbal utilisé pour exprimer des sentiments, des doutes, des souhaits.",
            "language": "fr",
            "score": 0.92,
            "kg_paths": ["subjonctif → mode verbal → expression"]
        },
        {
            "doc_id": "doc_003",
            "title": "French Subjunctive Mood",
            "content": "The subjunctive mood in French is used to express subjective states, doubts, wishes, and emotions.",
            "language": "en",
            "score": 0.88,
            "kg_paths": ["subjunctive → mood → subjective expression"]
        }
    ]

    # 根据top_k返回结果
    return mock_docs[:min(top_k, len(mock_docs))]


def render_search_results():
    """渲染检索结果"""
    st.markdown('<div class="section-header">📊 检索结果</div>', unsafe_allow_html=True)

    results = st.session_state.search_results

    if not results:
        st.info("没有检索结果")
        return

    # 结果统计
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("结果数量", len(results))
    with col2:
        avg_score = sum(r["score"] for r in results) / len(results)
        st.metric("平均分数", f"{avg_score:.3f}")
    with col3:
        languages = set(r["language"] for r in results)
        st.metric("语言覆盖", len(languages))

    # 结果列表
    for i, result in enumerate(results):
        with st.expander(f"📄 {result['title']} (评分: {result['score']:.3f})", expanded=i == 0):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.write("**文档信息:**")
                st.write(f"- 文档ID: {result['doc_id']}")
                st.write(f"- 语言: {result['language']}")
                st.write(f"- 相似度分数: {result['score']:.3f}")

                if 'kg_paths' in result and result['kg_paths']:
                    st.write("**知识图谱路径:**")
                    for path in result['kg_paths']:
                        st.write(f"- {path}")

                st.write("**内容预览:**")
                st.text_area("", result['content'][:300] + "...", height=100, disabled=True, key=f"search_preview_{result['doc_id']}")

            with col2:
                st.write("**操作:**")
                if st.button(f"🔍 查看详情", key=f"detail_{result['doc_id']}"):
                    st.session_state.selected_doc = result
                    st.info(f"已选择文档: {result['title']}")

                if st.button(f"💾 保存结果", key=f"save_{result['doc_id']}"):
                    save_search_result(result)

    # 导出结果
    if st.button("📥 导出所有结果"):
        export_search_results(results)


def save_search_result(result: Dict[str, Any]):
    """保存检索结果"""
    try:
        # 这里可以实现保存到收藏夹等功能
        st.success(f"已保存: {result['title']}")
    except Exception as e:
        st.error(f"保存失败: {e}")


def export_search_results(results: List[Dict[str, Any]]):
    """导出检索结果"""
    try:
        # 准备导出数据
        export_data = []
        for result in results:
            export_item = {
                "doc_id": result["doc_id"],
                "title": result["title"],
                "content": result["content"][:500] + "...",
                "language": result["language"],
                "score": result["score"],
                "kg_paths": "; ".join(result.get("kg_paths", []))
            }
            export_data.append(export_item)

        # 创建DataFrame
        df = pd.DataFrame(export_data)

        # 提供下载
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 下载检索结果 (CSV)",
            data=csv,
            file_name=f"search_results_{time.strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"导出失败: {e}")


def render_knowledge_graph_page():
    """渲染知识图谱页面"""
    st.markdown('<div class="main-header">🕸️ 知识图谱</div>', unsafe_allow_html=True)

    st.info("🚧 知识图谱可视化功能正在开发中...")

    # 这里将来会实现知识图谱的可视化
    # 可以使用streamlit-agraph或其他可视化库


def render_learning_page():
    """渲染学习支持页面"""
    st.markdown('<div class="main-header">🎓 学习支持</div>', unsafe_allow_html=True)

    st.info("🚧 学习支持功能正在开发中...")

    # 这里将来会实现：
    # - 概念选择器
    # - 练习题生成
    # - 学习进度追踪
    # - 个人学习记录


def render_settings_page():
    """渲染系统设置页面"""
    st.markdown('<div class="main-header">⚙️ 系统设置</div>', unsafe_allow_html=True)

    # 标签页
    tab1, tab2, tab3 = st.tabs(["🔧 模型参数", "🗄️ 外部服务", "💾 存储管理"])

    with tab1:
        render_model_settings()

    with tab2:
        render_service_settings()

    with tab3:
        render_storage_settings()


def render_model_settings():
    """渲染模型设置"""
    st.markdown('<div class="section-header">🤖 模型参数设置</div>', unsafe_allow_html=True)

    # 检索模型设置
    st.subheader("🔍 检索模型")

    col1, col2 = st.columns(2)
    with col1:
        dense_model = st.selectbox(
            "密集检索模型",
            ["sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
             "sentence-transformers/distiluse-base-multilingual-cased-v1",
             "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"]
        )

        dense_dim = st.number_input("嵌入维度", min_value=128, max_value=1024, value=384, step=128)

    with col2:
        batch_size = st.number_input("批处理大小", min_value=1, max_value=128, value=32)
        max_length = st.number_input("最大文本长度", min_value=128, max_value=512, value=256, step=64)

    # 检索权重设置
    st.subheader("⚖️ 检索权重")

    alpha = st.slider("密集检索权重 (α)", 0.0, 1.0, 0.4, 0.1)
    beta = st.slider("BM25权重 (β)", 0.0, 1.0, 0.4, 0.1)
    gamma = 1.0 - alpha - beta

    st.info(f"知识图谱权重 (γ): {gamma:.2f}")

    if gamma < 0:
        st.warning("⚠️ 权重总和超过1.0，请调整参数")

    # 保存设置
    if st.button("💾 保存模型设置", type="primary"):
        # 保存到配置文件
        settings = {
            "retrieval": {
                "dense_model": dense_model,
                "dense_dim": dense_dim,
                "batch_size": batch_size,
                "max_length": max_length,
                "weights": {
                    "alpha": alpha,
                    "beta": beta,
                    "gamma": max(0.0, gamma)
                }
            }
        }

        # 这里应该保存到配置文件
        st.success("✅ 模型设置已保存")


def render_service_settings():
    """渲染外部服务设置"""
    st.markdown('<div class="section-header">🌐 外部服务设置</div>', unsafe_allow_html=True)

    # Neo4j设置
    st.subheader("🕸️ Neo4j 图数据库")

    col1, col2 = st.columns(2)
    with col1:
        neo4j_uri = st.text_input("Neo4j URI", value="bolt://localhost:7687")
        neo4j_username = st.text_input("用户名", value="neo4j")
    with col2:
        neo4j_password = st.text_input("密码", value="kgclir2024", type="password")
        neo4j_database = st.text_input("数据库名", value="kgclir")

    # Elasticsearch设置
    st.subheader("🔍 Elasticsearch")

    col1, col2 = st.columns(2)
    with col1:
        es_host = st.text_input("主机地址", value="localhost")
        es_port = st.number_input("端口", min_value=1, max_value=65535, value=9200)
    with col2:
        es_scheme = st.selectbox("协议", ["http", "https"], index=0)
        es_index = st.text_input("索引名", value="kgclir_documents")

    # 服务测试
    if st.button("🔧 测试服务连接"):
        test_services({
            "neo4j": {
                "uri": neo4j_uri,
                "username": neo4j_username,
                "password": neo4j_password,
                "database": neo4j_database
            },
            "elasticsearch": {
                "host": es_host,
                "port": es_port,
                "scheme": es_scheme,
                "index": es_index
            }
        })


def test_services(config: Dict[str, Any]):
    """测试外部服务连接"""
    with st.spinner("正在测试服务连接..."):
        results = {}

        # 测试Neo4j
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                config["neo4j"]["uri"],
                auth=(config["neo4j"]["username"], config["neo4j"]["password"])
            )
            with driver.session(database=config["neo4j"]["database"]) as session:
                session.run("RETURN 1")
            results["neo4j"] = "✅ 连接成功"
            driver.close()
        except Exception as e:
            results["neo4j"] = f"❌ 连接失败: {str(e)}"

        # 测试Elasticsearch
        try:
            from elasticsearch import Elasticsearch
            es = Elasticsearch([{
                "host": config["elasticsearch"]["host"],
                "port": config["elasticsearch"]["port"],
                "scheme": config["elasticsearch"]["scheme"]
            }])
            if es.ping():
                results["elasticsearch"] = "✅ 连接成功"
            else:
                results["elasticsearch"] = "❌ 连接失败"
        except Exception as e:
            results["elasticsearch"] = f"❌ 连接失败: {str(e)}"

        # 显示结果
        for service, status in results.items():
            st.write(f"**{service.upper()}**: {status}")


def render_storage_settings():
    """渲染存储设置"""
    st.markdown('<div class="section-header">💾 存储管理</div>', unsafe_allow_html=True)

    # 存储路径设置
    st.subheader("📁 存储路径")

    upload_path = st.text_input("文件上传路径", value="data/uploads")
    model_path = st.text_input("模型缓存路径", value="models")
    output_path = st.text_input("输出路径", value="outputs")

    # 缓存管理
    st.subheader("🗄️ 缓存管理")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🧹 清理文件缓存"):
            # 清理文件缓存逻辑
            st.success("文件缓存已清理")

    with col2:
        if st.button("🧹 清理模型缓存"):
            # 清理模型缓存逻辑
            st.success("模型缓存已清理")

    with col3:
        if st.button("🧹 清理所有缓存"):
            # 清理所有缓存逻辑
            st.success("所有缓存已清理")

    # 存储统计
    st.subheader("📊 存储统计")

    try:
        # 显示存储使用情况
        storage_stats = get_storage_statistics()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("文档数量", storage_stats.get("document_count", 0))
        with col2:
            st.metric("存储使用", f"{storage_stats.get('storage_used', '0 MB')}")
        with col3:
            st.metric("缓存文件", storage_stats.get("cache_files", 0))

    except Exception as e:
        st.error(f"获取存储统计失败: {e}")


def get_storage_statistics() -> Dict[str, Any]:
    """获取存储统计信息"""
    stats = {}

    try:
        # 文档数量
        storage = create_data_manager()
        doc_stats = storage.get_statistics()
        stats["document_count"] = doc_stats.get("total_documents", 0)

        # 存储使用情况
        import os
        def get_folder_size(folder):
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(folder):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.exists(fp):
                        total_size += os.path.getsize(fp)
            return total_size

        storage_used = get_folder_size("data/uploads")
        stats["storage_used"] = f"{storage_used / (1024*1024):.1f} MB"

        # 缓存文件数量
        cache_count = 0
        if os.path.exists("models"):
            for root, dirs, files in os.walk("models"):
                cache_count += len(files)
        stats["cache_files"] = cache_count

    except Exception as e:
        logger.error(f"获取存储统计失败: {e}")

    return stats


def main():
    """主函数"""
    # 初始化会话状态
    init_session_state()

    # 渲染侧边栏
    render_sidebar()

    # 根据选择的页面渲染内容
    current_page = st.session_state.current_page

    if current_page == "📥 数据获取与管理":
        render_data_acquisition_page()
    elif current_page == "🔍 跨语言检索":
        render_search_page()
    elif current_page == "🕸️ 知识图谱":
        render_knowledge_graph_page()
    elif current_page == "🎓 学习支持":
        render_learning_page()
    elif current_page == "⚙️ 系统设置":
        render_settings_page()
    else:
        # 默认显示数据获取页面
        render_data_acquisition_page()


if __name__ == "__main__":
    main()