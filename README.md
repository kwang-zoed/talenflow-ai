<<<<<<< HEAD
# TalentFlow AI

智能招聘平台：面向求职者、HR/导师与管理员，提供 **双向 AI 推荐**（职位推简历 / 简历推职位）、智能投递、文档解析、成长任务与基于地理位置的通勤距离展示。

## 功能概览

| 角色 | 主要能力 |
|------|----------|
| **求职者** | 简历管理、个人所在地、浏览职位、AI 职位推荐（含距离）、智能投递（LangGraph + 人工审核）、成长任务 |
| **HR / 导师** | 工作台看板、职位与培训任务管理、投递审核、**AI 简历推荐**（粗排 + 按需精排、无限滚动、对照视图） |
| **管理员** | 运营统计、用户/职位/简历/项目管理、批量文档解析 |

### 平台能力层

| 能力 | 说明 |
|------|------|
| **双向推荐** | 求职者侧：简历 → 职位；HR 侧：职位 → 简历。BM25 + FAISS 混合检索，BGE embedding，BGE-Reranker 精排 |
| **会话式推荐** | HR 推荐采用 `session` 模型：首屏同步粗排，后台 Celery 精排，支持翻页、应用精排、任务队列 |
| **距离计算** | 用户资料 / 简历 / 职位工作地 → 高德地理编码 → Haversine 距离，推荐卡片展示「约 N km」 |
| **智能投递** | LangGraph Agent 编排，MCP 工具读写数据库，支持人工中断确认 |
| **文档解析** | PDF / Word 职位 JD 与简历结构化解析 |
| **异步任务** | Celery + Redis 处理推荐、精排与投递长任务 |

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3、Vite、Element Plus、Pinia、Vue Router、`element-china-area-data` |
| 后端 | FastAPI、SQLAlchemy、JWT（Access + Refresh 双令牌） |
| AI / RAG | LangGraph、LangChain、FAISS、sentence-transformers、BGE-small-zh + BGE-Reranker-v2-m3 |
| 数据 | MySQL 8、Redis 7、SQLite（LangGraph checkpoint） |
| 地图 | 高德 Web 服务 API（地理编码） |
| 部署 | Docker Compose、Nginx、GitHub Actions |

## 系统架构

```
浏览器 → frontend (Nginx :8080 / Vite :5173)
            └─ /api/* → backend (FastAPI :8000)
                              ├─ MySQL（业务数据 + 坐标字段）
                              ├─ Redis（Celery 队列 + 推荐 session 缓存）
                              ├─ vector_store（职位 FAISS + 简历 FAISS）
                              ├─ data（LangGraph checkpoint）
                              └─ MCP Server :8002（Agent 工具）

celery-worker ─ 职位/简历推荐精排、智能投递异步任务
```

## 快速开始

### 前置条件

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 或 Docker Engine + Compose
- 内存建议 **≥ 8GB**（embedding + reranker 模型较大）
- **DeepSeek / OpenAI API Key**（LLM 与 Agent）
- **高德 Web 服务 Key**（可选，用于距离计算；未配置时仅显示城市、不显示公里数）

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

# 距离功能（高德控制台 → 应用管理 → Web 服务）
AMAP_WEB_KEY=你的高德Web服务Key
AMAP_GEOCODE_ENABLED=true
```

> Docker Compose 只读取**根目录** `.env`。本地 `uvicorn` 开发使用 `talentflow-ai-backend-bak/.env`（可参考 `.env.local.example`），两者不要混用。

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

### 4. 初始化数据库

FastAPI 启动时会自动创建部分表。完整业务 schema 可手动导入：

```bash
./scripts/init-db.sh
```

首次部署脚本会自动导入 `dandelion_tribe_schema.sql` 并创建演示账号（若 users 表为空）。

**已有数据库升级**（新增所在地坐标字段）：

```bash
mysql -u root -p dandelion_tribe < scripts/migrations/add_location_coords.sql
cd talentflow-ai-backend-bak
python scripts/backfill_geocode.py   # 为已有记录补全经纬度
```

## 本地开发

### 前置：MySQL + Redis

本机需运行 **MySQL**（3306）与 **Redis**（6379）。后端配置见 `talentflow-ai-backend-bak/.env.local.example`，复制为 `talentflow-ai-backend-bak/.env` 后修改账号密码。

### 启动指引（Windows）

```powershell
# 查看四终端启动命令（MCP / API / Celery / 前端）
.\scripts\start-local.ps1
```

典型流程（conda 环境 `smart-customer-rag` 或自建 venv）：

```powershell
# 终端 1 — MCP
cd talentflow-ai-backend-bak
python mcp_server/server.py

# 终端 2 — FastAPI
cd talentflow-ai-backend-bak
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端 3 — Celery（Windows 建议 --pool=solo）
cd talentflow-ai-backend-bak
celery -A app.core.celery_app worker --loglevel=info --pool=solo

# 终端 4 — 前端
cd talentflow-ai-frontend
npm install
npm run dev
```

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| API 文档 | http://localhost:8000/docs |
| MCP | http://127.0.0.1:8002 |

### 模型下载

```powershell
cd talentflow-ai-backend-bak
$env:HF_ENDPOINT = "https://hf-mirror.com"   # 国内建议
python scripts/download_models.py
```

### 演示账号（bootstrap 后）

| 用户名 | 密码 | 角色 |
|--------|------|------|
| zhangsan | 123456 | 管理员 |
| lisi | 123456 | 求职者 |
| wangwu | 123456 | HR / 导师 |

## 核心功能说明

### 求职者：AI 职位推荐

- 入口：用户中心 → 职位驾驶舱（JobCockpit）
- 流程：读取默认简历 → BM25 + FAISS 混合召回 → 粗排 → BGE 精排 → 展示匹配职位与技能
- 距离：基于「我的所在地」与职位工作地计算通勤距离
- 详见 [docs/recommend-flow.md](docs/recommend-flow.md)

### HR：AI 简历推荐

- 入口：HR 岗位列表 → 某职位 → 智能推荐简历
- 流程：创建推荐 session → 同步返回粗排 Top N → 后台 Celery 精排 → 用户点击「应用精排」切换排序
- 交互：左右对照（职位 JD vs 简历）、无限滚动加载、任务队列、session 缓存
- 距离：基于求职者资料/简历所在地与职位工作地
- 详见 [docs/recommend-state.md](docs/recommend-state.md)

### 所在地与距离

| 数据 | 字段 | 说明 |
|------|------|------|
| 用户资料 | `residence_city` / `residence_address` | 求职者默认所在地，路径 `/dashboard/profile` |
| 简历 | `use_profile_location` | 默认继承用户资料；关闭后可单独设置 |
| 职位 | `location` / `work_address` | HR 发布职位时填写 |
| 坐标 | `latitude` / `longitude` | 保存或 backfill 时调用高德地理编码 |

保存时自动 geocode；历史数据运行 `scripts/backfill_geocode.py` 补全。

## 项目结构

```
talentflow-ai/
├── talentflow-ai-backend-bak/     # FastAPI 后端、RAG、LangGraph、MCP
│   ├── app/
│   │   ├── api/v1/                # 用户 / HR / 管理员 API
│   │   ├── rag/                   # 职位 & 简历混合检索、FAISS、Reranker
│   │   ├── services/              # 推荐、地理编码、session 存储
│   │   └── agents/                # LangGraph 智能投递
│   ├── scripts/
│   │   ├── eval/                  # RAG / Smart Apply 评测流水线
│   │   ├── acceptance/            # 推荐功能验收脚本
│   │   └── backfill_geocode.py    # 批量补全坐标
│   └── vector_store/              # FAISS 索引（职位 + 简历）
├── talentflow-ai-frontend/        # Vue 3 前端
│   ├── src/views/hr/              # HR 岗位、简历推荐
│   ├── src/views/user/dashboard/  # 求职者简历、职位驾驶舱、个人资料
│   └── src/components/            # LocationPicker、RecommendMatchCard 等
├── scripts/                       # 构建、部署、DB 初始化、本地启动
├── docs/                          # 架构图、流程图、部署与 CI 文档
├── docker-compose*.yml
└── .github/workflows/             # CI 与 Docker Hub 发布
```

## 常用命令

```bash
# Docker
docker compose ps
docker compose logs -f backend celery-worker
docker compose down

# 数据库检查
./scripts/check-db.sh

# 简历向量重建
cd talentflow-ai-backend-bak && python scripts/reindex_resumes.py

# 生产部署（Hub 拉镜像）
./scripts/deploy-remote.sh
```

## 测试与评测

```bash
# 冒烟测试（需本地全套服务）
cd talentflow-ai-backend-bak
python scripts/smoke_test.py

# HR 简历推荐验收
bash scripts/acceptance/resume_recommend/run_all.sh

# RAG 评测（LangSmith）
python scripts/eval/cli.py --help
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
| [docs/recommend-flow.md](docs/recommend-flow.md) | 求职者职位推荐流程 |
| [docs/recommend-state.md](docs/recommend-state.md) | 推荐状态与会话模型 |
| [docs/smart-apply-flow.md](docs/smart-apply-flow.md) | 智能投递流程 |
| [docs/CI_CD.md](docs/CI_CD.md) | CI/CD 流程 |
| [docs/DEPLOY_SSH.md](docs/DEPLOY_SSH.md) | SSH 自动部署 |

## 常见问题

**推荐卡片显示「未填写所在地」但有城市名？**  
多为前端 session 缓存了距离功能上线前的旧数据。强刷页面（Ctrl+Shift+R）或点击推荐页刷新按钮；仍无效时清除浏览器 `sessionStorage` 中以 `resume_recommend_` 开头的键。

**距离不显示但城市正常？**  
检查 `AMAP_WEB_KEY` 是否写入 `talentflow-ai-backend-bak/.env` 并已重启后端；对历史数据运行 `backfill_geocode.py`。

**HR 精排一直排队？**  
确认 Celery Worker 已启动；Windows 本地需 `--pool=solo`。

## License

本项目仅供学习与研究使用。
=======
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
>>>>>>> a55bae2bf996956bd82426f4a115e47dffc836f7
