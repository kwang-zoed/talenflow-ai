# CI/CD 详细流程说明（无服务器阶段）

目标：**每次改代码先自动验证能构建 → 通过后把前后端镜像推到 Docker Hub → 删掉本地/Runner 上的旧镜像**。  
暂不部署远程服务器；以后有机器再在 Publish 后加 SSH 即可。

---

## 一、整体地图（先建立印象）

```text
你改代码 → git push
              │
              ├─ 推到 main 以外的分支 / 开 PR
              │     └─ 自动跑【CI】只测不推（约 10～40 分钟，视缓存与模型大小）
              │
              └─ 合并到 main（或直接 push main）
                    ├─ 自动跑【CI】（同上）
                    └─ 自动跑【Publish Docker Hub】构建 + 推送 + 删 Runner 旧镜像

你本机也可以不走 GitHub，手动：
  build-and-push.ps1 → 构建 → push Hub → -PruneLocal 删本机旧镜像
```

| 工作流文件 | 触发时机 | 会不会推 Hub | 删镜像位置 |
|------------|----------|--------------|------------|
| `.github/workflows/ci.yml` | PR、push 到 main/master | 否 | 仅删本次 CI 临时 tag |
| `.github/workflows/publish-dockerhub.yml` | push main、手动 Run workflow | 是 | GitHub Runner 上旧 tag |
| `scripts/build-and-push.ps1` | 你本地手动执行 | 是（需 -Login） | 加 `-PruneLocal` 删本机 |

---

## 二、阶段 0：一次性准备（只做一次）

### 步骤 0-1：确认本机工具

| 工具 | 用途 | 如何确认 |
|------|------|----------|
| Git | 提交、推送 | `git --version` |
| Docker Desktop | 本地构建/拉镜像 | `docker info` 无报错 |
| GitHub 仓库 | 托管代码、跑 Actions | 代码已 push 到 GitHub |

**出问题可问：**「步骤 0-1：docker info 报错 …」

---

### 步骤 0-2：Docker Hub 与 Token

1. 登录 [Docker Hub](https://hub.docker.com/)。
2. **Account Settings → Security → New Access Token**（权限 Read & Write）。
3. 复制 Token（只显示一次，务必保存）。

**最终镜像地址格式：**

```text
docker.io/<你的用户名>/talentflow-backend:latest
docker.io/<你的用户名>/talentflow-frontend:latest
```

**出问题可问：**「步骤 0-2：Token 权限不够 / 登录失败 …」

---

### 步骤 0-3：GitHub Secrets（Publish 必配）

路径：仓库 **Settings → Secrets and variables → Actions → New repository secret**

| Secret 名称 | 填什么 |
|-------------|--------|
| `DOCKERHUB_USERNAME` | **`kwangzoed`** |
| `DOCKERHUB_TOKEN` | Docker Hub → Security → Personal access token（见 `docs/DOCKERHUB_SECRETS.md`） |

> 用 GitHub 登录 Docker Hub **不能**代替 Token；须在 Hub 单独生成 Token 填到 Secrets。

可选 **Variables**（非必须）：

| Variable | 填什么 |
|----------|--------|
| `DOCKER_NAMESPACE` | 与用户名相同；不配则用 Secret 里的用户名 |

**如何确认成功：** 之后 Publish 日志里 `docker login` 一步为绿色，不会出现 `unauthorized`。

**出问题可问：**「步骤 0-3：Publish 里 login failed …」

---

### 步骤 0-4：本地镜像仓库配置（仅本地脚本用）

```powershell
cd C:\Users\kzd\Desktop\talentflow-ai
Copy-Item .env.registry.example .env.registry
notepad .env.registry
```

`.env.registry` 至少改：

```env
DOCKER_REGISTRY=docker.io
DOCKER_NAMESPACE=你的DockerHub用户名
IMAGE_TAG=latest
```

**说明：** GitHub Actions **不读** `.env.registry`，只读 Secrets；本机 `build-and-push.ps1` 才读 `.env.registry`。

**出问题可问：**「步骤 0-4：DOCKER_NAMESPACE 未设置 …」

---

### 步骤 0-5：确认仓库目录完整

| 路径 | CI/Publish 是否需要 |
|------|---------------------|
| `talentflow-ai-backend-bak/` + `Dockerfile` | **必须** |
| `talentflow-ai-backend-bak/app/bge-*` 模型目录 | **必须**（Dockerfile 会 COPY，没有则构建失败） |
| `talentflow-ai-frontend/` + `Dockerfile` | 可选；没有则跳过前端，只推 backend |
| `docker-compose.yml` | CI 会 `compose config` 校验 |

**出问题可问：**「步骤 0-5：CI 构建 backend 报 COPY 找不到模型 …」

---

## 三、阶段 A：日常改代码 → 触发 CI（自动测试）

**何时触发：** 向 `main` 或 `master` 分支 **push**，或向这两支 **开 Pull Request**。

**在哪看结果：** GitHub 仓库 → **Actions** → 选 **CI** 工作流 → 点最新一次 run。

CI 分 **2 个 Job**，必须都绿才算通过。

---

### Job A1：`后端静态检查`（backend-check）

按顺序执行：

| 子步骤 | 做什么 | 成功标志 |
|--------|--------|----------|
| A1-1 checkout | 拉取你提交的代码 | 绿色 |
| A1-2 setup-python | 安装 Python 3.11 | 绿色 |
| A1-3 安装依赖 | 只装检查 import 需要的轻量包（**不是**完整 `requirements.txt`） | 绿色 |
| A1-4 check_imports | 运行 `talentflow-ai-backend-bak/check_imports.py` | 日志末尾 `ALL CHECK PASSED` |
| A1-5 compose config | 在项目根执行 `docker compose config` | 无语法错误 |

**这一步在验证什么：** Python 模块能导入、`docker-compose.yml` 没有写错。  
**不验证：** 数据库、Redis、智能投递、LLM 调用。

**常见失败 → 你可这样问：**

- 「A1-4 check_imports 失败，报错 xxx」
- 「A1-5 compose config 报错 xxx」

---

### Job A2：`Docker 构建验证`（docker-build-verify）

**依赖：** Job A1 成功后才会开始。

| 子步骤 | 做什么 | 成功标志 |
|--------|--------|----------|
| A2-1 checkout | 再次拉代码 | 绿色 |
| A2-2 setup-buildx | 启用 Docker 构建器 | 绿色 |
| A2-3 构建 backend | `docker build` backend Dockerfile，`push: false` | 绿色，日志 `exporting to image` 成功 |
| A2-4 检查 frontend | 看是否存在 `talentflow-ai-frontend/Dockerfile` | 有则继续 A2-5；无则 **notice 跳过**（不算失败） |
| A2-5 构建 frontend | 仅目录存在时构建前端 | 绿色或跳过 |
| A2-6 清理 CI 临时镜像 | 删除 `talentflow-*:ci-<sha>`，避免占满 Runner 磁盘 | 总是执行 |

**这一步在验证什么：** Dockerfile 能完整构建出镜像（含 pip 安装、COPY 模型等）。  
**不会：** 推送到 Docker Hub；不会启动容器跑业务。

**耗时：** 首次可能 20～40 分钟；有 GHA 缓存后通常会短很多。

**常见失败 → 你可这样问：**

- 「A2-3 backend 构建失败，pip / COPY / 磁盘 …」
- 「A2-5 frontend 构建失败 …」

---

### 阶段 A 结束后你应该看到什么

- Actions 里 **CI** 全部为绿色 ✓  
- Docker Hub 上**还没有**新镜像（CI 不 push）  
- 可以合并 PR 或继续 push main 触发 Publish  

**并发说明：** 同一分支短时间内多次 push，旧的 CI 会被 **cancel-in-progress** 取消，只保留最新一次，属正常。

---

## 四、阶段 B：合并到 main → 自动 Publish（推 Hub + 删 Runner 旧镜像）

**何时触发：**

1. **push 到 `main` / `master`**（包括合并 PR 后），或  
2. **Actions → Publish Docker Hub → Run workflow**（手动，可填 `image_tag`，默认 `latest`）

**在哪看：** Actions → **Publish Docker Hub**。

分 **2 个 Job**：`发布前检查` → `构建并推送镜像`。

---

### Job B1：`发布前检查`（gate）

| 子步骤 | 做什么 | 成功标志 |
|--------|--------|----------|
| B1-1 checkout | 拉 main 上最新代码 | 绿色 |
| B1-2 check_imports | 与 CI 类似，快速 import 检查 | `ALL CHECK PASSED` |

**作用：** 即使没走 PR、直接 push main，也有一层最基本校验。

**出问题可问：**「B1-2 gate 失败 …」

---

### Job B2：`构建并推送镜像`（publish）

| 子步骤 | 做什么 | 成功标志 |
|--------|--------|----------|
| B2-1 checkout | 拉代码 | 绿色 |
| B2-2 docker login | 用 `DOCKERHUB_USERNAME` + `DOCKERHUB_TOKEN` 登录 | `Login Succeeded` |
| B2-3 setup-buildx | 构建器就绪 | 绿色 |
| B2-4 计算镜像名 | 生成推送地址 | 日志里有 `docker.io/用户名/talentflow-backend` |
| B2-5 推送 backend | 构建并 **push** 两个 tag | 见下表 |
| B2-6 检查 frontend | 同 CI | 无目录则跳过 B2-7 |
| B2-7 推送 frontend | 有目录则 push 两个 tag | 绿色或跳过 |
| B2-8 删除 Runner 旧镜像 | 运行 `prune-talentflow-images.sh` | 日志 `rm` / `keep` |
| B2-9 发布摘要 | 写入 Actions Summary | 页面底部可见镜像列表 |

**Backend 推送后的两个标签（每次 main 发布）：**

| 标签 | 含义 | 示例 |
|------|------|------|
| `latest`（或你手动填的 tag） | 日常 `docker pull` 用 | `.../talentflow-backend:latest` |
| `<完整 git commit sha>` | 可回滚到某次提交 | `.../talentflow-backend:a1b2c3d4...` |

Frontend 同理（若构建了前端）。

**B2-8 删镜像规则（在 GitHub Runner 上，不是你电脑）：**

- **保留：** `latest`（或手动指定的 tag）+ **当前这次 commit 的 sha**  
- **删除：** 同仓库名下其它 tag 的本地镜像  
- 最后 `docker image prune -f` 清悬空层  

**注意：** Hub 上历史 tag **不会**被此脚本删除，只删 Runner 磁盘上的本地副本。要删 Hub 上旧 tag 需在 Docker Hub 网页手动删。

**常见失败 → 你可这样问：**

- 「B2-2 login unauthorized」（Secrets 没配对）  
- 「B2-5 push denied / quota」（Hub 权限或限流）  
- 「B2-5 构建 OOM / 超时」  
- 「B2-8 prune 报错」（一般可忽略，把完整日志发来）  

---

### 阶段 B 成功后如何确认 Hub 已有新镜像

1. 打开 `https://hub.docker.com/r/<用户名>/talentflow-backend/tags`  
2. 应看到 `latest` 和一条长 sha tag，时间为刚才。  
3. 本机试拉：`docker pull docker.io/<用户名>/talentflow-backend:latest`

---

## 五、阶段 C：本机手动构建 + 推送 + 删旧镜像（不经过 GitHub）

适合：想在本机先验证构建、或 Actions 还没配好、或 Hub 限流时本地推。

### 步骤 C-1：仅构建、不推送（调试用）

```powershell
cd C:\Users\kzd\Desktop\talentflow-ai
.\scripts\build-and-push.ps1 -BuildOnly
```

| 顺序 | 脚本内部做什么 |
|------|----------------|
| C1-1 | 检查 `docker` 可用 |
| C1-2 | 读取 `.env.registry` |
| C1-3 | `docker compose ... build backend frontend` |
| C1-4 | 列出本机 `talentflow` 相关镜像，**结束**（不 login、不 push） |

**成功：** 终端显示 `Build done`，`docker images` 能看到 `.../talentflow-backend:latest`。

**出问题可问：**「C1-3 compose build 失败 …」

---

### 步骤 C-2：构建 + 登录 + 推送 Hub

```powershell
.\scripts\build-and-push.ps1 -Login
```

在 C1 基础上增加：

| 顺序 | 做什么 |
|------|--------|
| C2-1 | `docker login`（交互输入 Hub 账号密码，或已登录过） |
| C2-2 | `docker push` backend 镜像 |
| C2-3 | `docker push` frontend 镜像（若构建了） |

**成功：** 终端 `Push succeeded`，并打印 `docker pull ...` 地址。

**出问题可问：**「C2-2 push unauthorized …」

---

### 步骤 C-3：推送后删除本机旧镜像（你关心的「本地存镜像」）

```powershell
.\scripts\build-and-push.ps1 -Login -PruneLocal
```

在 C2 成功后增加：

| 顺序 | 做什么 |
|------|--------|
| C3-1 | 调用 `prune-talentflow-images.ps1` |
| C3-2 | 扫描 `docker.io/<命名空间>/talentflow-backend` 与 `talentflow-frontend` |
| C3-3 | **保留** `.env.registry` 里 `IMAGE_TAG`（默认 `latest`） |
| C3-4 | **删除** 同仓库其它 tag（如旧的 sha、旧的 `v0.1` 等） |
| C3-5 | `docker image prune -f` 清未使用层 |

**只删镜像、不构建不推送：**

```powershell
.\scripts\prune-talentflow-images.ps1 -Namespace 你的用户名 -KeepTags latest
# 预览：加 -DryRun
```

**成功：** `docker images` 里 talentflow 只剩你要留的 tag，磁盘占用下降。

**注意：**

- 正在运行的容器用的镜像 **可能仍被占用**，删 tag 会失败，需先 `docker compose down`。  
- **不会**删除 Hub 远程 tag，只删本机。  

**出问题可问：**「C3-4 某镜像删不掉 image is in use …」

---

## 六、阶段 D：本机用 Hub 上的镜像跑起来（验证「能跑通」）

仍无远程服务器时，可在本机用 **pull 模式** 验证镜像是否可用：

```powershell
cd C:\Users\kzd\Desktop\talentflow-ai
# 确保根目录 .env 已配置 MySQL/Redis/API Key 等
docker compose -f docker-compose.yml -f docker-compose.pull.yml pull
docker compose -f docker-compose.yml -f docker-compose.pull.yml up -d
```

| 步骤 | 做什么 |
|------|--------|
| D-1 pull | 从 Hub 拉 `latest`（不在本机构建） |
| D-2 up | 启动 mysql、redis、backend、celery、mcp、frontend |
| D-3 访问 | 浏览器 `http://localhost:8080`（前端）、API `8000` |

**CI/Publish 不会自动做 D**；这是你自己验证部署物是否正常。

**出问题可问：**「D-2 某容器一直 restarting …」

---

## 七、两条路径对照（避免搞混）

| 问题 | GitHub CI | GitHub Publish | 本机 build-and-push |
|------|-----------|----------------|---------------------|
| 会推 Hub 吗 | 否 | 是 | 加 -Login 才是 |
| 删哪的旧镜像 | 仅 CI 临时 tag | Runner 上旧 tag | 本机（-PruneLocal） |
| 要配 Secrets 吗 | 否 | 是 | 否（本地 login） |
| 典型耗时 | 中～长 | 长 | 最长（本机 CPU） |

**推荐习惯：**

1. 功能分支开发 → push → 等 **CI 绿**  
2. 合并 **main** → 等 **Publish 绿** → 到 Hub 看 tag  
3. 本机磁盘紧 → `pull` 前或 push 后用 **PruneLocal**  

---

## 八、故意不放进流水线的事（避免误解）

| 内容 | 原因 |
|------|------|
| 智能投递全链路 / LangGraph | 慢、要 API Key、要 Celery+MCP+MySQL |
| LangSmith 上报 | 属运行时配置，在 `.env` 配即可 |
| 远程 SSH 部署 | 你暂未租服务器 |
| 删除 Hub 上历史 tag | 需 Hub 网页或 API 另行管理 |

以后若要加「部署后 smoke_test」，可在 Publish 末尾加 Job，再单独写一节。

---

## 九、你提问时怎么描述最高效

请尽量带 **阶段 + 步骤编号**，例如：

- 「A2-3 backend 构建失败，日志最后几行是 …」  
- 「B2-2 docker login 401」  
- 「C3-4 prune 删不掉 …」  

并附上：**GitHub Actions 链接** 或 **完整报错片段**（可打码 Token）。

---

## 十、相关文件索引

| 文件 | 作用 |
|------|------|
| `.github/workflows/ci.yml` | 阶段 A |
| `.github/workflows/publish-dockerhub.yml` | 阶段 B |
| `scripts/build-and-push.ps1` | 阶段 C |
| `scripts/prune-talentflow-images.ps1` | 本机删旧镜像 |
| `scripts/prune-talentflow-images.sh` | Publish 里 Runner 删旧镜像 |
| `docker-compose.registry.yml` | 本地 compose build 时指定镜像名 |
| `docker-compose.pull.yml` | 阶段 D 从 Hub 拉镜像 |
| `docs/DEPLOY.md` | 完整 Docker 运行说明 |
