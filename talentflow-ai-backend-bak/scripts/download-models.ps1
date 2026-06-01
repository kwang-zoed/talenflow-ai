#Requires -Version 5.1
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root
if (-not $env:HF_ENDPOINT) { $env:HF_ENDPOINT = "https://hf-mirror.com" }
Write-Host "HF_ENDPOINT=$env:HF_ENDPOINT" -ForegroundColor Cyan
pip install -q huggingface_hub
python scripts/download_models.py @args
