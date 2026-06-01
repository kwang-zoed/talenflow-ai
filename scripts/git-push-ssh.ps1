#Requires -Version 5.1
<#
.SYNOPSIS
  使用项目目录 .github-keys/id_ed25519 推送到 origin（需已配置 git remote）。
#>
param(
    [string]$Branch = "master"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$PrivateKey = Join-Path $Root ".github-keys\id_ed25519"

if (-not (Test-Path $PrivateKey)) {
    Write-Host "未找到私钥，请先运行: .\scripts\setup-github-ssh.ps1" -ForegroundColor Red
    exit 1
}

Set-Location $Root
$env:GIT_SSH_COMMAND = "ssh -i `"$PrivateKey`" -o IdentitiesOnly=yes"
Write-Host "GIT_SSH_COMMAND 已设置，推送到 origin $Branch ..." -ForegroundColor Cyan
git push -u origin $Branch
exit $LASTEXITCODE
