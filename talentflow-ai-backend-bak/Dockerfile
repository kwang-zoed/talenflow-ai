# 默认 DaoCloud 镜像，避免国内直连 auth.docker.io 超时
ARG PYTHON_BASE=docker.m.daocloud.io/library/python:3.11-slim-bookworm
FROM ${PYTHON_BASE}

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 120 -r requirements.txt \
    && pip install -i https://pypi.tuna.tsinghua.edu.cn/simple huggingface_hub

# 模型不进 Git（体积 >2GB）；构建时从 HuggingFace / 镜像站拉取
ARG HF_ENDPOINT=https://hf-mirror.com
ENV HF_ENDPOINT=${HF_ENDPOINT}
COPY scripts/download_models.py ./scripts/download_models.py
RUN mkdir -p app && python scripts/download_models.py

COPY app ./app
COPY mcp_server ./mcp_server
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

RUN mkdir -p uploads/jobs data vector_store

EXPOSE 8000 8002

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
