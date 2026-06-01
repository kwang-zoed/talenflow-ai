# 大模型文件说明

GitHub **禁止**单文件 >100MB。本仓库 **不提交** BGE 权重（reranker 约 2.1GB）。

## 本地开发（Conda）

```powershell
cd talentflow-ai-backend-bak
pip install huggingface_hub
$env:HF_ENDPOINT = "https://hf-mirror.com"
python scripts/download_models.py
```

## Docker 构建

`Dockerfile` 在 `docker build` 时自动执行 `download_models.py`（默认 `HF_ENDPOINT=https://hf-mirror.com`）。

## GitHub Actions CI / Publish

无需改 workflow：构建镜像时会下载模型（首次较慢，BuildKit 可缓存 layer）。

## 目录（本地存在，Git 忽略）

| 路径 | 用途 |
|------|------|
| `app/bge-small-zh-v1.5-embedding/` | 职位 embedding |
| `app/bge-reranker-v2-m3/` | 推荐 rerank |

## 不要用 Git LFS 存模型

2GB 的 reranker 超出 GitHub 单文件 100MB 限制，LFS 免费配额也不够。  
若曾执行过 `git lfs track "*.safetensors"`，请运行（任选一种）：

```powershell
# 方式 A：双击或在 cmd 里运行（不受执行策略限制）
scripts\fix-git-remove-lfs-and-models.bat

# 方式 B：单次绕过执行策略
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\fix-git-remove-lfs-and-models.ps1

git push -u origin master --force
```

## 清理 Git 历史（push 仍报大文件时）

旧 commit 里若已包含 2GB 模型，仅 `git rm --cached` 不够，需从历史删除：

```powershell
# 需先安装: pip install git-filter-repo
git filter-repo --invert-paths --path talentflow-ai-backend-bak/app/bge-reranker-v2-m3 --force
git filter-repo --invert-paths --path talentflow-ai-backend-bak/app/bge-small-zh-v1.5-embedding --force
git remote add origin git@github.com:kwang-zoed/talenflow-ai.git
git push -u origin master --force
```

或新建干净分支（简单但丢历史）：

```powershell
git checkout --orphan master-clean
git add .
git commit -m "chore: initial without large models"
git branch -D master
git branch -m master
git push -u origin master --force
```

## 构建镜像怎么办？

**不依赖 Git 里的模型。** `docker build` / GitHub Actions 会在镜像构建阶段执行 `download_models.py`，模型打进镜像 layer，推 Docker Hub 时一并带上。

