# Docker 安装与镜像发布

## 一、Windows 安装 Docker Desktop

### 方式 A：winget（推荐）

以**管理员**打开 PowerShell：

```powershell
winget install -e --id Docker.DockerDesktop
```

安装完成后：

1. **重启电脑**
2. 启动 **Docker Desktop**，等待左下角显示 *Engine running*
3. 验证：

```powershell
docker --version
docker compose version
docker run hello-world
```

### 方式 B：官网安装包

1. 打开 https://docs.docker.com/desktop/setup/install/windows-install/
2. 下载 Docker Desktop Installer
3. 安装时勾选 **Use WSL 2 instead of Hyper-V**（推荐）
4. 若提示启用 WSL2，在管理员 PowerShell 执行：

```powershell
wsl --install
```

重启后再启动 Docker Desktop。

### 常见问题

| 问题 | 处理 |
|------|------|
| `docker` 不是内部命令 | 重启终端；确认 Docker Desktop 已启动 |
| WSL2 未安装 | `wsl --install` 后重启 |
| 虚拟化未开启 | BIOS 开启 Intel VT-x / AMD-V |
| 内存不足 | Docker Desktop → Settings → Resources → Memory ≥ 8GB |
| `auth.docker.io` 连接超时 / `dockerproxy` 500 | 见下方「国内镜像拉取失败」 |

### 国内镜像拉取失败

报错示例：

```text
failed to fetch oauth token: Post "https://auth.docker.io/token": dial tcp ... connectex
unexpected status from HEAD request to https://dockerproxy.net/... 500
```

**原因：** 国内网络无法稳定访问 Docker Hub，与项目业务代码无关。

**本项目已默认改用 DaoCloud 镜像**（见各 `Dockerfile` 与 `docker-compose.yml` 中的 `docker.m.daocloud.io/library/...`），重新构建即可：

```powershell
docker compose -f docker-compose.yml -f docker-compose.registry.yml --env-file .env.registry build backend frontend
```

若 DaoCloud 也不可用，在 `.env` 中改为你自己的镜像源（阿里云个人加速地址等），或删除 Docker Desktop → Settings → Docker Engine 里失效的 `registry-mirrors` 后重启。

海外环境可改回官方镜像，例如在 `.env` 中：

```env
DOCKER_PYTHON_BASE=python:3.11-slim-bookworm
DOCKER_NODE_BASE=node:18-alpine
DOCKER_NGINX_BASE=nginx:stable-alpine
DOCKER_MYSQL_IMAGE=mysql:8.0
DOCKER_REDIS_IMAGE=redis:7-alpine
```

---

## 二、本项目要推送哪些镜像

| 镜像 | 包含服务 | 说明 |
|------|----------|------|
| `talentflow-backend` | backend、mcp-server、celery-worker | **同一镜像**，启动命令不同 |
| `talentflow-frontend` | frontend | Nginx + Vue 静态页 |
| — | mysql、redis | 使用官方镜像，**无需推送** |

---

## 三、构建并推送到 Docker Hub

### 1. 注册 Docker Hub

https://hub.docker.com 注册账号，记住用户名。

### 2. 配置仓库信息

```powershell
cd C:\Users\kzd\Desktop\talentflow-ai
Copy-Item .env.registry.example .env.registry
notepad .env.registry
```

```env
DOCKER_REGISTRY=docker.io
DOCKER_NAMESPACE=你的DockerHub用户名
IMAGE_TAG=latest
```

### 3. 构建 + 推送

**若 PowerShell 报「禁止运行脚本」**，用下面任一方式：

```powershell
# 方式 A：双击或命令行运行 bat（推荐，无需改系统策略）
.\scripts\build-and-push.bat -Login

# 方式 B：单次绕过执行策略
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-and-push.ps1 -Login

# 方式 C：永久允许当前用户运行本地脚本（可选）
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\scripts\build-and-push.ps1 -Login
```

```powershell
# 登录（你已完成可跳过）
docker login

# 构建并推送（首次 build 可能 20～40 分钟）
.\scripts\build-and-push.bat -Login
```

仅构建不推送：

```powershell
.\scripts\build-and-push.ps1 -BuildOnly
```

### 4. 推送结果

仓库中会出现：

- `你的用户名/talentflow-backend:latest`
- `你的用户名/talentflow-frontend:latest`

---

## 四、阿里云 / 腾讯云容器镜像服务

```env
# 阿里云示例
DOCKER_REGISTRY=registry.cn-hangzhou.aliyuncs.com
DOCKER_NAMESPACE=你的命名空间
IMAGE_TAG=v1.0.0
```

```powershell
docker login registry.cn-hangzhou.aliyuncs.com
.\scripts\build-and-push.ps1
```

---

## 五、服务器从仓库拉取部署（无需 build）

服务器上只需 `.env`、compose 文件，**不要**上传整个源码（可选）。

```bash
cd /opt/talentflow-ai
cp .env.registry.example .env.registry
nano .env.registry   # 与构建时相同的 DOCKER_NAMESPACE / IMAGE_TAG

docker login
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.pull.yml --env-file .env.registry pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.pull.yml --env-file .env.registry --env-file .env up -d
```

仍需在服务器准备根目录 `.env`（MySQL 密码、API Key 等）。

---

## 六、文件说明

| 文件 | 作用 |
|------|------|
| `docker-compose.registry.yml` | 构建时打上仓库 tag |
| `docker-compose.pull.yml` | 服务器只 pull 不 build |
| `.env.registry.example` | 仓库命名空间配置 |
| `scripts/build-and-push.ps1` | Windows 构建推送脚本 |
| `scripts/build-and-push.sh` | Linux/macOS 脚本 |

---

## 七、注意

1. **backend 镜像很大**（含 BGE 模型 + torch），推送/upload 较慢
2. **不要**把 `.env`、`.env.registry` 提交 git（含密码）
3. 向量库 `vector_store`、MySQL 数据在 **volume** 里，不在镜像中；新环境需导入或重新建索引
