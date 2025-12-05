#!/usr/bin/env bash
# -*- coding: utf-8 -*-

# KG-CLIR 演示启动脚本
# 一键启动完整的Streamlit演示系统

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo -e "${BLUE}"
    echo "========================================="
    echo "$1"
    echo "========================================="
    echo -e "${NC}"
}

# 获取脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

print_header "🚀 KG-CLIR 演示系统启动"

print_info "项目根目录: $PROJECT_ROOT"
print_info "切换到项目目录..."
cd "$PROJECT_ROOT"

# 检查Python版本
print_info "检查Python环境..."
PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
print_success "Python版本: $PYTHON_VERSION"

# 检查虚拟环境
if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    print_success "虚拟环境: $VIRTUAL_ENV"
else
    print_warning "未检测到虚拟环境，建议使用虚拟环境"
fi

# 安装/更新依赖
print_info "检查并安装依赖..."
if pip install streamlit streamlit-agraph plotly pandas PyPDF2 pdfplumber python-docx beautifulsoup4 openpyxl; then
    print_success "依赖安装完成"
else
    print_error "依赖安装失败"
    exit 1
fi

# 创建必要目录
print_info "创建必要目录..."
mkdir -p data/uploads
mkdir -p data/uploads/temp
mkdir -p data/demo
mkdir -p outputs
mkdir -p models
mkdir -p logs
mkdir -p .streamlit

# 创建示例数据
print_info "创建示例数据..."
cat > data/demo/sample_corpus.jsonl << 'EOF'
{"doc_id": "demo_001", "title": "法语虚拟式语法", "content": "法语虚拟式是法语语法中的重要组成部分，主要用于表达主观、不确定、愿望、情感等内容。虚拟式的构成通常由助动词avoir或être的虚拟式现在时加上动词的过去分词构成。例如：Il faut que tu ailles à l'école.（你必须去学校。）", "language": "zh", "type": "grammar"}
{"doc_id": "demo_002", "title": "Le subjonctif français", "content": "Le subjonctif est un mode verbal essentiel en français. Il s'emploie pour exprimer des sentiments, des doutes, des souhaits. On l'utilise après des verbes comme vouloir, falloir, devoir. Par exemple: Je veux que tu viennes demain.", "language": "fr", "type": "grammar"}
{"doc_id": "demo_003", "title": "French Subjunctive Guide", "content": "The French subjunctive mood is used to express subjective states, doubts, wishes, emotions, and necessities. It typically follows verbs of volition, emotion, doubt, and necessity. For example: It is necessary that you study French.", "language": "en", "type": "guide"}
{"doc_id": "demo_004", "title": "法语学习方法", "content": "学习法语需要掌握语法、词汇、发音等多个方面。建议每天坚持学习，多听多说多练。可以使用语言学习应用，观看法语电影，阅读法语文章等方式提高语言水平。", "language": "zh", "type": "learning"}
EOF

print_success "示例数据创建完成"

# 设置环境变量
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH:-}"
export STREAMLIT_SERVER_PORT=8501
export STREAMLIT_SERVER_ADDRESS=0.0.0.0

print_info "环境变量设置完成"

# 显示启动信息
print_header "📱 访问信息"
print_success "Streamlit应用地址: http://localhost:8501"
print_info "如果没有自动打开浏览器，请手动访问上述地址"

print_info "系统功能:"
print_info "  📥 数据获取与管理 - 支持PDF、Word、Excel等文件上传"
print_info "  🔍 跨语言检索 - 支持中法英三语言搜索"
print_info "  🕸️ 知识图谱 - 交互式知识图谱可视化"
print_info "  🎓 学习支持 - 个性化学习路径推荐"
print_info "  ⚙️ 系统设置 - 模型参数和服务配置"

print_info "示例数据:"
print_info "  • 4个示例文档（中法英三语）"
print_info "  • 语法讲解和学习指南"
print_info "  • 支持各种文件格式测试"

# 启动确认
echo ""
print_warning "按任意键启动Streamlit应用，或按Ctrl+C取消..."
read -n 1 -s

echo ""
print_info "🚀 启动Streamlit应用..."

# 启动Streamlit
if streamlit run src/app/streamlit_ui.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=false \
    --browser.gatherUsageStats=false; then
    print_success "Streamlit应用正常关闭"
else
    print_error "Streamlit应用启动失败"
    exit 1
fi

print_header "👋 感谢使用 KG-CLIR 系统"
print_info "如需再次启动，请运行: bash scripts/start_demo.sh"