@echo off
REM 绕过 PowerShell 执行策略，运行构建推送脚本
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build-and-push.ps1" %*
