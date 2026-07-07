#!/usr/bin/env bash
# 使用 smart-customer-rag conda 环境跑后端验收脚本
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR/../../.."
PY="conda run -n smart-customer-rag python"
$PY scripts/acceptance/resume_recommend/test_resume_retriever.py --seed
$PY scripts/acceptance/resume_recommend/test_recommend_resumes.py --job-id "${JOB_ID:-1}"
$PY scripts/acceptance/resume_recommend/test_resume_index_hooks.py
echo "Backend acceptance done. API test: bash scripts/acceptance/resume_recommend/test_hr_recommend_api.sh"
