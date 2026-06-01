#Requires -Version 5.1
<#
  修复 LFS + 大模型导致 push 失败：
  1. 关闭 Git LFS（不再用 LFS 存模型）
  2. 从 Git 索引移除 bge 模型目录
  3. 用 orphan 分支重建历史（去掉 2GB blob）
  4. 提示 force push

  用法（项目根）:
    .\scripts\fix-git-remove-lfs-and-models.ps1
    .\scripts\fix-git-remove-lfs-and-models.ps1 -ForcePush
#>
param(
    [switch]$ForcePush,
    [string]$Branch = "master"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

Write-Host "=== 1. 关闭 Git LFS ===" -ForegroundColor Cyan
if (Get-Command git-lfs -ErrorAction SilentlyContinue) {
    git lfs uninstall --local 2>$null
}
git config --local --unset-all lfs.repositoryformatversion 2>$null
git config --local lfs.https://github.com/kwang-zoed/talenflow-ai.git/info/lfs.locksverify false 2>$null
git config --local lfs.https://github.com/kwang-zoed/talentflow-ai.git/info/lfs.locksverify false 2>$null
if (Test-Path .gitattributes) {
    Remove-Item .gitattributes -Force
    Write-Host "已删除 .gitattributes"
}

Write-Host ""
Write-Host "=== 2. 从 Git 索引移除模型（本地文件保留）===" -ForegroundColor Cyan
git rm -r --cached talentflow-ai-backend-bak/app/bge-small-zh-v1.5-embedding 2>$null
git rm -r --cached talentflow-ai-backend-bak/app/bge-reranker-v2-m3 2>$null
git rm --cached talentflow-ai-backend-bak/data/langgraph_checkpoints.sqlite 2>$null
git rm --cached talentflow-ai-backend-bak/data/langgraph_checkpoints.sqlite-shm 2>$null
git rm --cached talentflow-ai-backend-bak/data/langgraph_checkpoints.sqlite-wal 2>$null

Write-Host ""
Write-Host "=== 3. 暂存当前代码（.gitignore 已忽略模型）===" -ForegroundColor Cyan
git add -A
$staged = git diff --cached --stat
Write-Host $staged

Write-Host ""
Write-Host "=== 4. 创建无大文件的新历史（orphan 分支）===" -ForegroundColor Cyan
git checkout --orphan "${Branch}-clean"
git add -A
git commit -m "chore: initial push without large models (download at docker build)"

git branch -D $Branch 2>$null
git branch -m $Branch
Write-Host "当前分支已重建为 $Branch（不含 2GB 模型 blob）" -ForegroundColor Green

Write-Host ""
Write-Host "=== 5. 确认远程 ===" -ForegroundColor Cyan
git remote -v
Write-Host "仓库名应为 GitHub 上真实名称（talenflow-ai 或 talentflow-ai）"

Write-Host ""
Write-Host "=== 6. 推送 ===" -ForegroundColor Cyan
Write-Host "  git push -u origin $Branch --force"
Write-Host ""
Write-Host "模型以后由 Docker 构建时 download_models.py 下载，见 docs/MODELS.md" -ForegroundColor DarkGray

if ($ForcePush) {
    Write-Host "正在 force push ..." -ForegroundColor Yellow
    git push -u origin $Branch --force
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Push 成功。" -ForegroundColor Green
    } else {
        Write-Host "Push 失败，请检查 SSH 与仓库 URL。" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}
