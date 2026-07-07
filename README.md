# TalentFlow AI

面向高校与企业的 **智能招聘平台**：求职者管理简历与 AI 职位匹配，HR 发布岗位并 AI 推荐候选人，管理员统筹运营；底层集成 RAG 混合检索、LangGraph 智能投递与高德地理编码距离计算。

---

## 目录

- [功能概览](#功能概览)
- [技术栈](#技术栈)
- [系统架构](#系统架构)
- [快速开始（Docker）](#快速开始docker)
- [本地开发](#本地开发)
- [核心能力说明](#核心能力说明)
- [项目结构](#项目结构)
- [常用命令](#常用命令)
- [测试与评测](#测试与评测)
- [CI/CD](#cicd)
- [文档索引](#文档索引)
- [常见问题](#常见问题)

---

## 功能概览

### 按角色

| 角色 | 入口 | 主要功能 |
|------|------|----------|
| **求职者** | `/dashboard` | 简历 CRUD、个人所在地、职位浏览、AI 职位推荐（含通勤距离）、智能投递、成长任务 |
| **HR / 导师** | `/hr` | 工作台、职位管理（含 JD 解析）、**AI 简历推荐**（粗排 + 精排）、投递审核、培训任务 |
| **管理员** | `/admin` | 运营看板、用户 / 职位 / 简历 / 项目管理、批量文档解析 |

### 平台能力

| 模块 | 说明 |
|------|------|
| **双向 AI 推荐** | 简历 → 职位（求职者）；职位 → 简历（HR）。BM25 + FAISS 混合召回，BGE 向量 + BGE-Reranker 精排 |
| **会话式 HR 推荐** | 创建 session → 同步粗排首屏 → Celery 后台精排 → 按需「应用精排」；支持无限滚动、任务队列、JD/简历对照 |
| **智能投递** | LangGraph 编排：读简历 → 优化材料 → 可选人工审核（interrupt）→ 写入投递记录；MCP 工具访问数据库 |
| **文档解析** | PDF / Word 简历与 JD 结构化抽取 |
| **距离计算** | 用户资料 / 简历 / 职位工作地 → 高德地理编码 → Haversine 距离，卡片展示「约 N km」 |
| **异步任务** | Celery + Redis：推荐精排、智能投递、文档解析等长任务 |

---

## 技术栈

| 层级 | 选型 |
|------|------|
| 前端 | Vue 3、Vite、Element Plus、Pinia、Vue Router |
| 后端 | FastAPI、SQLAlchemy、JWT（Access + Refresh 双令牌） |
| AI / RAG | LangGraph、LangChain、FAISS、sentence-transformers |
| 模型 | BGE-small-zh-v1.5（Embedding）、BGE-Reranker-v2-m3（精排） |
| 数据 | MySQL 8、Redis 7、SQLite（LangGraph Checkpoint） |
| 地图 | 高德 Web 服务 API（地理编码，可选） |
| 部署 | Docker Compose、Nginx、GitHub Actions → Docker Hub |

---

## 系统架构

```
┌─────────────┐     ┌──────────────────────────────────────────────┐
│  浏览器      │────▶│  frontend  Vue3 + Nginx (:8080 / dev :5173)   │
└─────────────┘     └────────────────────┬─────────────────────────┘
                                         │ /api/*
                                         ▼
                        ┌────────────────────────────────────────────┐
                        │  backend  FastAPI (:8000)                  │
                        │    ├─ MySQL          业务数据 + 坐标        │
                        │    ├─ Redis          Celery + 推荐 Session  │
                        │    ├─ vector_store   职位/简历 FAISS 索引   │
                        │    ├─ data/          LangGraph Checkpoint   │
                        │    └─ MCP Server     Agent 工具 (:8002)     │
                        └────────────────┬───────────────────────────┘
                                         │
                        ┌────────────────▼───────────────────────────┐
                        │  celery-worker  精排 / 智能投递 / 解析任务    │
                        └────────────────────────────────────────────┘
```

---

## 快速开始（Docker）

### 前置条件

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 或 Docker Engine + Compose
- 内存建议 **≥ 8 GB**（Embedding + Reranker 模型较大）
- **DeepSeek / OpenAI API Key**（LLM 与 Agent 必需）
- **高德 Web 服务 Key**（距离功能可选，未配置时仅显示城市）

### 1. 配置环境变量

在项目根目录（与 `docker-compose.yml` 同级）：

```powershell
# Windows
Copy-Item .env.example .env
notepad .env
```

```bash
# macOS / Linux
cp .env.example .env && nano .env
```

**必改项：**

```env
MYSQL_ROOT_PASSWORD=强密码
MYSQL_PASSWORD=强密码
REDIS_PASSWORD=强密码
SECRET_KEY=随机长字符串
OPENAI_API_KEY=sk-xxx
OPENAI_API_BASE=https://api.deepseek.com/v1
```

**距离功能（可选）：**

```env
AMAP_WEB_KEY=高德Web服务Key
AMAP_GEOCODE_ENABLED=true
```

> Docker 只读**根目录** `.env`。本地 uvicorn 使用 `talentflow-ai-backend-bak/.env`，参考 `.env.local.example`，两者勿混用。

### 2. 构建并启动

```bash
docker compose up -d --build
```

首次构建约 **15～40 分钟**（下载 PyTorch 与 BGE 模型，见 [docs/MODELS.md](docs/MODELS.md)）。

国内网络可指定 HuggingFace 镜像：

```bash
docker compose build backend --build-arg HF_ENDPOINT=https://hf-mirror.com
```

### 3. 访问地址

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:8080 |
| API 文档 | http://localhost:8000/docs |
| 健康检查 | http://localhost:8000/ |

### 4. 初始化数据库

```bash
./scripts/init-db.sh
```

脚本会在 MySQL 容器运行且库表缺失时导入 `dandelion_tribe_schema.sql`，并在 `users` 为空时创建演示账号。

**已有库升级（所在地坐标字段）：**

```bash
mysql -u root -p dandelion_tribe < scripts/migrations/add_location_coords.sql
cd talentflow-ai-backend-bak && python scripts/backfill_geocode.py
```

---

## 本地开发

### 环境要求

本机需运行 **MySQL**（3306）和 **Redis**（6379）。复制配置：

```powershell
cd talentflow-ai-backend-bak
Copy-Item .env.local.example .env
notepad .env
```

### 启动步骤

查看 Windows 四终端启动说明：

```powershell
.\scripts\start-local.ps1
```

手动启动（conda 环境 `smart-customer-rag` 或自建 venv）：

| 终端 | 命令 | 说明 |
|------|------|------|
| 1 | `python mcp_server/server.py` | MCP 工具服务 |
| 2 | `uvicorn app.main:app --reload --port 8000` | FastAPI |
| 3 | `celery -A app.core.celery_app worker --loglevel=info --pool=solo` | Celery（Windows 需 `--pool=solo`） |
| 4 | `cd ../talentflow-ai-frontend && npm run dev` | 前端 |

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| API | http://localhost:8000/docs |

### 下载 BGE 模型

```powershell
cd talentflow-ai-backend-bak
$env:HF_ENDPOINT = "https://hf-mirror.com"   # 国内建议
python scripts/download_models.py
```

### 演示账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| zhangsan | 123456 | 管理员 |
| lisi | 123456 | 求职者 |
| wangwu | 123456 | HR / 导师 |

---

## 核心能力说明

### 求职者 · AI 职位推荐

- **入口**：用户中心 → 职位驾驶舱（JobCockpit）
- **流程**：读取默认简历 → BM25 + FAISS 混合召回 → 粗排融合 → BGE 精排 → 展示匹配职位、技能与距离
- **距离**：基于「我的所在地」（`/dashboard/profile`）与职位工作地计算
- **文档**：[docs/recommend-flow.md](docs/recommend-flow.md)

### HR · AI 简历推荐

- **入口**：HR 岗位列表 → 选择职位 → 智能推荐简历
- **流程**：
  1. `POST /hr/recommend/session` 创建会话，同步返回粗排 Top N
  2. Celery 后台对 Top 50 做 BGE 精排
  3. 用户点击「应用精排」按精排顺序重排列表
  4. 滚动加载更多（`GET .../more`）
- **交互**：左右对照（职位 JD ↔ 简历）、任务队列、session 缓存
- **文档**：[docs/recommend-state.md](docs/recommend-state.md)

### 所在地与距离

| 实体 | 字段 | 说明 |
|------|------|------|
| 用户资料 | `residence_city` / `residence_address` | 默认所在地，页面 `/dashboard/profile` |
| 简历 | `use_profile_location` | 默认 `1`：继承用户资料；设为 `0` 可单独填写 |
| 职位 | `location` / `work_address` | HR 发布时填写 |
| 坐标 | `latitude` / `longitude` | 保存时自动 geocode；历史数据用 `backfill_geocode.py` 补全 |

---

## 项目结构

```
talentflow-ai/
├── talentflow-ai-backend-bak/       # 后端
│   ├── app/
│   │   ├── api/v1/                  # 认证、用户、HR、管理员 API
│   │   ├── rag/                     # 混合检索、FAISS、Reranker
│   │   ├── services/                # 推荐、地理编码、Session 存储
│   │   ├── agents/                  # LangGraph 智能投递
│   │   └── models/                  # ORM 模型
│   ├── scripts/
│   │   ├── eval/                    # RAG / Smart Apply 评测
│   │   ├── acceptance/              # 推荐功能验收
│   │   ├── backfill_geocode.py      # 批量补全坐标
│   │   └── reindex_resumes.py       # 重建简历向量索引
│   ├── vector_store/                # FAISS 索引（职位 + 简历）
│   └── mcp_server/                  # MCP 工具服务
├── talentflow-ai-frontend/          # Vue 3 前端
│   └── src/
│       ├── views/hr/                # HR 岗位、简历推荐
│       ├── views/user/dashboard/    # 简历、职位驾驶舱、个人资料
│       └── components/              # LocationPicker、RecommendMatchCard 等
├── scripts/                         # 部署、DB 初始化、本地启动
├── docs/                            # 架构与流程文档
├── docker-compose.yml
└── .github/workflows/               # CI / Docker Hub 发布
```

---

## 常用命令

```bash
# Docker 运维
docker compose ps
docker compose logs -f backend celery-worker
docker compose down

# 数据库检查
./scripts/check-db.sh

# 简历向量重建
cd talentflow-ai-backend-bak && python scripts/reindex_resumes.py

# 远程部署（Docker Hub 拉镜像）
./scripts/deploy-remote.sh
```

---

## 测试与评测

```bash
# 全链路冒烟（需 MySQL + Redis + API + Celery + MCP）
cd talentflow-ai-backend-bak
python scripts/smoke_test.py

# HR 简历推荐验收
bash scripts/acceptance/resume_recommend/run_all.sh

# RAG 评测 CLI
python scripts/eval/cli.py --help
```

---

## CI/CD

| 工作流 | 触发 | 作用 |
|--------|------|------|
| `ci.yml` | PR / push | 后端检查 + Docker 构建验证 |
| `publish-dockerhub.yml` | 合并 main | 构建镜像推送 Docker Hub，可选 SSH 部署 |

详见 [docs/CI_CD.md](docs/CI_CD.md)、[docs/DEPLOY_SSH.md](docs/DEPLOY_SSH.md)。

---

## 文档索引

| 文档 | 内容 |
|------|------|
| [docs/DEPLOY.md](docs/DEPLOY.md) | Docker 部署指南 |
| [docs/DOCKER_INSTALL.md](docs/DOCKER_INSTALL.md) | Docker 安装与国内镜像 |
| [docs/MODELS.md](docs/MODELS.md) | BGE 模型下载策略 |
| [docs/function-structure.md](docs/function-structure.md) | 功能结构图 |
| [docs/recommend-flow.md](docs/recommend-flow.md) | 求职者职位推荐流程 |
| [docs/recommend-state.md](docs/recommend-state.md) | 推荐会话状态机 |
| [docs/smart-apply-flow.md](docs/smart-apply-flow.md) | 智能投递流程 |
| [docs/GITHUB_SSH.md](docs/GITHUB_SSH.md) | GitHub SSH 推送配置 |
| [docs/CI_CD.md](docs/CI_CD.md) | CI/CD 说明 |

---

## 常见问题

**Q：推荐卡片有城市名，但显示「未填写所在地」？**  
A：多为浏览器缓存了距离功能上线前的旧 session 数据。强刷（Ctrl+Shift+R）或点击推荐页刷新按钮；仍无效时清除 `sessionStorage` 中以 `resume_recommend_` 开头的键。

**Q：有城市但没有公里数？**  
A：检查 `talentflow-ai-backend-bak/.env` 中 `AMAP_WEB_KEY` 是否配置并重启后端；对历史记录运行 `python scripts/backfill_geocode.py`。

**Q：HR 精排一直「排队中」？**  
A：确认 Celery Worker 已启动；Windows 本地必须使用 `--pool=solo`。

**Q：Docker 与本地 `.env` 区别？**  
A：根目录 `.env` 供 Docker Compose；`talentflow-ai-backend-bak/.env` 供本地 uvicorn/celery，数据库 host 通常为 `localhost` 而非容器服务名。

---

## License

本项目仅供学习与研究使用。
