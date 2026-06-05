# 云服务器部署（Docker Hub 拉镜像）

适用于已 push 到 Hub 的 `kwangzoed/talentflow-backend` / `talentflow-frontend`。

## 1. 准备

```bash
cd /opt/talentflow-ai   # 或 ~/workspace
cp .env.production.example .env && nano .env
cp .env.registry.example .env.registry && nano .env.registry
```

`.env.registry` 示例：

```env
DOCKER_REGISTRY=docker.io
DOCKER_NAMESPACE=kwangzoed
IMAGE_TAG=latest
```

## 2. 一键部署

```bash
chmod +x scripts/deploy-server.sh scripts/init-db.sh
./scripts/deploy-server.sh
```

等价命令：

```bash
docker compose -f docker-compose.server.yml \
  --env-file .env --env-file .env.registry \
  pull && up -d
```

`docker-compose.server.yml` 已合并：`pull` + `prod`（仅 80）+ `hub-entrypoint-fix`。

## 3. 首次：导入数据库 + 账号

```bash
# 将 dandelion_tribe_schema.sql 放到项目根目录
./scripts/init-db.sh dandelion_tribe_schema.sql
```

或分步：

```bash
docker exec -i talentflow-mysql mysql -uroot -p<密码> dandelion_tribe < dandelion_tribe_schema.sql
docker exec talentflow-api python scripts/seed_demo_users.py
```

默认账号：

| 用户 | 密码 | 角色 |
|------|------|------|
| admin | admin12345 | 管理员 |
| hr | hr12345678 | HR |

## 4. 访问

- 前端：`http://<公网IP>/`
- 管理：`http://<公网IP>/admin`
- **云安全组**入站放行 **TCP 80**

## 5. 更新版本

```bash
git pull
./scripts/deploy-server.sh
```

合并到 **main** 且配置 SSH 后，**Publish 工作流会自动部署**，见 **`docs/DEPLOY_SSH.md`**。

## 6. 故障排查

| 现象 | 处理 |
|------|------|
| `exec /docker-entrypoint.sh: no such file` | 确认使用 `docker-compose.server.yml`（含 entrypoint 修复） |
| 职位解析 `No module named pdfplumber` | 拉最新 backend 镜像或容器内 `pip install pdfplumber python-docx` |
| 登录 401 / 127.0.0.1 | 拉最新 frontend 镜像（已改 `/api` 路径） |
| 外网超时 | 阿里云/腾讯云安全组放行 80，非 ufw 问题时可忽略 |

## 7. 本地 LAN（Windows）

见 `scripts/open-lan-firewall.ps1`（开发默认 **8080**，生产服务器用 **80**）。
