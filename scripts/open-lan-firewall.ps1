#Requires -RunAsAdministrator
# Allow LAN access to TalentFlow on port 8080
# Run in elevated PowerShell:
#   Set-ExecutionPolicy -Scope Process Bypass -Force
#   .\scripts\open-lan-firewall.ps1

$ErrorActionPreference = "Stop"

$ruleName = "TalentFlow HTTP 8080"
$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if ($existing) {
    Enable-NetFirewallRule -DisplayName $ruleName
    Write-Host "Enabled existing rule: $ruleName"
}
else {
    New-NetFirewallRule `
        -DisplayName $ruleName `
        -Direction Inbound `
        -Protocol TCP `
        -LocalPort 8080 `
        -Action Allow `
        -Profile Private, Public
    Write-Host "Created inbound rule: TCP 8080 (Private + Public)"
}

$dockerRule = "TalentFlow Docker Desktop"
if (-not (Get-NetFirewallRule -DisplayName $dockerRule -ErrorAction SilentlyContinue)) {
    $dockerExe = Join-Path $env:ProgramFiles "Docker\Docker\resources\com.docker.backend.exe"
    if (Test-Path $dockerExe) {
        New-NetFirewallRule `
            -DisplayName $dockerRule `
            -Direction Inbound `
            -Program $dockerExe `
            -Action Allow `
            -Profile Private, Public
        Write-Host "Allowed Docker Desktop inbound: $dockerExe"
    }
}

Write-Host ""
Write-Host "LAN URLs (use the Wi-Fi IP on your phone):" -ForegroundColor Cyan
Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
    ForEach-Object { Write-Host ("  http://{0}:8080/admin" -f $_.IPAddress) }

Write-Host ""
Write-Host "Phone: same Wi-Fi as PC, no guest/AP isolation, network profile = Private." -ForegroundColor Yellow
Write-Host "Dev default port 8080; production server uses port 80 (see docs/DEPLOY_SERVER.md)." -ForegroundColor Yellow
