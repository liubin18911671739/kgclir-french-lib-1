#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Cross-lingual Entity Alignment using MTransE
基于MTransE的跨语言实体对齐

实现 MTransE 算法：
Chen et al. (2017). Multilingual Knowledge Graph Embeddings for Cross-lingual Knowledge Alignment. IJCAI.

核心思想：
1. 分别学习各语言KG的TransE嵌入
2. 使用种子对齐作为桥梁，学习跨语言转换矩阵
3. 通过最近邻搜索发现新对齐

公式：
- TransE: h + r ≈ t (in each language)
- MTransE: M_ij * e_i ≈ e_j (cross-lingual transformation)
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from collections import defaultdict
import torch
import torch.nn as nn
import torch.optim as optim
from tqdm import tqdm

from ..utils.logger import logger


@dataclass
class AlignmentPair:
    """对齐实体对"""
    entity1: str  # 语言1的实体ID
    entity2: str  # 语言2的实体ID
    confidence: float = 1.0
    source: str = "seed"  # seed/predicted


class TransE(nn.Module):
    """
    TransE模型
    
    Bordes et al. (2013). Translating Embeddings for Modeling Multi-relational Data. NIPS.
    """
    
    def __init__(self, num_entities: int, num_relations: int, embedding_dim: int = 100):
        super().__init__()
        
        self.entity_embeddings = nn.Embedding(num_entities, embedding_dim)
        self.relation_embeddings = nn.Embedding(num_relations, embedding_dim)
        
        # Xavier初始化
        nn.init.xavier_uniform_(self.entity_embeddings.weight)
        nn.init.xavier_uniform_(self.relation_embeddings.weight)
    
    def forward(self, heads, relations, tails):
        """
        计算TransE得分
        
        Args:
            heads: 头实体ID
            relations: 关系ID
            tails: 尾实体ID
        
        Returns:
            得分（负距离）
        """
        h = self.entity_embeddings(heads)
        r = self.relation_embeddings(relations)
        t = self.entity_embeddings(tails)
        
        # L2距离
        score = torch.norm(h + r - t, p=2, dim=1)
        
        return -score  # 距离越小，得分越高


class MTransE:
    """
    MTransE跨语言对齐模型
    
    分为两个阶段：
    1. 训练各语言的TransE模型
    2. 学习跨语言转换矩阵
    """
    
    def __init__(
        self,
        embedding_dim: int = 100,
        learning_rate: float = 0.001,
        margin: float = 1.0,
        device: str = "cpu"
    ):
        self.embedding_dim = embedding_dim
        self.learning_rate = learning_rate
        self.margin = margin
        self.device = torch.device(device)
        
        # 模型存储
        self.transe_models = {}  # {language: TransE}
        self.entity_to_id = {}   # {language: {entity_name: id}}
        self.id_to_entity = {}   # {language: {id: entity_name}}
        self.relation_to_id = {} # {language: {relation: id}}
        
        # 转换矩阵
        self.transformation_matrices = {}  # {(lang1, lang2): Matrix}
    
    def build_vocabulary(
        self,
        triples: Dict[str, List[Tuple[str, str, str]]]
    ):
        """
        构建词汇表
        
        Args:
            triples: {language: [(h, r, t), ...]}
        """
        logger.info("Building vocabulary...")
        
        for lang, lang_triples in triples.items():
            # 实体词汇
            entities = set()
            relations = set()
            
            for h, r, t in lang_triples:
                entities.add(h)
                entities.add(t)
                relations.add(r)
            
            # 构建映射
            self.entity_to_id[lang] = {e: i for i, e in enumerate(sorted(entities))}
            self.id_to_entity[lang] = {i: e for e, i in self.entity_to_id[lang].items()}
            self.relation_to_id[lang] = {r: i for i, r in enumerate(sorted(relations))}
            
            logger.info(f"  {lang}: {len(entities)} entities, {len(relations)} relations")
    
    def train_transe(
        self,
        language: str,
        triples: List[Tuple[str, str, str]],
        epochs: int = 100,
        batch_size: int = 128,
        negative_samples: int = 5
    ):
        """
        训练单语言TransE模型
        
        Args:
            language: 语言代码
            triples: 三元组列表 [(h, r, t), ...]
            epochs: 训练轮数
            batch_size: 批大小
            negative_samples: 负采样数量
        """
        logger.info(f"Training TransE for {language}...")
        
        # 创建TransE模型
        num_entities = len(self.entity_to_id[language])
        num_relations = len(self.relation_to_id[language])
        
        model = TransE(num_entities, num_relations, self.embedding_dim).to(self.device)
        optimizer = optim.Adam(model.parameters(), lr=self.learning_rate)
        
        # 转换三元组为ID
        triple_ids = []
        for h, r, t in triples:
            h_id = self.entity_to_id[language][h]
            r_id = self.relation_to_id[language][r]
            t_id = self.entity_to_id[language][t]
            triple_ids.append((h_id, r_id, t_id))
        
        # 训练
        for epoch in range(epochs):
            total_loss = 0.0
            np.random.shuffle(triple_ids)
            
            for i in range(0, len(triple_ids), batch_size):
                batch = triple_ids[i:i + batch_size]
                
                # 正样本
                pos_heads = torch.LongTensor([t[0] for t in batch]).to(self.device)
                pos_rels = torch.LongTensor([t[1] for t in batch]).to(self.device)
                pos_tails = torch.LongTensor([t[2] for t in batch]).to(self.device)
                
                pos_scores = model(pos_heads, pos_rels, pos_tails)
                
                # 负采样
                neg_scores_list = []
                for _ in range(negative_samples):
                    # 随机替换头或尾
                    neg_heads = pos_heads.clone()
                    neg_tails = pos_tails.clone()
                    
                    mask = torch.rand(len(batch)) < 0.5
                    neg_heads[mask] = torch.randint(0, num_entities, (mask.sum(),)).to(self.device)
                    neg_tails[~mask] = torch.randint(0, num_entities, ((~mask).sum(),)).to(self.device)
                    
                    neg_scores = model(neg_heads, pos_rels, neg_tails)
                    neg_scores_list.append(neg_scores)
                
                neg_scores = torch.stack(neg_scores_list).mean(dim=0)
                
                # Margin loss
                loss = torch.relu(self.margin + neg_scores - pos_scores).mean()
                
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
            
            if (epoch + 1) % 20 == 0:
                logger.info(f"  Epoch {epoch + 1}/{epochs}, Loss: {total_loss:.4f}")
        
        self.transe_models[language] = model
        logger.info(f"TransE training completed for {language}")
    
    def learn_transformation(
        self,
        lang1: str,
        lang2: str,
        seed_alignments: List[AlignmentPair],
        epochs: int = 50
    ):
        """
        学习跨语言转换矩阵
        
        Args:
            lang1: 源语言
            lang2: 目标语言
            seed_alignments: 种子对齐
            epochs: 训练轮数
        """
        logger.info(f"Learning transformation matrix: {lang1} -> {lang2}")
        
        # 提取种子实体的嵌入
        model1 = self.transe_models[lang1]
        model2 = self.transe_models[lang2]
        
        embeddings1 = []
        embeddings2 = []
        
        for pair in seed_alignments:
            if pair.entity1 in self.entity_to_id[lang1] and pair.entity2 in self.entity_to_id[lang2]:
                id1 = self.entity_to_id[lang1][pair.entity1]
                id2 = self.entity_to_id[lang2][pair.entity2]
                
                emb1 = model1.entity_embeddings.weight[id1].detach().cpu().numpy()
                emb2 = model2.entity_embeddings.weight[id2].detach().cpu().numpy()
                
                embeddings1.append(emb1)
                embeddings2.append(emb2)
        
        embeddings1 = np.array(embeddings1)
        embeddings2 = np.array(embeddings2)
        
        logger.info(f"  Using {len(embeddings1)} seed pairs")
        
        # 学习转换矩阵 M: M * e1 ≈ e2
        # 使用最小二乘法：M = (E1^T E1)^-1 E1^T E2
        M = np.linalg.lstsq(embeddings1, embeddings2, rcond=None)[0]
        
        self.transformation_matrices[(lang1, lang2)] = M
        
        # 评估转换质量
        transformed = embeddings1 @ M
        mse = np.mean((transformed - embeddings2) ** 2)
        logger.info(f"  Transformation MSE: {mse:.4f}")
    
    def predict_alignments(
        self,
        lang1: str,
        lang2: str,
        top_k: int = 10,
        threshold: float = 0.7
    ) -> List[AlignmentPair]:
        """
        预测跨语言对齐
        
        Args:
            lang1: 源语言
            lang2: 目标语言
            top_k: 每个实体返回top-k候选
            threshold: 置信度阈值
        
        Returns:
            预测的对齐对
        """
        logger.info(f"Predicting alignments: {lang1} -> {lang2}")
        
        model1 = self.transe_models[lang1]
        model2 = self.transe_models[lang2]
        M = self.transformation_matrices.get((lang1, lang2))
        
        if M is None:
            logger.error(f"No transformation matrix found for {lang1} -> {lang2}")
            return []
        
        # 获取所有实体嵌入
        embeddings1 = model1.entity_embeddings.weight.detach().cpu().numpy()
        embeddings2 = model2.entity_embeddings.weight.detach().cpu().numpy()
        
        # 转换lang1的嵌入
        transformed1 = embeddings1 @ M
        
        # 计算余弦相似度
        # 归一化
        transformed1_norm = transformed1 / (np.linalg.norm(transformed1, axis=1, keepdims=True) + 1e-8)
        embeddings2_norm = embeddings2 / (np.linalg.norm(embeddings2, axis=1, keepdims=True) + 1e-8)
        
        # 相似度矩阵
        similarity = transformed1_norm @ embeddings2_norm.T
        
        # 提取top-k对齐
        alignments = []
        
        for i in range(len(embeddings1)):
            # 找到top-k最相似的
            top_indices = np.argsort(similarity[i])[-top_k:][::-1]
            
            for j in top_indices:
                score = similarity[i, j]
                
                if score >= threshold:
                    entity1 = self.id_to_entity[lang1][i]
                    entity2 = self.id_to_entity[lang2][j]
                    
                    alignments.append(AlignmentPair(
                        entity1=entity1,
                        entity2=entity2,
                        confidence=float(score),
                        source="predicted"
                    ))
        
        logger.info(f"Predicted {len(alignments)} alignment pairs")
        
        return alignments
