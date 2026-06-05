# SSH 自动部署（GitHub Actions → 生产服务器）

Publish 工作流在 **推送 Docker Hub 成功后**，通过 SSH 在服务器执行 `./scripts/deploy-server.sh`。

默认目标：

| 项 | 默认值 |
|----|--------|
| 地址 | http://8.218.11.250/ |
| 用户 | `root` |
| 目录 | `/root/workspace` |
| 密钥 | 存 GitHub Secret，**勿提交** `.pem` 到 Git |

---

## 1. 把私钥放进 GitHub Secrets（一次性）

本地私钥路径（仅本机使用）：

```text
.cursor/rules/talentflow-ai.pem
```

**不要** `git add` 该文件（已在 `.gitignore` 忽略 `*.pem`）。

在 GitHub 仓库：**Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|------|--------|
| `SSH_PRIVATE_KEY` | 打开 `.pem`，**完整复制**（含 `-----BEGIN ... KEY-----` 与 `-----END ... KEY-----`） |

---

## 2. 配置 Variables（可选，不配则用默认）

**Settings → Secrets and variables → Actions → Variables**

| Name | 建议值 | 说明 |
|------|--------|------|
| `ENABLE_SSH_DEPLOY` | `true` | 设为 `true` 才执行 deploy job |
| `SSH_HOST` | `8.218.11.250` | 可省略，workflow 有默认 |
| `SSH_USER` | `root` | 可省略 |
| `SSH_DEPLOY_PATH` | `/root/workspace` | 可省略 |
| `SSH_PORT` | `22` | 可省略 |
| `DEPLOY_URL` | `http://8.218.11.250/` | 部署后 HTTP 探活 |

---

## 3. 服务器一次性准备

SSH 登录服务器：

```bash
cd /root/workspace
cp .env.production.example .env && nano .env
cp .env.registry.example .env.registry && nano .env.registry
# .env.registry 中 DOCKER_NAMESPACE=kwangzoed
chmod +x scripts/deploy-server.sh
```

确保：

- 已安装 Docker + Compose
- 安全组放行 **80**
- 首次若空库： `./scripts/init-db.sh dandelion_tribe_schema.sql`

---

## 4. 自动部署何时触发

```text
push main → CI 成功 → Publish 推 Hub → deploy job SSH 部署
```

手动：**Actions → Publish Docker Hub → Run workflow**

- 勾选逻辑：`skip_deploy` 为 true 时跳过 SSH（仅手动触发有效）

---

## 5. deploy job 在远程执行的命令

等价于：

```bash
cd /root/workspace
git pull --ff-only    # 更新 compose 脚本
./scripts/deploy-server.sh   # pull 镜像 + up -d
```

然后从 GitHub Runner 请求 `DEPLOY_URL` 做简单 HTTP 探活。

---

## 6. 故障排查

| 现象 | 处理 |
|------|------|
| `Permission denied (publickey)` | 检查 `SSH_PRIVATE_KEY` 是否与服务器 `authorized_keys` 对应 |
| `缺少 .env` | 在服务器 `/root/workspace` 创建 `.env` |
| deploy 被跳过 | 确认 Variable `ENABLE_SSH_DEPLOY=true` |
| 页面仍旧版 | Hub 镜像是否 push 成功；服务器 `docker compose pull` 日志 |

---

## 7. 安全提醒

- **切勿** 将 `talentflow-ai.pem` 提交到仓库
- 若密钥曾泄露，在阿里云 **轮换密钥** 并更新 GitHub Secret
- 生产 `.env` 仅保存在服务器，不要写入 workflow
