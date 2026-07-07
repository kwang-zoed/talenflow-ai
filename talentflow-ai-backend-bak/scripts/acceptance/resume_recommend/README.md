# 开发期临时验收脚本（E2E 通过后可删除本目录）

## 环境

使用项目 conda 环境：

```powershell
conda activate smart-customer-rag
cd talentflow-ai-backend-bak
```

## 运行

```powershell
# 阶段1（可加 --seed 插入测试简历）
python scripts/acceptance/resume_recommend/test_resume_retriever.py --seed

# 阶段2
python scripts/acceptance/resume_recommend/test_recommend_resumes.py --job-id 1

# 阶段3（需 FastAPI + Celery + Redis 已启动，并设置 HR_TOKEN）
$env:HR_TOKEN="Bearer <jwt>"
$env:JOB_ID=1
bash scripts/acceptance/resume_recommend/test_hr_recommend_api.sh

# 阶段7
python scripts/acceptance/resume_recommend/test_resume_index_hooks.py

# 全量重建简历向量索引（业务脚本，保留在 scripts/）
python scripts/reindex_resumes.py
```

前端手动清单见 `e2e-checklist.md`。
