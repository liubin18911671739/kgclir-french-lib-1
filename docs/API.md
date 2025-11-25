# KG-CLIR API 文档

本文件描述 FastAPI 后端提供的核心接口：/health、/search、/recommend、/exercise。

## 基本信息

- Base URL: `http://localhost:8000`
- OpenAPI: `/openapi.json`
- Swagger UI: `/docs`
- ReDoc: `/redoc`

## 认证

当前不要求认证。生产环境可在 `config/app.yaml` 中启用 API Key 或 JWT。

## 错误返回格式

```
{
  "status": "error",
  "message": "错误说明"
}
```

## 1. GET /health

健康检查。

- Response 200
```
{
  "status": "ok",
  "entities": 0,
  "relations": 0
}
```

## 2. POST /search

跨语言检索。返回融合后的排序结果和（可选）KG扩展词。

- Request (application/json)
```
{
  "query": "法语虚拟式用法",
  "language": "zh",
  "top_k": 10,
  "use_kg": true
}
```

- Response 200
```
{
  "results": [
    {
      "doc_id": "doc_0",
      "title": "Document 0",
      "snippet": "Sample content...",
      "language": "fr",
      "score": 0.83,
      "scores_breakdown": {"bm25": 0.80, "dense": 0.78, "kg": 0.70}
    }
  ],
  "total": 10,
  "query": "法语虚拟式用法",
  "query_expansion": ["subjonctif", "语法"],
  "processing_time_ms": 25.4
}
```

## 3. POST /recommend

学习路径推荐（基于知识图谱的先修关系 + 学习者画像）。

- Request
```
{
  "user_id": "u1",
  "target_level": "B1",
  "max_nodes": 15
}
```

- Response 200
```
{
  "user_id": "u1",
  "target_level": "B1",
  "path_nodes": [
    {"entity_id":"e1","name":"subjonctif","difficulty":0.6,"estimated_time":30,"prerequisites":["e0"]}
  ],
  "path_edges": [["e0","e1"]],
  "total_time": 180,
  "processing_time_ms": 10.2
}
```

## 4. POST /exercise

RAG 练习生成。优先调用 LLM，不可用则使用本地启发式降级。

- Request
```
{
  "concept": "subjonctif",
  "user_level": "A2",
  "num_questions": 5
}
```

- Response 200
```
{
  "concept": "subjonctif",
  "user_level": "A2",
  "exercises": [
    {"id":"q1","type":"mcq","question":"...","options":["A","B"],"answer":"A","explanation":"...","evidence_refs":[0]}
  ]
}
```

---

附：详见 `src/app/schemas.py` 中的 Pydantic 模型定义。

