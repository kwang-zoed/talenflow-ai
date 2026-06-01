#Requires -Version 5.1
param(
    [switch]$BuildOnly,
    [switch]$Login,
    [switch]$PruneLocal,
    [string]$RegistryEnvFile = ".env.registry",
    [string]$KeepTags = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Test-DockerCli {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Host ""
        Write-Host "ERROR: docker command not found. Install Docker Desktop first." -ForegroundColor Red
        Write-Host "  winget install -e --id Docker.DockerDesktop" -ForegroundColor Yellow
        Write-Host "  See docs/DOCKER_INSTALL.md" -ForegroundColor Yellow
        exit 1
    }
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Docker is not running. Start Docker Desktop." -ForegroundColor Red
        exit 1
    }
}

function Load-RegistryEnv {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        Write-Host "ERROR: missing $Path. Run: Copy-Item .env.registry.example .env.registry" -ForegroundColor Red
        exit 1
    }
    Get-Content $Path | ForEach-Object {
        if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
        if ($_ -match '^([^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            Set-Item -Path "env:$name" -Value $value
        }
    }
    if ($env:DOCKER_NAMESPACE -eq "your-dockerhub-username" -or [string]::IsNullOrWhiteSpace($env:DOCKER_NAMESPACE)) {
        Write-Host "ERROR: set DOCKER_NAMESPACE in .env.registry" -ForegroundColor Red
        exit 1
    }
    if (-not $env:DOCKER_REGISTRY) { $env:DOCKER_REGISTRY = "docker.io" }
    if (-not $env:IMAGE_TAG) { $env:IMAGE_TAG = "latest" }
}

Test-DockerCli
Load-RegistryEnv -Path $RegistryEnvFile

$backendImage = "$($env:DOCKER_REGISTRY)/$($env:DOCKER_NAMESPACE)/talentflow-backend:$($env:IMAGE_TAG)"
$frontendImage = "$($env:DOCKER_REGISTRY)/$($env:DOCKER_NAMESPACE)/talentflow-frontend:$($env:IMAGE_TAG)"

Write-Host "==> Image tags" -ForegroundColor Cyan
Write-Host "    backend:  $backendImage"
Write-Host "    frontend: $frontendImage"
Write-Host "    (mcp-server and celery-worker use the same backend image)"
Write-Host ""

if ($Login) {
    Write-Host "==> docker login $($env:DOCKER_REGISTRY)" -ForegroundColor Cyan
    docker login $env:DOCKER_REGISTRY
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "==> docker compose build (may take 20-40 min)" -ForegroundColor Cyan
docker compose `
    -f docker-compose.yml `
    -f docker-compose.registry.yml `
    --env-file $RegistryEnvFile `
    build backend frontend

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "==> Build done. Local images:" -ForegroundColor Green
docker images | Select-String "talentflow"

if ($BuildOnly) {
    Write-Host ""
    Write-Host "BuildOnly: skip push. Run: .\scripts\build-and-push.bat -Login" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "==> docker push" -ForegroundColor Cyan
docker push $backendImage
if ($LASTEXITCODE -ne 0) {
    Write-Host "HINT: run docker login first" -ForegroundColor Yellow
    exit $LASTEXITCODE
}
docker push $frontendImage
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($PruneLocal) {
    $keep = if ($KeepTags) { $KeepTags } else { $env:IMAGE_TAG }
    Write-Host ""
    Write-Host "==> Prune old local talentflow images (keep: $keep)" -ForegroundColor Cyan
    $pruneScript = Join-Path (Split-Path $MyInvocation.MyCommand.Path) "prune-talentflow-images.ps1"
    & $pruneScript -Registry $env:DOCKER_REGISTRY -Namespace $env:DOCKER_NAMESPACE -KeepTags $keep
}

Write-Host ""
Write-Host "==> Push succeeded" -ForegroundColor Green
Write-Host "  docker pull $backendImage"
Write-Host "  docker pull $frontendImage"
Write-Host ""
Write-Host "On server use docker-compose.pull.yml to deploy from registry."
