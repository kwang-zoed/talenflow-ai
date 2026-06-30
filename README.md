# TalentFlow AI

智能招聘平台：面向求职者、HR/导师与管理员，提供 AI 职位推荐、智能投递、简历/JD 解析与成长任务管理。

## 功能概览

| 角色 | 主要能力 |
|------|----------|
| **求职者** | 简历管理、浏览职位、AI 职位推荐、智能投递（LangGraph + 人工审核）、成长任务 |
| **HR / 导师** | 工作台看板、职位与培训任务管理、投递审核 |
| **管理员** | 运营统计、用户/职位/简历/项目管理、批量文档解析 |

**平台能力层**

- **职位推荐**：BM25 + FAISS 混合检索，BGE 向量 embedding 与 rerank 精排
- **智能投递**：LangGraph Agent 编排，MCP 工具读写数据库，支持人工中断确认
- **文档解析**：PDF / Word 职位 JD 与简历结构化解析
- **异步任务**：Celery + Redis 处理推荐与投递长任务

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3、Vite、Element Plus、Pinia、Vue Router |
| 后端 | FastAPI、SQLModel / SQLAlchemy、JWT 认证 |
| AI / RAG | LangGraph、LangChain、FAISS、sentence-transformers、BGE |
| 数据 | MySQL 8、Redis 7、SQLite（LangGraph checkpoint） |
| 部署 | Docker Compose、Nginx、GitHub Actions |

## 系统架构

```
浏览器 → frontend (Nginx :80)
            └─ /api/* → backend (FastAPI :8000)
                              ├─ MySQL（业务数据）
                              ├─ Redis（Celery 队列）
                              ├─ vector_store（FAISS 向量库）
                              ├─ data（LangGraph checkpoint）
                              └─ MCP Server :8002（Agent 工具）

celery-worker ─ 职位推荐 / 智能投递异步任务
```

## 快速开始

### 前置条件

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 或 Docker Engine + Compose
- 内存建议 **≥ 8GB**（embedding + reranker 模型较大）
- **DeepSeek / OpenAI API Key**（用于 LLM 与 Agent）

### 1. 配置环境变量

在项目根目录（与 `docker-compose.yml` 同级）：

```powershell
# Windows
Copy-Item .env.example .env
notepad .env
```

```bash
# macOS / Linux
cp .env.example .env
nano .env
```

至少修改以下项：

```env
MYSQL_ROOT_PASSWORD=你的强密码
MYSQL_PASSWORD=你的强密码
REDIS_PASSWORD=你的强密码
SECRET_KEY=随机长字符串
OPENAI_API_KEY=sk-xxx
OPENAI_API_BASE=https://api.deepseek.com/v1
```

> Docker Compose 只读取**根目录** `.env`，与 `talentflow-ai-backend-bak/.env`（本地 uvicorn 用）不要混用。

### 2. 启动服务

```bash
docker compose up -d --build
```

首次构建约 **15～40 分钟**（PyTorch + BGE 模型下载，见 [docs/MODELS.md](docs/MODELS.md)）。

国内网络构建时可指定 HuggingFace 镜像：

```bash
docker compose build backend --build-arg HF_ENDPOINT=https://hf-mirror.com
```

### 3. 访问

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:8080 |
| API 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/ |

### 4. 初始化数据库（可选）

FastAPI 启动时会自动创建部分表。完整业务 schema 可手动导入：

```bash
./scripts/init-db.sh
```

## 本地开发

### 后端

```powershell
cd talentflow-ai-backend-bak
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 下载 BGE 模型（国内建议设 HF 镜像）
$env:HF_ENDPOINT = "https://hf-mirror.com"
python scripts/download_models.py

# 需本地 MySQL + Redis，参考 .env.local.example
uvicorn app.main:app --reload --port 8000
```

另开终端启动 Celery 与 MCP：

```powershell
celery -A app.core.celery_app worker --loglevel=info
python mcp_server/server.py
```

### 前端

```powershell
cd talentflow-ai-frontend
npm install
npm run dev
```

开发环境 API 代理见 `talentflow-ai-frontend/.env.development`。

## 项目结构

```
talentflow-ai/
├── talentflow-ai-backend-bak/   # FastAPI 后端、RAG、LangGraph Agent、MCP
├── talentflow-ai-frontend/      # Vue 3 前端
├── docker-compose*.yml          # 本地 / 生产 / 镜像拉取等 Compose 配置
├── scripts/                     # 构建、部署、数据库初始化脚本
├── docs/                        # 架构图、流程图、部署与 CI 文档
└── .github/workflows/           # CI 与 Docker Hub 发布
```

## 常用命令

```bash
# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f backend celery-worker

# 停止（保留数据）
docker compose down

# 生产服务器部署（Hub 拉镜像）
./scripts/deploy-server.sh
```

## CI/CD

- **CI**（`.github/workflows/ci.yml`）：PR / push 时后端静态检查 + Docker 构建验证
- **Publish**（`.github/workflows/publish-dockerhub.yml`）：合并到 main 后构建并推送镜像到 Docker Hub，可选 SSH 自动部署

详见 [docs/CI_CD.md](docs/CI_CD.md)。

## 文档索引

| 文档 | 说明 |
|------|------|
| [docs/DEPLOY.md](docs/DEPLOY.md) | Docker 部署完整指南 |
| [docs/DOCKER_INSTALL.md](docs/DOCKER_INSTALL.md) | Docker 安装与国内镜像 |
| [docs/MODELS.md](docs/MODELS.md) | BGE 模型下载与 Git 策略 |
| [docs/function-structure.md](docs/function-structure.md) | 功能结构图 |
| [docs/recommend-flow.md](docs/recommend-flow.md) | 职位推荐流程 |
| [docs/smart-apply-flow.md](docs/smart-apply-flow.md) | 智能投递流程 |
| [docs/CI_CD.md](docs/CI_CD.md) | CI/CD 流程 |
| [docs/DEPLOY_SSH.md](docs/DEPLOY_SSH.md) | SSH 自动部署 |

## License

本项目仅供学习与研究使用。
