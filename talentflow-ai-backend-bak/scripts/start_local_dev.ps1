# 本地智能投递需要 4 个进程（4 个 PowerShell 窗口）
# 用法: 在 talentflow-ai-backend-bak 目录执行 .\scripts\start_local_dev.ps1 查看说明

$BackendRoot = Split-Path $PSScriptRoot -Parent
Write-Host "=== TalentFlow 本地开发（智能投递）===" -ForegroundColor Cyan
Write-Host "工作目录: $BackendRoot"
Write-Host ""
Write-Host "窗口 1 - Redis（若未安装服务，可用 Docker: docker run -d -p 6379:6379 redis:7 --requirepass 123456）"
Write-Host "窗口 2 - MCP Server:"
Write-Host "  cd $BackendRoot"
Write-Host "  conda activate smart-customer-rag"
Write-Host "  python -m mcp_server.server"
Write-Host ""
Write-Host "窗口 3 - Celery Worker:"
Write-Host "  cd $BackendRoot"
Write-Host "  conda activate smart-customer-rag"
Write-Host "  celery -A app.core.celery_app worker --loglevel=info --pool=solo"
Write-Host ""
Write-Host "窗口 4 - FastAPI:"
Write-Host "  cd $BackendRoot"
Write-Host "  conda activate smart-customer-rag"
Write-Host "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
Write-Host ""
Write-Host "自检（登录后带 Token）:"
Write-Host "  GET http://127.0.0.1:8000/api/v1/user/smart-apply/readiness"
Write-Host "  POST http://127.0.0.1:8000/api/v1/user/smart-apply/submit"
Write-Host "  GET  http://127.0.0.1:8000/api/v1/user/smart-apply/status/{task_id}"
Write-Host ""
Write-Host "LangSmith 只有 verify_ping 是正常的：必须 Celery 跑完图才有 smart_apply_astream trace。"
