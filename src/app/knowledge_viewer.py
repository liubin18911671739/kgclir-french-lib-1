#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
知识图谱可视化模块

提供交互式知识图谱可视化、统计分析、导出等功能。
基于streamlit-agraph组件实现节点交互和路径高亮。

Author: KG-CLIR Team
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
import pandas as pd
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 项目内部模块
from src.kg.ontology import FLOOntology, EntityType, RelationType
from src.utils.io import load_json, save_json
from src.utils.logger import get_logger

logger = get_logger(__name__)


class KnowledgeGraphViewer:
    """知识图谱查看器"""

    def __init__(self):
        self.graph = None
        self.ontology = None
        self.node_colors = {
            'Concept': '#FF6B6B',
            'Activity': '#4ECDC4',
            'Outcome': '#45B7D1',
            'Resource': '#96CEB4',
            'Grammar': '#FFEAA7',
            'Task': '#DDA0DD',
            'Skill': '#98D8C8'
        }
        self.edge_colors = {
            'belongsTo': '#95A5A6',
            'supports': '#3498DB',
            'tests': '#E74C3C',
            'covers': '#F39C12',
            'hasPrereq': '#9B59B6',
            'translatedAs': '#1ABC9C',
            'sameAs': '#34495E'
        }

    def load_knowledge_graph(self, kg_path: str) -> bool:
        """加载知识图谱"""
        try:
            if kg_path.endswith('.json'):
                # 从JSON文件加载
                data = load_json(kg_path)
                self._build_graph_from_json(data)
            elif kg_path.endswith('.jsonl'):
                # 从JSONL文件加载
                self._build_graph_from_jsonl(kg_path)
            else:
                logger.error(f"不支持的文件格式: {kg_path}")
                return False

            return True

        except Exception as e:
            logger.error(f"加载知识图谱失败: {e}")
            return False

    def _build_graph_from_json(self, data: Dict[str, Any]):
        """从JSON数据构建图"""
        self.graph = nx.MultiDiGraph()

        # 添加节点
        if 'entities' in data:
            for entity in data['entities']:
                self.graph.add_node(
                    entity['id'],
                    label=entity['name'],
                    type=entity['type'],
                    language=entity.get('language', 'unknown'),
                    **entity.get('properties', {})
                )

        # 添加边
        if 'relations' in data:
            for relation in data['relations']:
                self.graph.add_edge(
                    relation['subject'],
                    relation['object'],
                    type=relation['type'],
                    confidence=relation.get('confidence', 1.0),
                    **relation.get('properties', {})
                )

    def _build_graph_from_jsonl(self, file_path: str):
        """从JSONL文件构建图"""
        self.graph = nx.MultiDiGraph()

        from src.utils.io import load_jsonl
        data = load_jsonl(file_path)

        # 假设JSONL每行包含实体或关系信息
        for item in data:
            if 'entities' in item:
                for entity in item['entities']:
                    self.graph.add_node(
                        entity['id'],
                        label=entity['name'],
                        type=entity['type'],
                        language=entity.get('language', 'unknown'),
                        **entity.get('properties', {})
                    )
            elif 'relations' in item:
                for relation in item['relations']:
                    self.graph.add_edge(
                        relation['subject'],
                        relation['object'],
                        type=relation['type'],
                        confidence=relation.get('confidence', 1.0),
                        **relation.get('properties', {})
                    )

    def get_node_info(self, node_id: str) -> Optional[Dict[str, Any]]:
        """获取节点信息"""
        if self.graph and node_id in self.graph.nodes:
            return dict(self.graph.nodes[node_id])
        return None

    def get_neighbors(self, node_id: str, depth: int = 1) -> Set[str]:
        """获取节点的邻居"""
        if not self.graph or node_id not in self.graph.nodes:
            return set()

        neighbors = {node_id}
        current_level = {node_id}

        for _ in range(depth):
            next_level = set()
            for node in current_level:
                # 获取出边邻居
                next_level.update(self.graph.successors(node))
                # 获取入边邻居
                next_level.update(self.graph.predecessors(node))

            neighbors.update(next_level)
            current_level = neighbors - set([node_id]) if _ == 0 else next_level - neighbors

        return neighbors

    def find_path(self, source: str, target: str) -> List[str]:
        """查找两个节点之间的路径"""
        if not self.graph:
            return []

        try:
            # 尝试查找最短路径
            path = nx.shortest_path(self.graph, source, target)
            return path
        except nx.NetworkXNoPath:
            # 如果没有直接路径，尝试查找其他类型的路径
            try:
                path = nx.shortest_path(self.graph.to_undirected(), source, target)
                return path
            except nx.NetworkXNoPath:
                return []
        except Exception as e:
            logger.error(f"查找路径失败: {e}")
            return []

    def filter_nodes(self, node_type: str = None, language: str = None) -> List[str]:
        """过滤节点"""
        if not self.graph:
            return []

        filtered_nodes = []
        for node_id, node_data in self.graph.nodes(data=True):
            if node_type and node_data.get('type') != node_type:
                continue
            if language and node_data.get('language') != language:
                continue
            filtered_nodes.append(node_id)

        return filtered_nodes

    def get_statistics(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        if not self.graph:
            return {}

        stats = {
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "is_directed": self.graph.is_directed(),
            "is_multigraph": self.graph.is_multigraph()
        }

        # 节点类型统计
        node_types = {}
        for node_data in self.graph.nodes.values():
            node_type = node_data.get('type', 'Unknown')
            node_types[node_type] = node_types.get(node_type, 0) + 1
        stats["node_types"] = node_types

        # 边类型统计
        edge_types = {}
        for _, _, edge_data in self.graph.edges(data=True):
            edge_type = edge_data.get('type', 'Unknown')
            edge_types[edge_type] = edge_types.get(edge_type, 0) + 1
        stats["edge_types"] = edge_types

        # 语言统计
        languages = {}
        for node_data in self.graph.nodes.values():
            lang = node_data.get('language', 'unknown')
            languages[lang] = languages.get(lang, 0) + 1
        stats["languages"] = languages

        # 连通性统计
        if self.graph.is_directed():
            stats["weakly_connected_components"] = nx.number_weakly_connected_components(self.graph)
            stats["strongly_connected_components"] = nx.number_strongly_connected_components(self.graph)
        else:
            stats["connected_components"] = nx.number_connected_components(self.graph)

        # 度统计
        degrees = dict(self.graph.degree())
        if degrees:
            degrees_list = list(degrees.values())
            stats["avg_degree"] = sum(degrees_list) / len(degrees_list)
            stats["max_degree"] = max(degrees_list)
            stats["min_degree"] = min(degrees_list)

        return stats

    def create_plotly_network(self,
                            layout: str = "spring",
                            node_size_attr: str = "degree",
                            filter_type: str = None,
                            filter_language: str = None,
                            highlight_path: List[str] = None) -> go.Figure:
        """创建Plotly网络图"""
        if not self.graph:
            return go.Figure()

        # 过滤节点
        if filter_type or filter_language:
            nodes_to_keep = self.filter_nodes(filter_type, filter_language)
            subgraph = self.graph.subgraph(nodes_to_keep)
        else:
            subgraph = self.graph

        if subgraph.number_of_nodes() == 0:
            return go.Figure()

        # 计算布局
        if layout == "spring":
            pos = nx.spring_layout(subgraph, k=1, iterations=50)
        elif layout == "circular":
            pos = nx.circular_layout(subgraph)
        elif layout == "kamada_kawai":
            pos = nx.kamada_kawai_layout(subgraph)
        else:
            pos = nx.random_layout(subgraph)

        # 准备节点数据
        node_x = []
        node_y = []
        node_text = []
        node_color = []
        node_size = []

        degrees = dict(subgraph.degree())

        for node in subgraph.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)

            node_data = subgraph.nodes[node]
            label = node_data.get('label', node)
            node_text.append(f"{label}<br>Type: {node_data.get('type', 'Unknown')}")

            # 节点颜色
            node_type = node_data.get('type', 'Unknown')
            color = self.node_colors.get(node_type, '#808080')

            # 如果节点在路径中，高亮显示
            if highlight_path and node in highlight_path:
                color = '#FF0000'

            node_color.append(color)

            # 节点大小
            if node_size_attr == "degree":
                size = degrees[node] * 5
            else:
                size = 10

            node_size.append(size)

        # 准备边数据
        edge_x = []
        edge_y = []
        edge_info = []

        for edge in subgraph.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

            edge_data = subgraph.edges[edge]
            edge_type = edge_data.get('type', 'Unknown')
            confidence = edge_data.get('confidence', 1.0)
            edge_info.append(f"{edge_type}<br>Confidence: {confidence:.2f}")

        # 创建图形
        fig = go.Figure()

        # 添加边
        fig.add_trace(go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=1, color='#888'),
            hoverinfo='none',
            mode='lines',
            name='边'
        ))

        # 添加节点
        fig.add_trace(go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            text=node_text,
            hovertext=node_text,
            textposition="middle center",
            marker=dict(
                size=node_size,
                color=node_color,
                line=dict(width=2, color='white')
            ),
            name='节点'
        ))

        # 设置布局
        fig.update_layout(
            title="知识图谱可视化",
            titlefont_size=16,
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20,l=5,r=5,t=40),
            annotations=[
                dict(
                    text="拖动节点重新排列 | 滚轮缩放 | 双击节点查看详情",
                    showarrow=False,
                    xref="paper", yref="paper",
                    x=0.005, y=-0.002,
                    xanchor='left', yanchor='bottom',
                    font=dict(size=10, color="gray")
                )
            ],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor='white'
        )

        return fig

    def create_statistics_plots(self) -> Dict[str, go.Figure]:
        """创建统计图表"""
        stats = self.get_statistics()
        plots = {}

        if not stats:
            return plots

        # 节点类型分布
        if "node_types" in stats and stats["node_types"]:
            fig_types = px.pie(
                values=list(stats["node_types"].values()),
                names=list(stats["node_types"].keys()),
                title="节点类型分布"
            )
            plots["node_types"] = fig_types

        # 边类型分布
        if "edge_types" in stats and stats["edge_types"]:
            fig_edge_types = px.bar(
                x=list(stats["edge_types"].keys()),
                y=list(stats["edge_types"].values()),
                title="边类型分布"
            )
            plots["edge_types"] = fig_edge_types

        # 语言分布
        if "languages" in stats and stats["languages"]:
            fig_languages = px.pie(
                values=list(stats["languages"].values()),
                names=list(stats["languages"].keys()),
                title="语言分布"
            )
            plots["languages"] = fig_languages

        # 度分布
        if "avg_degree" in stats:
            degrees = [d for _, d in self.graph.degree()]
            if degrees:
                fig_degree = px.histogram(
                    x=degrees,
                    title="节点度分布",
                    labels={"x": "度", "y": "节点数量"}
                )
                plots["degree_distribution"] = fig_degree

        return plots

    def export_subgraph(self, nodes: List[str], output_path: str) -> bool:
        """导出子图"""
        if not self.graph:
            return False

        try:
            subgraph = self.graph.subgraph(nodes)

            # 转换为JSON格式
            export_data = {
                "nodes": [],
                "edges": []
            }

            # 导出节点
            for node_id, node_data in subgraph.nodes(data=True):
                export_data["nodes"].append({
                    "id": node_id,
                    **node_data
                })

            # 导出边
            for source, target, edge_data in subgraph.edges(data=True):
                export_data["edges"].append({
                    "source": source,
                    "target": target,
                    **edge_data
                })

            # 保存到文件
            save_json(export_data, output_path)
            return True

        except Exception as e:
            logger.error(f"导出子图失败: {e}")
            return False

    def search_nodes(self, query: str) -> List[Dict[str, Any]]:
        """搜索节点"""
        if not self.graph:
            return []

        results = []
        query_lower = query.lower()

        for node_id, node_data in self.graph.nodes(data=True):
            # 搜索节点标签
            label = node_data.get('label', '').lower()
            if query_lower in label:
                results.append({
                    "id": node_id,
                    "label": node_data.get('label', ''),
                    "type": node_data.get('type', ''),
                    "language": node_data.get('language', ''),
                    "match_type": "label"
                })

        return results


# 便利函数
def create_knowledge_viewer() -> KnowledgeGraphViewer:
    """创建知识图谱查看器"""
    return KnowledgeGraphViewer()


def load_default_knowledge_graph() -> KnowledgeGraphViewer:
    """加载默认知识图谱"""
    viewer = KnowledgeGraphViewer()

    # 尝试加载默认路径的知识图谱
    default_paths = [
        "outputs/kg/knowledge_graph.json",
        "data/knowledge_graph.json",
        "outputs/kg/demo_kg.json"
    ]

    for path in default_paths:
        if os.path.exists(path):
            if viewer.load_knowledge_graph(path):
                logger.info(f"成功加载知识图谱: {path}")
                break
    else:
        logger.warning("未找到默认知识图谱文件")

    return viewer


def generate_sample_knowledge_graph() -> KnowledgeGraphViewer:
    """生成示例知识图谱"""
    viewer = KnowledgeGraphViewer()
    viewer.graph = nx.MultiDiGraph()

    # 示例节点
    nodes = [
        ("concept_001", {"label": "虚拟式", "type": "Concept", "language": "zh"}),
        ("concept_002", {"label": "语法", "type": "Concept", "language": "zh"}),
        ("concept_003", {"label": "subjonctif", "type": "Concept", "language": "fr"}),
        ("activity_001", {"label": "语法练习", "type": "Activity", "language": "zh"}),
        ("outcome_001", {"label": "掌握虚拟式", "type": "Outcome", "language": "zh"}),
        ("resource_001", {"label": "法语语法书", "type": "Resource", "language": "zh"})
    ]

    # 示例边
    edges = [
        ("concept_001", "concept_002", {"type": "belongsTo", "confidence": 0.9}),
        ("concept_001", "concept_003", {"type": "translatedAs", "confidence": 1.0}),
        ("concept_001", "activity_001", {"type": "supports", "confidence": 0.8}),
        ("activity_001", "outcome_001", {"type": "tests", "confidence": 0.9}),
        ("concept_002", "resource_001", {"type": "covers", "confidence": 0.7})
    ]

    viewer.graph.add_nodes_from(nodes)
    viewer.graph.add_edges_from(edges)

    return viewer


if __name__ == "__main__":
    # 简单测试
    viewer = generate_sample_knowledge_graph()
    stats = viewer.get_statistics()

    print("知识图谱统计:")
    for key, value in stats.items():
        print(f"  {key}: {value}")