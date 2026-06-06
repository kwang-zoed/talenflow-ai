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

| Name | Value | 存放位置 |
|------|--------|----------|
| `SSH_PRIVATE_KEY` | 打开 `.pem`，**完整复制** | **Secret**（必须） |
| `ENABLE_SSH_DEPLOY` | `true` 或留空=开启；`false`=关闭 | Secret 或 Variable 均可 |
| `SSH_HOST` / `SSH_USER` / `SSH_DEPLOY_PATH` / `DEPLOY_URL` | 见下表默认值 | Secret 或 Variable 均可（不配则用默认） |

---

## 2. 配置 SSH 相关项（可选，不配则用默认）

**Settings → Secrets and variables → Actions**

可放在 **Secrets** 或 **Variables**（workflow 两种都读）。仅 `SSH_PRIVATE_KEY` 必须是 Secret。

| Name | 建议值 | 说明 |
|------|--------|------|
| `ENABLE_SSH_DEPLOY` | 留空或 `true` | **默认开启** SSH；设为 `false` 才关闭 |
| `SSH_HOST` | `8.218.11.250` | 可省略 |
| `SSH_USER` | `root` | 可省略 |
| `SSH_DEPLOY_PATH` | `/root/workspace` | 可省略 |
| `SSH_PORT` | `22` | 仅 Variables 有效 |
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
- 将 `dandelion_tribe_schema.sql` 放到 `scripts/schema/` 并提交 Git（CI/CD 首次空库会自动导入 + 创建 admin/hr）
- 或手动一次性：`./scripts/init-db.sh`（**非常规部署**，勿在每次 git 后执行）

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
git pull --ff-only              # 仅更新 compose/脚本，不重置数据库
./scripts/deploy-server.sh      # pull 镜像 + up -d + bootstrap-db（空库才 seed）
```

`bootstrap-db.sh` 逻辑：

- `users` 表已有数据 → **跳过**（数据在 `mysql_data` volume 持久化）
- 无 `users` 表 → 导入 `scripts/schema/dandelion_tribe_schema.sql`（仅一次）
- `users` 为空 → 创建 `admin` / `hr`（仅一次）

**切勿** `docker compose down -v`，否则会删掉 volume。

然后从 GitHub Runner 请求 `DEPLOY_URL` 做简单 HTTP 探活。

---

## 6. 故障排查

| 现象 | 处理 |
|------|------|
| `Permission denied (publickey)` | 检查 `SSH_PRIVATE_KEY` 是否与服务器 `authorized_keys` 对应 |
| `缺少 .env` | 在服务器 `/root/workspace` 创建 `.env` |
| deploy 被跳过（0s，job 灰色） | GitHub 上仍是旧 workflow（`vars.ENABLE_SSH_DEPLOY == 'true'`）；**push 最新 main** 后重跑 Publish |
| deploy job 跑了但 SSH 步骤跳过 | 未配置 Secret `SSH_PRIVATE_KEY` |
| 想关闭 SSH 部署 | `ENABLE_SSH_DEPLOY=false`（Secret 或 Variable） |
| 数据库无数据 | 确认 `scripts/schema/dandelion_tribe_schema.sql` 已提交；或手动 `./scripts/init-db.sh` |
| 每次部署数据被清空 | 是否误用了 `docker compose down -v` |

---

## 7. 安全提醒

- **切勿** 将 `talentflow-ai.pem` 提交到仓库
- 若密钥曾泄露，在阿里云 **轮换密钥** 并更新 GitHub Secret
- 生产 `.env` 仅保存在服务器，不要写入 workflow

---

## 8. 数据库（首次 vs 日常部署）

**推荐（随 Git 走）：** 把 schema 放进仓库后 push，CI/CD 首次部署自动完成建表 + 账号：

```bash
cp /path/to/dandelion_tribe_schema.sql scripts/schema/dandelion_tribe_schema.sql
git add scripts/schema/dandelion_tribe_schema.sql && git commit && git push
```

**或手动（仅空库一次）：**

```bash
scp dandelion_tribe_schema.sql root@8.218.11.250:/root/workspace/scripts/schema/
ssh root@8.218.11.250 'cd /root/workspace && ./scripts/bootstrap-db.sh && ./scripts/check-db.sh'
```

日常 git push **不会**重新 init；只有 `users` 为空时才会 seed。

默认账号：`admin` / `admin12345`，`hr` / `hr12345678`
