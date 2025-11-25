#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GCN-Align: Cross-lingual Entity Alignment using Graph Convolutional Networks
Wang et al. (2018). EMNLP.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv
from torch_geometric.data import Data
from typing import List, Dict, Tuple, Optional
import numpy as np
from tqdm import tqdm

from ..utils.logger import logger
from .mtrans_e import AlignmentPair


class GCNEncoder(nn.Module):
    """Graph Convolutional Network Encoder"""
    
    def __init__(self, num_nodes: int, embedding_dim: int = 100, 
                 hidden_dim: int = 256, num_layers: int = 2, dropout: float = 0.3):
        super().__init__()
        self.embedding = nn.Embedding(num_nodes, embedding_dim)
        nn.init.xavier_uniform_(self.embedding.weight)
        
        self.convs = nn.ModuleList()
        self.convs.append(GCNConv(embedding_dim, hidden_dim))
        for _ in range(num_layers - 2):
            self.convs.append(GCNConv(hidden_dim, hidden_dim))
        if num_layers > 1:
            self.convs.append(GCNConv(hidden_dim, embedding_dim))
        
        self.dropout = nn.Dropout(dropout)
        self.num_layers = num_layers
    
    def forward(self, node_ids: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        x = self.embedding(node_ids)
        for i, conv in enumerate(self.convs):
            x = conv(x, edge_index)
            if i < self.num_layers - 1:
                x = F.relu(x)
                x = self.dropout(x)
        x = F.normalize(x, p=2, dim=1)
        return x


class GCNAlign:
    """GCN-Align model for entity alignment"""
    
    def __init__(self, embedding_dim: int = 100, hidden_dim: int = 256,
                 num_layers: int = 2, learning_rate: float = 0.001,
                 margin: float = 0.5, temperature: float = 0.1,
                 dropout: float = 0.3, device: str = "cuda" if torch.cuda.is_available() else "cpu",
                 hard_negative_top_k: int = 50):
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.learning_rate = learning_rate
        self.margin = margin
        self.temperature = temperature
        self.device = torch.device(device)
        self.model = None
        self.entity_to_id = {}
        self.id_to_entity = {}
        self.graph_data = None
        # Hard negative mining参数：在每个正样本周围选取最接近的非对齐实体作为负样本
        # 设置为0将退化为随机负样本采样
        self.hard_negative_top_k = hard_negative_top_k
    
    def _build_graph(self, kg1_triples, kg2_triples, seed_alignments):
        logger.info("Building joint graph...")
        entities = set()
        for h, r, t in kg1_triples + kg2_triples:
            entities.add(h)
            entities.add(t)
        
        self.entity_to_id = {entity: idx for idx, entity in enumerate(sorted(entities))}
        self.id_to_entity = {idx: entity for entity, idx in self.entity_to_id.items()}
        num_nodes = len(entities)
        
        edges = []
        for h, r, t in kg1_triples + kg2_triples:
            h_id = self.entity_to_id[h]
            t_id = self.entity_to_id[t]
            edges.append([h_id, t_id])
            edges.append([t_id, h_id])
        
        for pair in seed_alignments:
            e1_id = self.entity_to_id.get(pair.entity1)
            e2_id = self.entity_to_id.get(pair.entity2)
            if e1_id is not None and e2_id is not None:
                edges.append([e1_id, e2_id])
                edges.append([e2_id, e1_id])
        
        if len(edges) == 0:
            edge_index = torch.tensor([[i, i] for i in range(num_nodes)], dtype=torch.long).t()
        else:
            edge_index = torch.tensor(edges, dtype=torch.long).t()
        
        node_ids = torch.arange(num_nodes, dtype=torch.long)
        data = Data(x=node_ids, edge_index=edge_index, num_nodes=num_nodes)
        logger.info(f"Graph built: {num_nodes} nodes, {edge_index.shape[1]} edges")
        return data
    
    def train(self, kg1_triples, kg2_triples, seed_alignments,
              validation_alignments=None, epochs=500, batch_size=256,
              neg_ratio=0.3, early_stopping_patience=30):
        logger.info("Training GCN-Align model...")
        self.graph_data = self._build_graph(kg1_triples, kg2_triples, seed_alignments)
        self.graph_data = self.graph_data.to(self.device)
        
        self.model = GCNEncoder(num_nodes=self.graph_data.num_nodes,
                               embedding_dim=self.embedding_dim,
                               hidden_dim=self.hidden_dim,
                               num_layers=self.num_layers).to(self.device)
        
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)
        
        train_pairs = [(self.entity_to_id[p.entity1], self.entity_to_id[p.entity2])
                       for p in seed_alignments
                       if p.entity1 in self.entity_to_id and p.entity2 in self.entity_to_id]
        
        history = {"loss": [], "val_hits1": []}
        best_val_hits1 = 0.0
        patience_counter = 0
        
        for epoch in range(epochs):
            self.model.train()
            epoch_loss = 0.0
            num_batches = 0
            np.random.shuffle(train_pairs)
            
            for i in range(0, len(train_pairs), batch_size):
                batch_pairs = train_pairs[i:i + batch_size]
                all_embeddings = self.model(self.graph_data.x, self.graph_data.edge_index)
                loss = self._contrastive_loss(all_embeddings, batch_pairs, neg_ratio=neg_ratio)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
                num_batches += 1
            
            avg_loss = epoch_loss / num_batches
            history["loss"].append(avg_loss)
            
            val_hits1 = 0.0
            if validation_alignments and epoch % 10 == 0:
                val_hits1 = self._validate(validation_alignments)
                history["val_hits1"].append(val_hits1)
                if val_hits1 > best_val_hits1:
                    best_val_hits1 = val_hits1
                    patience_counter = 0
                else:
                    patience_counter += 1
                if patience_counter >= early_stopping_patience:
                    logger.info(f"Early stopping at epoch {epoch}")
                    break
            
            if epoch % 50 == 0:
                logger.info(f"Epoch {epoch}/{epochs} - Loss: {avg_loss:.4f}, Val Hits@1: {val_hits1:.4f}")
        
        logger.info("Training completed")
        return history
    
    def _contrastive_loss(self, embeddings, positive_pairs, neg_ratio=0.3):
        """
        对比损失（带可选硬负样本矿挖）
        - 正样本距离: ||e1 - e2||_2
        - 负样本选择:
            • 若 hard_negative_top_k > 0: 计算 e1 到所有节点的距离，选取最接近的非 e2 节点作为 hardest negative
            • 否则：按 neg_ratio 随机采样若干负样本，取最难的一个
        - 损失: max(0, margin + pos_dist - neg_dist)
        """
        losses = []
        num_nodes = embeddings.shape[0]
        for e1_id, e2_id in positive_pairs:
            e1_emb = embeddings[e1_id]
            e2_emb = embeddings[e2_id]
            pos_dist = torch.norm(e1_emb - e2_emb, p=2)

            if self.hard_negative_top_k and self.hard_negative_top_k > 0:
                # 硬负样本：检索最近邻中排除真对齐的最接近者
                dists_all = torch.norm(embeddings - e1_emb.unsqueeze(0), p=2, dim=1)
                # 将正样本位置屏蔽为+inf，避免被选中
                dists_all[e2_id] = float('inf')
                # 取前top_k中最小距离
                topk = min(self.hard_negative_top_k, num_nodes - 1)
                neg_dist_candidates, neg_idx_candidates = torch.topk(-dists_all, k=topk, largest=True)
                # 注意：neg_dist_candidates 是负距离（因为用-排序），取其相反数还原
                hardest_neg_dist = (-neg_dist_candidates).min()
            else:
                # 随机负样本（保留最难者）
                num_neg = max(1, int(len(positive_pairs) * neg_ratio))
                neg_ids = torch.randint(0, num_nodes, (num_neg,), device=self.device)
                # 避免采到正样本实体
                neg_ids = torch.where(neg_ids == e2_id, (neg_ids + 1) % num_nodes, neg_ids)
                neg_embs = embeddings[neg_ids]
                neg_dists = torch.norm(e1_emb.unsqueeze(0) - neg_embs, p=2, dim=1)
                hardest_neg_dist = neg_dists.min()

            loss = F.relu(self.margin + pos_dist - hardest_neg_dist)
            losses.append(loss)

        return torch.mean(torch.stack(losses)) if losses else torch.tensor(0.0, device=self.device)
    
    def _validate(self, validation_alignments):
        self.model.eval()
        with torch.no_grad():
            all_embeddings = self.model(self.graph_data.x, self.graph_data.edge_index)
        hits = 0
        total = 0
        for pair in validation_alignments:
            e1_id = self.entity_to_id.get(pair.entity1)
            e2_id = self.entity_to_id.get(pair.entity2)
            if e1_id is None or e2_id is None:
                continue
            e1_emb = all_embeddings[e1_id]
            dists = torch.norm(all_embeddings - e1_emb.unsqueeze(0), p=2, dim=1)
            nearest_id = torch.argmin(dists).item()
            if nearest_id == e2_id:
                hits += 1
            total += 1
        return hits / total if total > 0 else 0.0
    
    def predict(self, source_entities, target_entities=None, top_k=10, threshold=0.8):
        self.model.eval()
        with torch.no_grad():
            all_embeddings = self.model(self.graph_data.x, self.graph_data.edge_index)
        results = []
        for source_entity in tqdm(source_entities, desc="Predicting alignments"):
            source_id = self.entity_to_id.get(source_entity)
            if source_id is None:
                results.append([])
                continue
            source_emb = all_embeddings[source_id]
            if target_entities is None:
                dists = torch.norm(all_embeddings - source_emb.unsqueeze(0), p=2, dim=1)
                candidate_ids = torch.arange(all_embeddings.shape[0])
            else:
                candidate_ids = [self.entity_to_id[e] for e in target_entities if e in self.entity_to_id]
                candidate_ids = torch.tensor(candidate_ids, device=self.device)
                candidate_embs = all_embeddings[candidate_ids]
                dists = torch.norm(candidate_embs - source_emb.unsqueeze(0), p=2, dim=1)
            similarities = 1 - (dists / (dists.max() + 1e-8))
            top_k_indices = torch.topk(similarities, min(top_k, len(similarities)), largest=True)
            candidates = []
            for idx, sim in zip(top_k_indices.indices, top_k_indices.values):
                target_id = candidate_ids[idx].item()
                target_entity = self.id_to_entity[target_id]
                confidence = sim.item()
                if target_entity == source_entity:
                    continue
                if confidence >= threshold:
                    candidates.append(AlignmentPair(entity1=source_entity, entity2=target_entity,
                                                   confidence=confidence, source="gcn_predicted"))
            results.append(candidates)
        return results
    
    def get_embeddings(self):
        self.model.eval()
        with torch.no_grad():
            all_embeddings = self.model(self.graph_data.x, self.graph_data.edge_index)
        embeddings_dict = {}
        for entity_id, entity_idx in self.entity_to_id.items():
            embeddings_dict[entity_id] = all_embeddings[entity_idx].cpu().numpy()
        return embeddings_dict
