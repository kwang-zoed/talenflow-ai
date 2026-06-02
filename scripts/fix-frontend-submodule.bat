@echo off
REM 将 talentflow-ai-frontend 从「坏掉的 submodule」改为普通目录，便于 GitHub CI 能检出前端代码
cd /d "%~dp0.."
echo ==^> 移除 submodule 指针 ...
git rm --cached talentflow-ai-frontend 2>nul
if exist "talentflow-ai-frontend\.git" (
  echo ==^> 删除嵌套的 .git（保留源码文件）...
  rmdir /s /q "talentflow-ai-frontend\.git"
)
git add talentflow-ai-frontend
echo.
echo 请执行:
echo   git commit -m "fix: track frontend as normal folder, not broken submodule"
echo   git push origin master
pause
