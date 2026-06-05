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
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 120 -r requirements.txt

# 模型不进 Git（体积 >2GB）。若本机 app/bge-* 已存在则跳过下载；否则构建时拉取（国内: --build-arg HF_ENDPOINT=https://hf-mirror.com）
ARG HF_ENDPOINT=
ENV HF_HUB_DOWNLOAD_TIMEOUT=600
COPY scripts/ ./scripts/
COPY app ./app
RUN if [ -n "${HF_ENDPOINT}" ]; then export HF_ENDPOINT="${HF_ENDPOINT}"; fi; \
    python -u scripts/download_models.py

COPY mcp_server ./mcp_server
COPY docker-entrypoint.sh /docker-entrypoint.sh
# Windows 检出若为 CRLF，Linux 容器内会 exec 失败；构建时统一为 LF
RUN sed -i 's/\r$//' /docker-entrypoint.sh && chmod +x /docker-entrypoint.sh

RUN mkdir -p uploads/jobs data vector_store

EXPOSE 8000 8002

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
