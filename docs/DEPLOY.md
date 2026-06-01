# TalentFlow AI Docker 部署指南

## 架构概览

```
浏览器 → frontend (Nginx:80)
            └─ /api/* → backend (FastAPI:8000)
                              ├─ MySQL（业务数据）
                              ├─ Redis（Celery 队列）
                              ├─ vector_store（FAISS 向量库 volume）
                              ├─ data（LangGraph SQLite checkpoint volume）
                              └─ MCP Server:8002（简历/投递工具）

celery-worker
  ├─ 职位推荐异步任务
  ├─ 智能投递 LangGraph 任务
  └─ 共享 backend 同款镜像 + volume
```

| 服务 | 容器名 | 默认宿主机端口 | 说明 |
|------|--------|----------------|------|
| frontend | talentflow-frontend | **8080** | Vue + Nginx 反代 `/api` |
| backend | talentflow-api | 8000 | FastAPI 主 API |
| celery-worker | talentflow-celery | — | 异步推荐 / 智能投递 |
| mcp-server | talentflow-mcp | 8002 | Agent 工具服务 |
| mysql | talentflow-mysql | 3306 | 业务数据库 |
| redis | talentflow-redis | 6379 | Celery broker |

---

## 前置条件

1. 安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)（Windows/macOS）或 Docker Engine + Compose（Linux）
2. 机器内存建议 **≥ 8GB**（embedding + reranker 模型较大）
3. 准备好 **DeepSeek/OpenAI API Key**
4. 若已有 MySQL 数据 dump，见下文「导入数据库」

---

## 快速启动（推荐）

### 1. 准备环境变量

在项目根目录 `talentflow-ai/`（与 `docker-compose.yml` 同级）：

**Windows PowerShell：**

```powershell
cd C:\Users\kzd\Desktop\talentflow-ai
Copy-Item .env.example .env
# 若 .env 已存在且要覆盖：
# Copy-Item .env.example .env -Force
notepad .env
```

**macOS / Linux：**

```bash
cp .env.example .env
nano .env
```

> **两个 `.env` 不要混用**
>
> | 文件 | 用途 |
> |------|------|
> | `talentflow-ai/.env` | **Docker Compose** 读取（mysql/redis/MCP 服务名等） |
> | `talentflow-ai-backend-bak/.env` | **本地** `uvicorn` 直接启动时用（仅 API Key 等少量变量） |

复制 `.env.example` 只会得到占位符 `change_me_*`，**必须手动改密码和 API Key** 才有用；或直接使用已为你生成好的根目录 `.env`（若存在）。

```env
MYSQL_ROOT_PASSWORD=你的强密码
MYSQL_PASSWORD=你的强密码
REDIS_PASSWORD=你的强密码
OPENAI_API_KEY=sk-xxx
SECRET_KEY=随机长字符串
```

> Docker Compose 会自动把 `REDIS_URL` / `CELERY_*` 里的主机名设为 `redis`，`MYSQL_SERVER` 设为 `mysql`。

### 2. 确认模型文件在镜像内

后端镜像会打包以下目录（体积较大，首次 build 较慢）：

- `talentflow-ai-backend-bak/app/bge-small-zh-v1.5-embedding/`
- `talentflow-ai-backend-bak/app/bge-reranker-v2-m3/`

若本地没有，需先下载 BGE 模型到上述路径再 build。

### 3. 一键启动

```bash
cd talentflow-ai
docker compose up -d --build
```

首次构建可能 **15～40 分钟**（PyTorch + 模型 COPY）。

### 4. 访问

- 前端：**http://localhost:8080**
- API 文档：**http://localhost:8000/docs**
- 健康检查：`curl http://localhost:8000/`

Nginx 会把前端的 `/api` 请求转发到 `backend:8000`，无需额外配置 CORS。

---

## 数据库初始化

FastAPI 启动时会自动创建部分表（如 `user_resume_cache`、`apply_tasks`）。

**完整业务表**若你本地已有 MySQL，请导入 dump：

```bash
# 将本地 dump 导入容器内 MySQL
docker exec -i talentflow-mysql mysql -uroot -p"$MYSQL_ROOT_PASSWORD" dandelion_tribe < your_backup.sql
```

或在 MySQL 客户端连接 `localhost:3306` 执行建表脚本。

---

## 向量库（FAISS）

- 容器内路径：`/app/vector_store/`
- Docker volume：`backend_vector_store`（持久化，重启不丢）

**首次部署**若 volume 为空：

1. 登录管理端/HRMentor 端发布职位（会自动写入向量库），或
2. 把本地已有的 `vector_store/index.faiss` + `metadata.pkl` 复制进 volume：

```bash
docker cp talentflow-ai-backend-bak/vector_store/. talentflow-api:/app/vector_store/
docker compose restart backend celery-worker
```

---

## 常用运维命令

```bash
# 查看状态
docker compose ps

# 查看日志
docker compose logs -f backend
docker compose logs -f celery-worker
docker compose logs -f mcp-server

# 重启单个服务
docker compose restart celery-worker

# 停止并保留数据
docker compose down

# 停止并删除 volume（⚠️ 会清空 MySQL / 向量库 / checkpoint）
docker compose down -v
```

---

## 服务依赖与启动顺序

Compose 已配置：

1. `mysql`、`redis` healthcheck 通过
2. `mcp-server` 启动（依赖 MySQL）
3. `backend` 启动（entrypoint 等待 MySQL）
4. `celery-worker` 启动（依赖 redis + backend）
5. `frontend` 启动（依赖 backend healthcheck）

---

## 环境变量说明

| 变量 | Docker 默认值 | 说明 |
|------|---------------|------|
| `MYSQL_SERVER` | `mysql` | 容器内服务名 |
| `REDIS_HOST` | `redis` | Celery broker 主机 |
| `MCP_SERVER_URL` | `http://mcp-server:8002/mcp` | Agent 调 MCP |
| `CHECKPOINTER_BACKEND` | `sqlite` | LangGraph 断点（无需 Redis Stack） |
| `PRELOAD_MODELS_ON_STARTUP` | `false` | 启动时不阻塞预热模型 |
| `SMART_APPLY_HUMAN_REVIEW` | `true` | 智能投递人工审核 |

---

## 常见问题

### 1. 智能投递报 `NotRegistered`

Celery Worker 未加载任务模块，重启 worker：

```bash
docker compose restart celery-worker
docker compose logs celery-worker | tail -50
```

### 2. MCP 连接失败

确认 API/Worker 环境变量：

```env
MCP_SERVER_URL=http://mcp-server:8002/mcp
```

```bash
docker compose logs mcp-server
curl http://localhost:8002/mcp
```

### 3. 推荐/向量检索无结果

检查向量库 volume 是否为空，需先写入职位向量。

### 4. 内存不足 / OOM

- 将 `PRELOAD_MODELS_ON_STARTUP=false`
- Celery `--concurrency=1`（已在 compose 中配置）
- 给 Docker Desktop 分配更多内存（Settings → Resources）

### 5. Windows 路径

Compose 使用 named volume，不依赖 Windows 路径挂载，避免 CRLF/权限问题。

---

## 生产环境建议

1. 修改所有默认密码，`.env` 不要提交 git
2. 前端改用 **443 + HTTPS**（Nginx 证书或前置 Traefik/Caddy）
3. 仅暴露 `frontend:443`，**不要**对外暴露 MySQL/Redis 端口（删除 compose 中 `ports` 映射）
4. 定期备份 `mysql_data`、`backend_vector_store`、`backend_data` volume
5. 使用外部对象存储替代本地 `uploads/`（若有多实例需求）

---

## 本地开发 vs Docker

| 场景 | 命令 |
|------|------|
| 全 Docker | `docker compose up -d --build` |
| 仅基础设施 | `docker compose up -d mysql redis` |
| 本地跑 API | `uvicorn app.main:app --reload --port 8000` |
| 本地 Celery | `celery -A app.core.celery_app worker --loglevel=info --pool=solo`（Windows 需 `--pool=solo`） |
| 本地 MCP | `python mcp_server/server.py` |

本地开发时 `.env` 中把 `MYSQL_SERVER=localhost`、`REDIS_HOST=localhost`、`MCP_SERVER_URL=http://127.0.0.1:8002/mcp`。

---

**远程服务器生产部署** → 见 [DEPLOY_REMOTE.md](./DEPLOY_REMOTE.md)
