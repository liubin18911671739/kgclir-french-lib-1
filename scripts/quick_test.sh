#!/bin/bash

# 快速测试脚本
# Quick Test Script

set -e  # 遇到错误立即退出

echo "======================================"
echo "KG-CLIR French Library - Quick Test"
echo "======================================"

# 1. 检查Python环境
echo -e "\n[1/5] Checking Python environment..."
python --version
pip --version

# 2. 安装依赖（演示模式：最小依赖）
echo -e "\n[2/5] Installing minimal dependencies..."
pip install -q pyyaml loguru numpy

# 3. 测试工具模块
echo -e "\n[3/5] Testing utility modules..."
python -c "
from src.utils.io import load_yaml, save_json
from src.utils.logger import logger
from src.utils.text_norm import normalize_text
from src.utils.lang_detect import detect_language

# 测试文本处理
text = 'Bonjour, comment ça va?'
normalized = normalize_text(text)
lang = detect_language(text)
logger.info(f'Text: {text}')
logger.info(f'Normalized: {normalized}')
logger.info(f'Language: {lang}')
print('✓ Utility modules OK')
"

# 4. 测试本体模块
echo -e "\n[4/5] Testing ontology module..."
python -c "
from src.kg.ontology import FLOOntology, EntityType, RelationType

# 创建本体
ontology = FLOOntology()

# 添加实体
ontology.add_entity('être', EntityType.WORD, 'fr', '动词：是')
ontology.add_entity('avoir', EntityType.WORD, 'fr', '动词：有')
ontology.add_entity('présent', EntityType.GRAMMAR, 'fr', '现在时')

# 添加关系
ontology.add_relation('être', 'présent', RelationType.COVERS)
ontology.add_relation('avoir', 'présent', RelationType.COVERS)

# 验证
report = ontology.validate_schema()
print(f'✓ Ontology: {report[\"total_entities\"]} entities, {report[\"total_relations\"]} relations')
"

# 5. 运行完整测试套件
echo -e "\n[5/5] Running full test suite..."
if [ -f "tests/test_kg.py" ]; then
    python tests/test_kg.py
else
    echo "Test file not found, skipping..."
fi

echo -e "\n======================================"
echo "✅ All quick tests passed!"
echo "======================================"
echo ""
echo "Next steps:"
echo "  1. Install full dependencies: pip install -r requirements.txt"
echo "  2. Run complete tests: pytest tests/"
echo "  3. Build knowledge graph: python src/kg/build_kg.py --demo"
echo "  4. Start API server: python src/app/main.py"
echo ""
