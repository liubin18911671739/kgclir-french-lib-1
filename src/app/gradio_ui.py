#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gradio UI
三个Tab:
- 检索
- 学习路径
- 练习生成
"""

from __future__ import annotations

import os
import json
import requests
import gradio as gr
from typing import List, Dict, Any

from ..utils.io import load_yaml


CFG = load_yaml("config/app.yaml")
API_BASE = f"http://{CFG.get('api', {}).get('server', {}).get('host', 'localhost')}:{CFG.get('api', {}).get('server', {}).get('port', 8000)}"


def _post(path: str, payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    url = API_BASE + path
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()


def ui_search(query: str, language: str, top_k: int):
    payload = {"query": query, "language": language, "top_k": int(top_k), "use_kg": True}
    data = _post(CFG["endpoints"]["search"]["path"], payload, timeout=CFG["endpoints"]["search"]["timeout"])
    lines = [f"Top {data['total']} for '{data['query']}'"]
    for r in data["results"]:
        lines.append(f"- [{r['score']:.3f}] {r.get('title') or r['doc_id']} | {r.get('snippet','')}")
    if data.get("query_expansion"):
        lines.append("\nQuery expansion: " + ", ".join(data["query_expansion"]))
    return "\n".join(lines)


def ui_recommend(user_id: str, target_level: str):
    payload = {"user_id": user_id, "target_level": target_level, "max_nodes": 15}
    data = _post(CFG["endpoints"]["recommend_path"]["path"], payload, timeout=CFG["endpoints"]["recommend_path"]["timeout"])
    nodes = data.get("path_nodes", [])
    edges = data.get("path_edges", [])
    txt = [f"Path for {data['user_id']} → {data['target_level']} | total {data['total_time']} min"]
    for n in nodes:
        txt.append(f"* {n['name']} (d={n['difficulty']:.2f}, t={n['estimated_time']}m)")
    txt.append("Edges: " + ", ".join([f"{a}->{b}" for a, b in edges]))
    return "\n".join(txt)


def ui_exercise(concept: str, user_level: str, num_questions: int):
    payload = {"concept": concept, "user_level": user_level, "num_questions": int(num_questions)}
    data = _post(CFG["endpoints"]["generate_exercise"]["path"], payload, timeout=CFG["endpoints"]["generate_exercise"]["timeout"])
    lines = [f"Exercises for {data['concept']} ({data['user_level']})"]
    for ex in data.get("exercises", []):
        lines.append(f"Q[{ex['type']}] {ex['question']}")
        if ex.get("options"):
            for i, op in enumerate(ex["options"], 1):
                lines.append(f"  {i}. {op}")
        if ex.get("answer"):
            lines.append(f"Answer: {ex['answer']}")
        if ex.get("explanation"):
            lines.append(f"Explain: {ex['explanation']}")
        lines.append("")
    return "\n".join(lines)


def launch():
    with gr.Blocks(title=CFG.get("gradio", {}).get("ui", {}).get("title", "KG-CLIR")) as demo:
        gr.Markdown(CFG.get("gradio", {}).get("ui", {}).get("description", ""))

        with gr.Tab("🔍 检索"):
            q = gr.Textbox(label="查询")
            lang = gr.Dropdown(choices=["zh", "fr", "en"], value="zh", label="语言")
            k = gr.Slider(1, 50, value=10, step=1, label="Top-K")
            out = gr.Textbox(lines=15, label="结果")
            btn = gr.Button("检索")
            btn.click(fn=ui_search, inputs=[q, lang, k], outputs=[out])

        with gr.Tab("📚 学习路径"):
            uid = gr.Textbox(value="user_1", label="学习者ID")
            lvl = gr.Dropdown(choices=["A1", "A2", "B1", "B2", "C1", "C2"], value="B1", label="目标等级")
            out2 = gr.Textbox(lines=12, label="路径")
            btn2 = gr.Button("生成路径")
            btn2.click(fn=ui_recommend, inputs=[uid, lvl], outputs=[out2])

        with gr.Tab("✏️ 练习生成"):
            concept = gr.Textbox(label="概念/知识点")
            level = gr.Dropdown(choices=["A1", "A2", "B1", "B2", "C1", "C2"], value="A2", label="学习者水平")
            n = gr.Slider(1, 10, value=5, step=1, label="题目数量")
            out3 = gr.Textbox(lines=15, label="练习")
            btn3 = gr.Button("生成")
            btn3.click(fn=ui_exercise, inputs=[concept, level, n], outputs=[out3])

    port = CFG.get("gradio", {}).get("server", {}).get("port", 7860)
    demo.launch(server_name="0.0.0.0", server_port=port, share=CFG.get("gradio", {}).get("server", {}).get("share", False))


if __name__ == "__main__":
    launch()
