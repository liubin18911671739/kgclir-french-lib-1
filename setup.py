#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Setup script for KG-CLIR French Library

安装方式：
    pip install -e .                    # 开发模式
    pip install .                       # 正式安装
    python setup.py install             # 传统安装
"""

from setuptools import setup, find_packages
from pathlib import Path

# 读取README作为长描述
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# 读取requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file, "r", encoding="utf-8") as f:
        requirements = [
            line.strip() 
            for line in f 
            if line.strip() and not line.startswith("#")
        ]

setup(
    name="kgclir-french-lib",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@university.edu",
    description="多语种知识图谱与法语学习支持系统 - 面向大学图书馆跨语言知识服务",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/kgclir-french-lib",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/kgclir-french-lib/issues",
        "Documentation": "https://github.com/yourusername/kgclir-french-lib/docs",
        "Source Code": "https://github.com/yourusername/kgclir-french-lib",
    },
    packages=find_packages(where=".", exclude=["tests", "tests.*", "notebooks", "scripts"]),
    package_dir={"": "."},
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-cov>=4.1.0",
            "black>=23.11.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
        ],
        "notebook": [
            "jupyter>=1.0.0",
            "ipython>=8.18.1",
            "matplotlib>=3.8.2",
            "seaborn>=0.13.0",
        ],
        "cpu": [
            "faiss-cpu==1.7.4",  # CPU版本FAISS
        ],
    },
    entry_points={
        "console_scripts": [
            "kgclir-build=src.kg.build_kg:main",
            "kgclir-align=src.align.align_pipeline:main",
            "kgclir-search=src.retrieval.kg_clir:main",
            "kgclir-app=src.app.api:main",
            "kgclir-check=scripts.check_environment:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Education",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Education",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Natural Language :: Chinese (Simplified)",
        "Natural Language :: French",
        "Natural Language :: English",
        "Operating System :: OS Independent",
    ],
    keywords=[
        "knowledge graph",
        "cross-lingual retrieval",
        "multilingual NLP",
        "educational technology",
        "French learning",
        "information retrieval",
        "graph neural networks",
    ],
    license="MIT",
    include_package_data=True,
    zip_safe=False,
)
