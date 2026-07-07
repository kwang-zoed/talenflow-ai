# TalentFlow LangSmith 评测基线对比记录

> 最后更新：2026-06-08（阶段 5 + CLI 合并）  
> 流程完整说明：[langsmith-eval-guide.md](./langsmith-eval-guide.md)  
> **生产方案**：[langsmith-eval-production-plan.md](./langsmith-eval-production-plan.md)

## 统一入口

```bash
conda activate smart-customer-rag
cd talentflow-ai-backend-bak

python scripts/eval/cli.py setup
python scripts/eval/cli.py import-jobs
python scripts/eval/cli.py seed --pipeline rag
python scripts/eval/cli.py smoke --pipeline rag --all
python scripts/eval/cli.py run --pipeline rag
python scripts/eval/cli.py run --pipeline smart_apply
```

## 实验一览

| 实验 ID | 数据集 | 评估器 | 说明 |
|---------|--------|--------|------|
| `talentflow-rag-v1-baseline-20260608-922ef3c8` | v1 (8条→后扩13) | 格式+Recall+Precision+Embedding | 阶段 2 核心指标 |
| `talentflow-rag-v1-full-20260608-65ce3ee8` | v1 (13条) | 上述 + LLM Judge | 阶段 3 完整 RAG |
| `talentflow-smart-apply-v1-20260608-7d61cf0c` | smart_apply v1 (5条) | 格式 + LLM Judge | 阶段 4 |
| `talentflow-rag-v2-20260608-7f718836` | v2 (13条) | 格式+Recall+Precision+Embedding | 阶段 5 复审 |

## RAG：阶段 2 vs 阶段 3（核心 → 完整）

```bash
python scripts/eval/cli.py compare \
  --baseline talentflow-rag-v1-baseline-20260608-922ef3c8 \
  --candidate talentflow-rag-v1-full-20260608-65ce3ee8 \
  --out scripts/eval/docs/rag_baseline_vs_full.md
```

**预期结论（基于阶段 2/3 跑通结果）：**

| 维度 | 稳定性 | 说明 |
|------|--------|------|
| `valid_format` | 稳定 1.0 | HybridRetriever 输出契约固定 |
| `recall_at_k` | 稳定 1.0 | 13 条合成标注与检索一致 |
| `precision_at_k` | 随 K 变化 | 多期望 ID 时 precision 低于 recall |
| `semantic_similarity_avg` | 稳定偏高 | BGE 与 eval 职位同分布 |
| `relevance_score` | 新增维度 | Judge 提供业务语义边界判断 |
| `relevance_pass` | 新增维度 | ≥4/5 二值化通过率 |

## BadCase 分析结论

```bash
python scripts/eval/cli.py analyze \
  --experiment talentflow-rag-v1-full-20260608-65ce3ee8 \
  --out scripts/eval/docs/rag_badcases.json
```

阶段 5 首次分析：合成 golden set 上 **无 recall@5 失败项**，标注质量可接受。

后续优化方向：

1. 引入真实业务 query（`cli.py trace`）扩充 v2+
2. 对 `relevance_score` 边界样本（3 分）做人工复审
3. 调整 BM25/FAISS 权重后，用 `cli.py compare` 做 A/B 对比

## 数据集版本

| 版本 | 条数 | 变更 |
|------|------|------|
| v1 | 13 | 合成用例 + eval 职位 9001-9013 |
| v2 | 13 | 标注复审 + CHANGELOG + source 元数据 |

上传 v2：

```bash
python scripts/eval/cli.py seed --pipeline rag \
  --file talentflow_golden_set_v2.json --replace
python scripts/eval/cli.py run --pipeline rag \
  --dataset talentflow_golden_set_v2 --prefix talentflow-rag-v2
```

## Trace 补充流程

```bash
# Smart Apply trace → 本地 JSON
python scripts/eval/cli.py trace --source smart_apply --limit 20 \
  --out scripts/eval/datasets/traces_export.json

# RAG 评估 run → 建议标注（需人工复审 expected_job_ids）
python scripts/eval/cli.py trace --source eval_rag \
  --experiment talentflow-rag-v1-full-20260608-65ce3ee8 --dry-run
```

## 目录结构（合并后）

```
scripts/eval/
├── cli.py                 # 统一入口
├── config.py
├── core/                  # bootstrap, dataset_io, runner, analysis, traces, setup
├── pipelines/             # rag.py, smart_apply.py
├── evaluators/            # 评估器 + _common.py
├── schemas/, datasets/, docs/
└── *.py                   # 旧脚本薄包装（兼容）
```
