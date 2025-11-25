#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RAG-based Exercise Generation
RAG练习生成

目标:
- 基于查询与KG证据生成可自动评测的练习题（选择/填空/翻译/改错）
- 优先使用环境API (OpenAI/Anthropic)，不可用则使用本地启发式降级生成
- 强制引用证据并返回规范化JSON，便于前端/评测解析

引用:
- Lewis et al. (2020). Retrieval-Augmented Generation. NeurIPS.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from ..utils.logger import logger
from ..kg.ontology import FLOOntology, RelationType
from ..retrieval.kg_expansion import KGQueryExpander


class RAGExerciseGenerator:
    """
    RAG练习生成器

    Args:
        ontology: FLO本体（用于证据检索）
        kg_expander: 知识图谱查询扩展器（可选）
        provider: LLM提供方: "openai" | "anthropic" | None
        model: 模型名称（可选）
    """

    def __init__(
        self,
        ontology: FLOOntology,
        kg_expander: Optional[KGQueryExpander] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.ontology = ontology
        self.kg_expander = kg_expander
        self.provider = provider
        self.model = model

    # ========== Evidence Retrieval ==========
    def retrieve_evidence(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        使用KG进行证据检索（实体+关系片段）
        策略: 匹配实体名与别名 +（可选）扩展相关实体，按简单匹配打分
        """
        logger.info(f"Retrieving KG evidence for query: {query}")
        candidates = []

        # 1) 匹配实体
        q_lower = query.lower()
        for eid, e in self.ontology.entities.items():
            score = 0
            if e.name.lower() in q_lower or q_lower in e.name.lower():
                score += 2
            for alias in getattr(e, "aliases", []) or []:
                if alias.lower() in q_lower or q_lower in alias.lower():
                    score += 1
                    break
            if score > 0:
                candidates.append((eid, score))

        # 2) 扩展实体
        if self.kg_expander is not None:
            expanded = self.kg_expander.expand_query(query, top_k=10)
            for term, w in expanded.items():
                for eid, e in self.ontology.entities.items():
                    if term.lower() in e.name.lower():
                        candidates.append((eid, 1 + w))

        # 去重并排序
        seen = {}
        for eid, s in candidates:
            seen[eid] = max(seen.get(eid, 0), s)
        ranked = sorted(seen.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # 构造证据条目
        evidences: List[Dict[str, Any]] = []
        for eid, s in ranked:
            e = self.ontology.entities[eid]
            neighbors = []
            for nb_id, rel_type in self.ontology.adjacency_list.get(eid, []):
                nb = self.ontology.entities.get(nb_id)
                if nb:
                    neighbors.append({
                        "relation": rel_type.value,
                        "target": nb.name,
                        "target_id": nb_id,
                    })
            evidences.append({
                "entity_id": eid,
                "name": e.name,
                "language": e.language,
                "type": e.entity_type.value,
                "neighbors": neighbors[:10],
                "score": float(s),
            })
        return evidences

    # ========== Prompt ==========
    def build_prompt(self, query: str, evidences: List[Dict[str, Any]], num_questions: int = 5) -> str:
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "exercises": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "type": {"type": "string", "enum": ["mcq", "cloze", "translate", "correct"]},
                            "question": {"type": "string"},
                            "options": {"type": "array", "items": {"type": "string"}},
                            "answer": {"type": "string"},
                            "explanation": {"type": "string"},
                            "evidence_refs": {"type": "array", "items": {"type": "integer"}}
                        },
                        "required": ["id", "type", "question", "answer", "evidence_refs"]
                    }
                }
            },
            "required": ["query", "exercises"]
        }
        evidence_text = []
        for i, ev in enumerate(evidences):
            neighbors_str = ", ".join([f"-({n['relation']})-> {n['target']}" for n in ev.get("neighbors", [])])
            evidence_text.append(f"[{i}] {ev['name']} ({ev['type']}) | {neighbors_str}")
        prompt = (
            "You are a French learning assistant. Generate exercises strictly in JSON.\n"
            "Types: mcq, cloze, translate, correct. Cite evidence by indices.\n"
            f"Query: {query}\n"
            "Evidence:\n" + "\n".join(evidence_text) + "\n" +
            f"JSON Schema: {json.dumps(schema)}\n"
            f"Number of exercises: {num_questions}. Ensure valid JSON only."
        )
        return prompt

    # ========== LLM Calls ==========
    def _call_openai(self, prompt: str) -> Optional[str]:
        try:
            import openai
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return None
            openai.api_key = api_key
            # 使用新的Chat Completions接口
            client = openai.OpenAI()
            model = self.model or "gpt-4o-mini"
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.warning(f"OpenAI call failed: {e}")
            return None

    def _call_anthropic(self, prompt: str) -> Optional[str]:
        try:
            import anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                return None
            client = anthropic.Anthropic(api_key=api_key)
            model = self.model or "claude-3-5-sonnet-20241022"
            msg = client.messages.create(
                model=model,
                max_tokens=1000,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}],
            )
            # API返回结构可能有变动，这里处理常见形式
            txt = "".join([b.get("text", "") if isinstance(b, dict) else str(b) for b in getattr(msg, "content", [])])
            return txt or None
        except Exception as e:
            logger.warning(f"Anthropic call failed: {e}")
            return None

    # ========== Fallback ==========
    def _generate_mock(self, query: str, evidences: List[Dict[str, Any]], num_questions: int = 5) -> Dict[str, Any]:
        exercises = []
        for i in range(min(num_questions, len(evidences))):
            ev = evidences[i]
            qid = f"q{i+1}"
            qtext = f"请根据证据[{i}]：{ev['name']}，选择正确的关系或含义。"
            opts = [ev["name"], ev["name"].lower(), ev["name"].upper(), ev["name"].capitalize()]
            exercises.append({
                "id": qid,
                "type": "mcq",
                "question": qtext,
                "options": opts,
                "answer": opts[0],
                "explanation": f"依据证据[{i}]与KG邻接关系。",
                "evidence_refs": [i],
            })
        return {"query": query, "exercises": exercises}

    def _extract_json(self, text: str) -> Optional[str]:
        """尝试从LLM输出中提取JSON片段"""
        if not text:
            return None
        m = re.search(r"\{[\s\S]*\}$", text.strip())
        if m:
            return m.group(0)
        m = re.search(r"\{[\s\S]*\}", text)
        return m.group(0) if m else None

    # ========== Public ==========
    def generate_exercises(self, query: str, num_questions: int = 5, top_k: int = 5) -> Dict[str, Any]:
        evidences = self.retrieve_evidence(query, top_k=top_k)
        prompt = self.build_prompt(query, evidences, num_questions=num_questions)

        raw = None
        if self.provider == "openai":
            raw = self._call_openai(prompt)
        elif self.provider == "anthropic":
            raw = self._call_anthropic(prompt)

        if raw:
            json_str = self._extract_json(raw) or raw
            try:
                data = json.loads(json_str)
                # 基础验证
                if not isinstance(data, dict) or "exercises" not in data:
                    raise ValueError("Invalid JSON structure")
                # 限制题量
                data["exercises"] = data.get("exercises", [])[:num_questions]
                return data
            except Exception as e:
                logger.warning(f"Failed to parse LLM JSON, fallback to mock: {e}")

        # Fallback: 本地启发式
        return self._generate_mock(query, evidences, num_questions=num_questions)
