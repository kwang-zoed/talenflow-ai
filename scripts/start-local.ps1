# 使用 conda 环境 smart-customer-rag 启动本地后端
# 用法：先 conda activate smart-customer-rag，或在各终端用下面命令

$CondaEnv = "smart-customer-rag"
$Python = "C:\DevelopSoftware\Anaconda\envs\smart-customer-rag\python.exe"
$Celery = "C:\DevelopSoftware\Anaconda\envs\smart-customer-rag\Scripts\celery.exe"
$Backend = "C:\Users\kzd\Desktop\talentflow-ai\talentflow-ai-backend-bak"
$Frontend = "C:\Users\kzd\Desktop\talentflow-ai\talentflow-ai-frontend"

Write-Host "Conda 环境: $CondaEnv" -ForegroundColor Cyan
Write-Host ""
Write-Host "前置：MySQL localhost:3306、Redis localhost:6379（密码 123456）已启动" -ForegroundColor Yellow
Write-Host ""
Write-Host "=== 方式 A：4 个终端手动启动 ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "conda activate $CondaEnv" -ForegroundColor Gray
Write-Host ""
Write-Host "# 终端1 MCP" -ForegroundColor Yellow
Write-Host "cd `"$Backend`""
Write-Host "python mcp_server/server.py"
Write-Host ""
Write-Host "# 终端2 FastAPI" -ForegroundColor Yellow
Write-Host "cd `"$Backend`""
Write-Host "uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
Write-Host ""
Write-Host "# 终端3 Celery" -ForegroundColor Yellow
Write-Host "cd `"$Backend`""
Write-Host "celery -A app.core.celery_app worker --loglevel=info --pool=solo"
Write-Host ""
Write-Host "# 终端4 前端（任意终端，无需 conda）" -ForegroundColor Yellow
Write-Host "cd `"$Frontend`""
Write-Host "npm run dev"
Write-Host ""
Write-Host "前端: http://localhost:5173  |  API: http://localhost:8000/docs" -ForegroundColor Green
