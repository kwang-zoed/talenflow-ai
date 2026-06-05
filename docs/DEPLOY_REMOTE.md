# 远程服务器部署指南

适用于 Linux 云服务器（阿里云 / 腾讯云 / AWS 等），使用 Docker Compose 一键部署全栈。

---

## 一、服务器要求

| 项目 | 建议 |
|------|------|
| 系统 | Ubuntu 22.04 / Debian 12 |
| CPU | ≥ 2 核 |
| 内存 | **≥ 8GB**（embedding + reranker 模型占内存） |
| 磁盘 | ≥ 30GB（含模型与 Docker 镜像） |
| 开放端口 | **80**（HTTP），可选 **443**（HTTPS） |

---

## 二、服务器初始化（首次一次）

SSH 登录服务器后执行：

```bash
# 1. 更新系统
sudo apt update && sudo apt upgrade -y

# 2. 安装 Docker（官方脚本）
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# 重新登录 SSH 使 docker 组生效

# 3. 安装 Compose 插件（若 get.docker.com 未带）
sudo apt install -y docker-compose-plugin

# 4. 验证
docker --version
docker compose version

# 5. 防火墙（仅开放 Web）
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp   # 若用 HTTPS
sudo ufw enable
```

---

## 三、上传代码到服务器

### 方式 A：Git（推荐）

```bash
cd /opt
sudo git clone <你的仓库地址> talentflow-ai
sudo chown -R $USER:$USER talentflow-ai
cd talentflow-ai
```

### 方式 B：从本机 rsync（Windows 可用 WSL 或 Git Bash）

在本机执行（替换 `user@your-server-ip`）：

```bash
rsync -avz --progress \
  --exclude node_modules \
  --exclude .git \
  --exclude __pycache__ \
  --exclude "*.sqlite*" \
  --exclude .env \
  ./  user@your-server-ip:/opt/talentflow-ai/
```

> **重要**：必须包含 BGE 模型目录，否则推荐/向量功能不可用：
> - `talentflow-ai-backend-bak/app/bge-small-zh-v1.5-embedding/`
> - `talentflow-ai-backend-bak/app/bge-reranker-v2-m3/`

模型体积大，首次上传可能较慢；也可在服务器上 `git lfs pull` 或单独 scp。

---

## 四、配置生产环境变量

在服务器项目根目录：

```bash
cd /opt/talentflow-ai
cp .env.production.example .env
nano .env
```

**必须修改**（四处密码 + 密钥保持一致）：

```env
MYSQL_ROOT_PASSWORD=强密码A
MYSQL_PASSWORD=强密码B
REDIS_PASSWORD=强密码C

REDIS_URL=redis://:强密码C@redis:6379/0
CELERY_BROKER_URL=redis://:强密码C@redis:6379/0
CELERY_RESULT_BACKEND=redis://:强密码C@redis:6379/1

SECRET_KEY=随机32位以上字符串
OPENAI_API_KEY=sk-xxx
```

`.env` **不要提交 git**，只在服务器上存在。

---

## 五、启动（生产模式）

### 方式 A：从 Docker Hub 拉镜像（推荐）

```bash
cd /opt/talentflow-ai
cp .env.registry.example .env.registry   # DOCKER_NAMESPACE=kwangzoed
chmod +x scripts/deploy-server.sh
./scripts/deploy-server.sh
```

详见 **`docs/DEPLOY_SERVER.md`**（含 seed、安全组、故障排查）。

### 方式 B：在服务器本地 build（需模型目录，耗时长）

```bash
DEPLOY_MODE=build ./scripts/deploy-remote.sh
```

或：

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## 六、导入已有数据（可选）

### MySQL

在本机导出：

```bash
mysqldump -u root -p dandelion_tribe > backup.sql
scp backup.sql user@server:/opt/talentflow-ai/
```

在服务器导入：

```bash
docker exec -i talentflow-mysql mysql -uroot -p"你的ROOT密码" dandelion_tribe < backup.sql
```

### 向量库 FAISS

```bash
# 本机
scp -r talentflow-ai-backend-bak/vector_store/* user@server:/tmp/vector_store/

# 服务器
docker cp /tmp/vector_store/. talentflow-api:/app/vector_store/
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart backend celery-worker
```

---

## 七、访问与验证

```bash
# 服务器上自检
curl -I http://127.0.0.1/
curl http://127.0.0.1:8000/   # prod 模式下 8000 未映射公网，需在容器内测：
docker exec talentflow-api curl -s http://127.0.0.1:8000/
```

浏览器访问：

```
http://你的服务器公网IP/
```

API 文档（生产建议关公网或加鉴权）：经 Nginx 反代后访问 `/api/docs` 可能不可用（前端 nginx 只代理 `/api` 到 backend，可试 `http://IP/api/v1/...`）。

---

## 八、绑定域名 + HTTPS（推荐）

在服务器安装 Caddy，自动申请 Let's Encrypt 证书：

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy

sudo nano /etc/caddy/Caddyfile
```

```caddy
your-domain.com {
    reverse_proxy localhost:80
}
```

```bash
sudo systemctl reload caddy
```

同时将 `docker-compose.prod.yml` 中 frontend 改为 `"127.0.0.1:8080:80"`，避免与 Caddy 抢 80 端口——或 Caddy 反代到 `8080` 而把 compose frontend 保持 `8080:80`。

简单做法：**frontend 用 8080**，Caddy 占 80/443 反代到 8080：

```yaml
# docker-compose.prod.yml 中
frontend:
  ports:
    - "127.0.0.1:8080:80"
```

```caddy
your-domain.com {
    reverse_proxy 127.0.0.1:8080
}
```

---

## 九、日常运维

```bash
cd /opt/talentflow-ai

# 状态
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# 日志
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f celery-worker

# 更新代码后重新部署
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 重启 Celery（智能投递 NotRegistered）
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart celery-worker

# 备份 MySQL
docker exec talentflow-mysql mysqldump -uroot -p"ROOT密码" dandelion_tribe > backup_$(date +%F).sql
```

### 备份 volume

```bash
docker run --rm -v talentflow-ai_mysql_data:/data -v $(pwd):/backup alpine \
  tar czf /backup/mysql_data_$(date +%F).tar.gz -C /data .
```

---

## 十、架构（生产）

```
公网
  │
  ├─ :80/443  Caddy（可选 HTTPS）
  │      └─→ frontend (Nginx) ── /api → backend
  │
  └─ 不暴露公网：
         mysql / redis / mcp-server / backend:8000

celery-worker ←→ redis ←→ backend
                    └─ vector_store / data / uploads (Docker volumes)
```

---

## 十一、常见问题

| 现象 | 处理 |
|------|------|
| 外网无法访问 | 检查云厂商**安全组**是否放行 80/443 |
| build OOM | 服务器内存 < 8GB，加 swap 或升配 |
| 推荐无结果 | 向量库为空，导入 vector_store 或发布职位 |
| 智能投递失败 | `docker compose logs celery-worker`，重启 worker |
| 502 Bad Gateway | backend 未就绪，`docker compose ps` 看 health |

---

## 十二、与本机开发区别

| 配置 | 本机 Docker | 远程生产 |
|------|-------------|----------|
| compose 文件 | `docker-compose.yml` | `+ docker-compose.prod.yml` |
| 对外端口 | 8080 / 8000 / 3306... | **仅 80**（或 Caddy 443） |
| `.env` 位置 | 项目根目录 | 服务器项目根目录（独立配置） |
| 密码 | 可 dev 弱密码 | **必须强密码** |

本地开发文档见 [DEPLOY.md](./DEPLOY.md)。
