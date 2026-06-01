@echo off
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fix-git-remove-lfs-and-models.ps1" %*
pause
