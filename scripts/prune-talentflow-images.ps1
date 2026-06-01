#Requires -Version 5.1
<#
.SYNOPSIS
  删除本机旧的 talentflow-backend / talentflow-frontend 镜像，保留指定 tag。

.EXAMPLE
  .\scripts\prune-talentflow-images.ps1 -Namespace kwangzoed -KeepTags latest,abc123def
  .\scripts\prune-talentflow-images.ps1 -Namespace kwangzoed -DryRun
#>
param(
    [string]$Registry = "docker.io",
    [Parameter(Mandatory = $true)]
    [string]$Namespace,
    [string]$KeepTags = "latest",
    [switch]$DryRun
)

$ErrorActionPreference = "Continue"
$keepSet = @{}
foreach ($t in ($KeepTags -split ',')) {
    $k = $t.Trim()
    if ($k) { $keepSet[$k] = $true }
}

function Test-KeepTag([string]$Tag) {
    return $keepSet.ContainsKey($Tag)
}

foreach ($short in @("talentflow-backend", "talentflow-frontend")) {
    $repo = "$Registry/$Namespace/$short"
    Write-Host "==> Prune $repo" -ForegroundColor Cyan
    $images = docker images $repo --format "{{.Repository}}:{{.Tag}}" 2>$null
    if (-not $images) {
        Write-Host "  (none)"
        continue
    }
    foreach ($ref in $images) {
        if ($ref -match '<none>') { continue }
        $tag = ($ref -split ':')[-1]
        if (Test-KeepTag $tag) {
            Write-Host "  keep  $ref" -ForegroundColor Green
            continue
        }
        if ($DryRun) {
            Write-Host "  [dry] rm $ref" -ForegroundColor Yellow
        } else {
            Write-Host "  rm    $ref" -ForegroundColor DarkYellow
            docker rmi -f $ref 2>$null | Out-Null
        }
    }
}

if (-not $DryRun) {
    docker image prune -f | Out-Null
    Write-Host "==> docker image prune -f done" -ForegroundColor Green
}
