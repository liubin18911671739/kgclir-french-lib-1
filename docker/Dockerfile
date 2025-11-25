# syntax=docker/dockerfile:1

ARG PY_BASE=python:3.10-slim
FROM ${PY_BASE} as builder

ENV PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.7.1

RUN apt-get update && apt-get install -y --no-install-recommends build-essential git && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./

# 安装依赖（按项目 requirements.txt）
RUN pip install --upgrade pip && pip install -r requirements.txt

# 下载spaCy模型
RUN python -m spacy download en_core_web_sm && \
    python -m spacy download fr_core_news_sm && \
    python -m spacy download zh_core_web_sm

COPY . .

FROM ${PY_BASE} as runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 仅复制必要文件以减小镜像
COPY --from=builder /app /app

EXPOSE 8000 7860

CMD ["uvicorn", "src.app.api:app", "--host", "0.0.0.0", "--port", "8000"]

