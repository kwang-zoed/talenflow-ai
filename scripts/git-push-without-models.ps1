#Requires -Version 5.1
<#
  从 Git 索引移除大模型并重写最近一次提交历史中的大文件（便于 push GitHub）。
  用法: 在项目根目录 .\scripts\git-push-without-models.ps1
#>
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

Write-Host "==> 从 Git 跟踪中移除 BGE 模型目录 ..." -ForegroundColor Cyan
git rm -r --cached talentflow-ai-backend-bak/app/bge-small-zh-v1.5-embedding 2>$null
git rm -r --cached talentflow-ai-backend-bak/app/bge-reranker-v2-m3 2>$null
if (Test-Path .gitattributes) { git rm --cached .gitattributes 2>$null; Remove-Item .gitattributes -Force }

git add .gitignore talentflow-ai-backend-bak/Dockerfile talentflow-ai-backend-bak/scripts/download_models.py docs/MODELS.md

Write-Host ""
Write-Host "==> 请执行:" -ForegroundColor Yellow
Write-Host "  git commit -m `"chore: remove models from git, download at docker build`""
Write-Host "  git push -u origin master"
Write-Host ""
Write-Host "若 push 仍提示大文件，说明旧 commit 里还有 blob，需:" -ForegroundColor Yellow
Write-Host "  git filter-repo --invert-paths --path talentflow-ai-backend-bak/app/bge-reranker-v2-m3 --force"
Write-Host "  或见 docs/MODELS.md 「清理历史」一节"
