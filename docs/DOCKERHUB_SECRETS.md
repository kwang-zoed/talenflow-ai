# Docker Hub 凭据（给 GitHub Actions Publish 用）

## 和「用 GitHub 登录 Docker Hub」的关系

你用 **GitHub 授权登录** [hub.docker.com](https://hub.docker.com) 时：

- **Docker Hub 用户名**仍是 **`kwangzoed`**（在 Hub 右上角头像 → Account Settings 可确认）
- GitHub Actions **不能**用「GitHub 登录」自动推镜像
- 必须在 Docker Hub **单独创建一个 Access Token**，填到 GitHub Secrets

这和你在本机 `docker login` 用浏览器登录不是同一套机制。

---

## 步骤 1：在 Docker Hub 创建 Token

1. 浏览器打开 https://hub.docker.com （用 GitHub 登录即可）
2. 右上角头像 → **Account Settings**
3. 左侧 **Security** → **Personal access tokens** → **Generate new token**
4. Description 填：`github-actions-talentflow`
5. Permissions 选 **Read & Write**（或 Read, Write, Delete）
6. **Generate**，复制 Token（只显示一次，形如 `dckr_pat_xxxx...`）

---

## 步骤 2：填到 GitHub 仓库 Secrets

仓库 `talenflow-ai`（或你的实际仓库名）：

**Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|------|--------|
| `DOCKERHUB_USERNAME` | `kwangzoed` |
| `DOCKERHUB_TOKEN` | 刚复制的 `dckr_pat_...`（整段粘贴） |

不要加引号，不要有空格换行。

### 名称必须完全一致（区分大小写）

| 正确 | 常见错误（会导致 Username and password required） |
|------|--------------------------------------------------|
| `DOCKERHUB_USERNAME` | `DOCKER_USERNAME`、`dockerhub_username`、`DOCKER_USER` |
| `DOCKERHUB_TOKEN` | `DOCKER_TOKEN`、`DOCKER_PASSWORD`、`GITHUB_TOKEN` |

在 **Repository secrets** 里创建，不要只建在 Environment 里（除非 workflow 绑定了 environment）。

确认仓库是 **`kwang-zoed/talenflow-ai`**（你 push 的那个），Secrets 要建在这个仓库的 Settings 里，不是别的 fork。

Token 类型必须是 Docker Hub 的 **`dckr_pat_...`**，不是 GitHub Personal Access Token。

---

## 步骤 3：验证 Publish 工作流

再 push 一次 `master`，或 **Actions → Publish Docker Hub → Run workflow**。

成功时日志里有：

- `Login Succeeded`
- `pushing ... talentflow-backend:latest`

Hub 上查看：https://hub.docker.com/r/kwangzoed/talentflow-backend/tags

---

## 本机 docker login（可选，与 GitHub 无关）

本机执行 `.\scripts\build-and-push.bat -Login` 时：

- 可用 Hub 用户名 `kwangzoed` + 上面同一个 **Access Token** 作为密码
- 或浏览器登录后的凭据（视 Docker Desktop 而定）

GitHub Actions **只认** Secrets 里的 `DOCKERHUB_*`，不会读你本机 `docker login` 状态。

---

## 仍报 Username and password required？

1. 打开 **Settings → Secrets and variables → Actions → Repository secrets**，确认列表里**正好两条**：`DOCKERHUB_USERNAME`、`DOCKERHUB_TOKEN`。
2. 若是 **Organization secret**，检查是否勾选 “Allow access to repository talentflow-ai / talenflow-ai”。
3. 改完 Secret 后必须 **重新 Run workflow** 或再 push 一次（旧 run 不会自动用新 Secret）。
4. 推送包含「检查 Docker Hub Secrets」步骤的最新 `publish-dockerhub.yml` 后，失败日志会写明是 USERNAME 还是 TOKEN 为空。
