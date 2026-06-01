#Requires -Version 5.1
<#
.SYNOPSIS
  在本项目 .github-keys/ 目录生成 GitHub 专用 SSH 密钥，并可选测试连接。

.EXAMPLE
  .\scripts\setup-github-ssh.ps1
  .\scripts\setup-github-ssh.ps1 -TestOnly
  .\scripts\setup-github-ssh.ps1 -SetRemote -GitHubUser kwang-zoed -RepoName talentflow-ai
#>
param(
    [switch]$TestOnly,
    [switch]$SetRemote,
    [string]$GitHubUser = "kwang-zoed",
    [string]$RepoName = "talentflow-ai",
    [string]$Email = "kwang-zoed@users.noreply.github.com"
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$KeyDir = Join-Path $Root ".github-keys"
$PrivateKey = Join-Path $KeyDir "id_ed25519"
$PublicKey = "$PrivateKey.pub"

New-Item -ItemType Directory -Force -Path $KeyDir | Out-Null

function Get-SshExe {
    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($git) {
        $gitSsh = Join-Path (Split-Path $git.Source) "usr\bin\ssh.exe"
        if (Test-Path $gitSsh) { return $gitSsh }
    }
    return "ssh"
}

$Ssh = Get-SshExe
$IdentityArg = "-i `"$PrivateKey`" -o IdentitiesOnly=yes"

if (-not $TestOnly) {
    if (Test-Path $PrivateKey) {
        Write-Host "私钥已存在，跳过生成: $PrivateKey" -ForegroundColor Yellow
    } else {
        Write-Host "==> 生成 ED25519 密钥 ..." -ForegroundColor Cyan
        & ssh-keygen -t ed25519 -C $Email -f $PrivateKey -N '""'
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Write-Host "已生成:" -ForegroundColor Green
        Write-Host "  私钥 $PrivateKey"
        Write-Host "  公钥 $PublicKey"
    }

    Write-Host ""
    Write-Host "==> 请将下面公钥整段复制到 GitHub -> Settings -> SSH and GPG keys -> New SSH key" -ForegroundColor Cyan
    Write-Host "    https://github.com/settings/keys" -ForegroundColor DarkGray
    Write-Host ""
    Get-Content $PublicKey
    Write-Host ""

    $snippetPath = Join-Path $KeyDir "ssh-config-snippet.txt"
    @"
Host github.com-talentflow
    HostName github.com
    User git
    IdentityFile $PrivateKey
    IdentitiesOnly yes
"@ | Set-Content -Path $snippetPath -Encoding UTF8
    Write-Host "可选: 将以下内容追加到 `$env:USERPROFILE\.ssh\config`" -ForegroundColor DarkYellow
    Write-Host "      文件已保存: $snippetPath"
    Write-Host ""
}

Write-Host "==> 测试 SSH 连接 GitHub ..." -ForegroundColor Cyan
$env:GIT_SSH_COMMAND = "ssh $IdentityArg"
& $Ssh $IdentityArg.Split(' ') -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1
# ssh -T 成功时 exit 1 且输出 Hi xxx，属正常
Write-Host ""
Write-Host "若看到 'Hi $GitHubUser!' 表示公钥已生效。" -ForegroundColor Green

if ($SetRemote) {
    $url = "git@github.com:${GitHubUser}/${RepoName}.git"
    Set-Location $Root
    git remote set-url origin $url
    Write-Host "已设置 origin -> $url" -ForegroundColor Green
    Write-Host "推送示例:" -ForegroundColor Cyan
    Write-Host "  `$env:GIT_SSH_COMMAND = 'ssh -i `"$PrivateKey`" -o IdentitiesOnly=yes'"
    Write-Host "  git push -u origin master"
}
