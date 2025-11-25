#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Learner Modeling
学习者建模

功能:
- 掌握度估计: M(c) = (n_c/N_c) * w1 + coverage_rate(c) * w2, 再乘遗忘项
- 遗忘曲线: Exponential decay based on time since last success
- 学习者画像存储: SQLite (learners, concept_mastery, exercise_log)
- 进度追踪: 整体与按概念的准确率/尝试次数

学术引用:
- Corbett & Anderson (1995). Knowledge Tracing. User Modeling and User-Adapted Interaction.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from ..utils.logger import logger
from ..kg.ontology import FLOOntology, RelationType


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LearnerDB:
    """SQLite后端，用于持久化学习者画像与练习日志"""

    def __init__(self, db_path: str = "data/learning/learner.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self._create_tables()

    def _create_tables(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS learners (
                learner_id TEXT PRIMARY KEY,
                current_level TEXT,
                mastery_threshold REAL,
                created_at TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS concept_mastery (
                learner_id TEXT,
                concept_id TEXT,
                attempts INTEGER DEFAULT 0,
                successes INTEGER DEFAULT 0,
                last_attempt_at TEXT,
                last_success_at TEXT,
                PRIMARY KEY (learner_id, concept_id)
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS exercise_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                learner_id TEXT,
                concept_id TEXT,
                question_id TEXT,
                difficulty REAL,
                success INTEGER,
                response_time REAL,
                created_at TEXT
            );
            """
        )
        self.conn.commit()

    def upsert_learner(self, learner_id: str, current_level: str, mastery_threshold: float) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO learners (learner_id, current_level, mastery_threshold, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(learner_id) DO UPDATE SET
                current_level=excluded.current_level,
                mastery_threshold=excluded.mastery_threshold
            """,
            (learner_id, current_level, mastery_threshold, utcnow_iso()),
        )
        self.conn.commit()

    def update_concept_stats(self, learner_id: str, concept_id: str, success: bool) -> None:
        cur = self.conn.cursor()
        now = utcnow_iso()
        # Ensure row exists
        cur.execute(
            """
            INSERT INTO concept_mastery (learner_id, concept_id, attempts, successes, last_attempt_at, last_success_at)
            VALUES (?, ?, 0, 0, NULL, NULL)
            ON CONFLICT(learner_id, concept_id) DO NOTHING
            """,
            (learner_id, concept_id),
        )
        # Update stats
        if success:
            cur.execute(
                """
                UPDATE concept_mastery
                   SET attempts = attempts + 1,
                       successes = successes + 1,
                       last_attempt_at = ?,
                       last_success_at = ?
                 WHERE learner_id = ? AND concept_id = ?
                """,
                (now, now, learner_id, concept_id),
            )
        else:
            cur.execute(
                """
                UPDATE concept_mastery
                   SET attempts = attempts + 1,
                       last_attempt_at = ?
                 WHERE learner_id = ? AND concept_id = ?
                """,
                (now, learner_id, concept_id),
            )
        self.conn.commit()

    def log_exercise(
        self,
        learner_id: str,
        concept_id: str,
        question_id: str,
        difficulty: float,
        success: bool,
        response_time: float,
    ) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO exercise_log(learner_id, concept_id, question_id, difficulty, success, response_time, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (learner_id, concept_id, question_id, float(difficulty), int(success), float(response_time), utcnow_iso()),
        )
        self.conn.commit()

    def get_concept_stats(self, learner_id: str, concept_id: str) -> Tuple[int, int, Optional[str]]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT attempts, successes, last_success_at FROM concept_mastery WHERE learner_id=? AND concept_id=?",
            (learner_id, concept_id),
        )
        row = cur.fetchone()
        if not row:
            return 0, 0, None
        return int(row[0] or 0), int(row[1] or 0), row[2]

    def recent_accuracy(self, learner_id: str, concept_id: Optional[str] = None, k: int = 10) -> float:
        cur = self.conn.cursor()
        if concept_id:
            cur.execute(
                """
                SELECT success FROM exercise_log
                 WHERE learner_id=? AND concept_id=?
                 ORDER BY id DESC LIMIT ?
                """,
                (learner_id, concept_id, k),
            )
        else:
            cur.execute(
                "SELECT success FROM exercise_log WHERE learner_id=? ORDER BY id DESC LIMIT ?",
                (learner_id, k),
            )
        rows = cur.fetchall()
        if not rows:
            return 0.0
        return sum(int(r[0]) for r in rows) / len(rows)


@dataclass
class LearnerModel:
    """
    学习者模型（与 PathRecommender 兼容接口）

    属性:
        mastered_concepts: 已掌握概念集合
    方法:
        compute_mastery, is_mastered, update_progress
    """

    learner_id: str
    current_level: str = "A1"
    mastery_threshold: float = 0.7
    w1: float = 0.6  # 成功率权重
    w2: float = 0.4  # 覆盖率权重
    forgetting_lambda: float = 0.1  # 遗忘速率（天）
    ontology: Optional[FLOOntology] = None
    db: Optional[LearnerDB] = None

    def __post_init__(self):
        if self.db is None:
            self.db = LearnerDB()
        self.db.upsert_learner(self.learner_id, self.current_level, self.mastery_threshold)
        self.mastered_concepts: set = set()

    # ========== Mastery ==========
    def _coverage_rate(self, concept_id: str) -> float:
        """
        覆盖率: 先修概念中已掌握的比例
        """
        if not self.ontology:
            return 0.0
        prereqs = []
        # 通过邻接反向扫描 hasPrereq 的前置（target->source）
        for src, rel_type in self.ontology.adjacency_list.get(concept_id, []):
            # 注意本体定义是 source->target, hasPrereq: concept -> prereq
            # 这里需要反向查找：找到有边 concept_id -hasPrereq-> prereq
            # adjacency_list[current] 列举的是 (neighbor, relation_type)
            # 因此对 concept_id 的邻居中，hasPrereq 的 neighbor 即为 prereq
            if rel_type == RelationType.HAS_PREREQ:
                prereqs.append(src)
        if not prereqs:
            return 1.0
        mastered = sum(1 for p in prereqs if p in self.mastered_concepts)
        return mastered / len(prereqs)

    def _forgetting_factor(self, last_success_at: Optional[str]) -> float:
        """
        遗忘因子: f = exp(-lambda * days_since_last_success)
        """
        if not last_success_at:
            return 1.0
        try:
            t = datetime.fromisoformat(last_success_at)
        except Exception:
            return 1.0
        delta_days = max(0.0, (datetime.now(timezone.utc) - t).total_seconds() / 86400.0)
        import math

        return math.exp(-self.forgetting_lambda * delta_days)

    def compute_mastery(self, concept_id: str) -> float:
        """
        计算单个概念掌握度 M(c)
        M(c) = (n_c/N_c) * w1 + coverage_rate(c) * w2, 再乘 f_forgetting
        """
        attempts, successes, last_success = self.db.get_concept_stats(self.learner_id, concept_id)
        success_ratio = (successes / attempts) if attempts > 0 else 0.0
        coverage = self._coverage_rate(concept_id)
        base = self.w1 * success_ratio + self.w2 * coverage
        mastery = max(0.0, min(1.0, base)) * self._forgetting_factor(last_success)
        return mastery

    def is_mastered(self, concept_id: str) -> bool:
        return self.compute_mastery(concept_id) >= self.mastery_threshold

    def update_progress(
        self,
        concept_id: str,
        success: bool,
        question_id: str = "",
        difficulty: float = 0.5,
        response_time: float = 0.0,
    ) -> float:
        """
        更新练习记录与统计，并返回更新后的掌握度
        """
        self.db.log_exercise(self.learner_id, concept_id, question_id, difficulty, success, response_time)
        self.db.update_concept_stats(self.learner_id, concept_id, success)

        mastery = self.compute_mastery(concept_id)
        if mastery >= self.mastery_threshold:
            self.mastered_concepts.add(concept_id)
        return mastery

    # ========== Metrics ==========
    def overall_accuracy(self, k_recent: int = 50) -> float:
        return self.db.recent_accuracy(self.learner_id, None, k=k_recent)

    def concept_accuracy(self, concept_id: str, k_recent: int = 10) -> float:
        return self.db.recent_accuracy(self.learner_id, concept_id, k=k_recent)

    def get_concept_stats(self, concept_id: str) -> Dict:
        attempts, successes, last_success = self.db.get_concept_stats(self.learner_id, concept_id)
        return {
            "attempts": attempts,
            "successes": successes,
            "accuracy": (successes / attempts) if attempts > 0 else 0.0,
            "last_success_at": last_success,
            "mastery": self.compute_mastery(concept_id),
        }
