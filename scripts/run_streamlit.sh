#!/usr/bin/env bash
# -*- coding: utf-8 -*-

# KG-CLIR Streamlit 启动脚本
# 用于启动基于Streamlit的用户界面系统

set -euo pipefail

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
STREAMLIT_PORT="${STREAMLIT_PORT:-8501}"
STREAMLIT_HOST="${STREAMLIT_HOST:-0.0.0.0}"

echo "========================================="
echo "KG-CLIR Streamlit 启动脚本"
echo "========================================="
echo "项目根目录: $PROJECT_ROOT"
echo "Streamlit地址: http://$STREAMLIT_HOST:$STREAMLIT_PORT"
echo "========================================="

# 检查Python环境
echo "🐍 检查Python环境..."
python --version
echo ""

# 检查依赖
echo "📦 检查关键依赖..."
python -c "
import streamlit
print(f'✅ Streamlit {streamlit.__version__}')
" || {
    echo "❌ Streamlit未安装，正在安装..."
    pip install streamlit streamlit-agraph plotly pandas
}

python -c "
import pandas
print(f'✅ Pandas {pandas.__version__}')
" || {
    echo "❌ Pandas未安装，正在安装..."
    pip install pandas
}

python -c "
import plotly
print(f'✅ Plotly {plotly.__version__}')
" || {
    echo "❌ Plotly未安装，正在安装..."
    pip install plotly
}

echo ""

# 检查项目模块
echo "🔍 检查项目模块..."
cd "$PROJECT_ROOT"

# 检查PYTHONPATH
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"

# 测试导入关键模块
python -c "
try:
    from src.app.streamlit_ui import main
    print('✅ 主界面模块可用')
except ImportError as e:
    print(f'❌ 主界面模块导入失败: {e}')
    exit(1)

try:
    from src.app.data_manager import create_data_manager
    print('✅ 数据管理模块可用')
except ImportError as e:
    print(f'❌ 数据管理模块导入失败: {e}')
    exit(1)

try:
    from src.app.knowledge_viewer import create_knowledge_viewer
    print('✅ 知识图谱查看器可用')
except ImportError as e:
    print(f'⚠️ 知识图谱查看器导入失败: {e}')
" || {
    echo "❌ 模块检查失败"
    exit 1
}

echo ""

# 创建必要目录
echo "📁 创建必要目录..."
mkdir -p data/uploads
mkdir -p data/uploads/temp
mkdir -p outputs
mkdir -p models
mkdir -p logs

# 设置环境变量
echo "🌍 设置环境变量..."
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"
export STREAMLIT_SERVER_PORT=$STREAMLIT_PORT
export STREAMLIT_SERVER_ADDRESS=$STREAMLIT_HOST
export STREAMLIT_SERVER_HEADLESS=false
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# 选择启动模式
echo ""
echo "选择启动模式:"
echo "1) 完整界面 (streamlit_ui.py) - 推荐"
echo "2) 极简界面 (simple_ui.py)"
echo "3) 知识图谱可视化 (knowledge_viewer.py)"

read -p "请选择 (1-3) [默认: 1]: " choice
choice=${choice:-1}

case $choice in
    1)
        echo "🚀 启动完整Streamlit界面..."
        echo "📱 访问地址: http://$STREAMLIT_HOST:$STREAMLIT_PORT"
        echo ""
        echo "🎯 功能包括:"
        echo "  • 📥 数据获取与管理"
        echo "  • 🔍 跨语言检索"
        echo "  • 🕸️ 知识图谱可视化"
        echo "  • 🎓 学习支持"
        echo "  • ⚙️ 系统设置"
        echo ""

        # 启动Streamlit
        streamlit run src/app/streamlit_ui.py \
            --server.port=$STREAMLIT_PORT \
            --server.address=$STREAMLIT_HOST \
            --server.headless=false \
            --browser.gatherUsageStats=false
        ;;

    2)
        echo "🚀 启动极简界面..."
        echo "📱 访问地址: http://$STREAMLIT_HOST:$STREAMLIT_PORT"
        echo ""
        echo "🎯 功能包括:"
        echo "  • 🔍 简化搜索"
        echo "  • 📊 快速统计"
        echo "  • ❓ 使用帮助"
        echo ""

        streamlit run src/app/simple_ui.py \
            --server.port=$STREAMLIT_PORT \
            --server.address=$STREAMLIT_HOST \
            --server.headless=false \
            --browser.gatherUsageStats=false
        ;;

    3)
        echo "🚀 启动知识图谱可视化..."
        echo "📱 访问地址: http://$STREAMLIT_HOST:$STREAMLIT_PORT"
        echo ""
        echo "🎯 功能包括:"
        echo "  • 🕸️ 交互式知识图谱"
        echo "  • 📊 统计分析"
        echo "  • 🔍 节点搜索"
        echo "  • 📥 数据导出"
        echo ""

        # 创建知识图谱可视化脚本
        cat > temp_kg_viewer.py << 'EOF'
import streamlit as st
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.app.knowledge_viewer import load_default_knowledge_graph, generate_sample_knowledge_graph

st.set_page_config(page_title="知识图谱可视化", page_icon="🕸️", layout="wide")
st.title("🕸️ 知识图谱可视化")

# 加载知识图谱
viewer = load_default_knowledge_graph()
if not viewer.graph:
    st.warning("未找到知识图谱文件，使用示例数据...")
    viewer = generate_sample_knowledge_graph()

if viewer.graph:
    # 显示统计信息
    stats = viewer.get_statistics()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("节点数", stats.get("node_count", 0))
    with col2:
        st.metric("边数", stats.get("edge_count", 0))
    with col3:
        st.metric("语言数", len(stats.get("languages", {})))
    with col4:
        st.metric("组件数", stats.get("connected_components", 0))

    # 创建可视化
    if st.button("生成网络图"):
        fig = viewer.create_plotly_network()
        st.plotly_chart(fig, use_container_width=True)

    # 创建统计图表
    plots = viewer.create_statistics_plots()
    for name, fig in plots.items():
        st.subheader(name.replace("_", " ").title())
        st.plotly_chart(fig, use_container_width=True)
else:
    st.error("无法加载知识图谱")
EOF

        streamlit run temp_kg_viewer.py \
            --server.port=$STREAMLIT_PORT \
            --server.address=$STREAMLIT_HOST \
            --server.headless=false \
            --browser.gatherUsageStats=false

        # 清理临时文件
        rm -f temp_kg_viewer.py
        ;;

    *)
        echo "❌ 无效选择，退出"
        exit 1
        ;;
esac

echo ""
echo "✅ Streamlit应用已停止"
echo "========================================="