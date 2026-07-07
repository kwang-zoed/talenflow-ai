"""阶段 0：LangSmith 连通性验收。"""

from __future__ import annotations

from core.bootstrap import get_client, require_api_key, setup_paths

setup_paths()
import config  # noqa: E402


def _print_config_summary() -> None:
    print("=" * 60)
    print("LangSmith Eval Setup — 阶段 0 连通性检查")
    print("=" * 60)
    print(f"  eval project     : {config.LANGSMITH_EVAL_PROJECT}")
    print(f"  endpoint         : {config.LANGSMITH_ENDPOINT}")
    print(f"  api key set      : {bool(config.LANGSMITH_API_KEY.strip())}")
    print(f"  datasets dir     : {config.DATASETS_DIR}")
    print(f"  evaluators dir   : {config.EVALUATORS_DIR}")
    print(f"  schemas dir      : {config.SCHEMAS_DIR}")
    print(f"  rag dataset name : {config.RAG_DATASET_NAME}")
    print(f"  setup test name  : {config.SETUP_TEST_DATASET_NAME}")
    print("-" * 60)


def _ensure_dirs() -> list[str]:
    errors: list[str] = []
    for d, label in (
        (config.DATASETS_DIR, "datasets"),
        (config.EVALUATORS_DIR, "evaluators"),
        (config.SCHEMAS_DIR, "schemas"),
    ):
        if not d.is_dir():
            errors.append(f"目录不存在: {label} ({d})")
    return errors


def _get_or_create_setup_dataset(client):
    name = config.SETUP_TEST_DATASET_NAME
    description = (
        "TalentFlow 评测阶段 0 连通性测试 Dataset，"
        "可安全删除，不影响业务 trace。"
    )
    for ds in client.list_datasets(dataset_name=name):
        print(f"  [reuse] Dataset 已存在: {name} (id={ds.id})")
        return ds
    created = client.create_dataset(dataset_name=name, description=description)
    print(f"  [create] Dataset 已创建: {name} (id={created.id})")
    return created


def _ensure_setup_example(client, dataset_id: str) -> None:
    examples = list(client.list_examples(dataset_id=dataset_id, limit=1))
    if examples:
        print(f"  [reuse] Example 已存在: {examples[0].id}")
        return
    client.create_examples(
        dataset_id=dataset_id,
        inputs=[{"ping": "talentflow-eval-setup"}],
        outputs=[{"status": "ok"}],
    )
    print("  [create] 写入 1 条测试 Example")


def verify_setup() -> int:
    _print_config_summary()

    dir_errors = _ensure_dirs()
    if dir_errors:
        for err in dir_errors:
            print(f"[FAIL] {err}")
        return 1

    if not require_api_key():
        print("[FAIL] 未配置 LANGSMITH_API_KEY（或 LANGCHAIN_API_KEY）")
        print("       请在 .env 中设置后重试。")
        return 1

    try:
        client = get_client()
        projects = list(client.list_projects(limit=5))
        print(f"  [ok] API 连通，可见 project 数（前 5）: {len(projects)}")

        dataset = _get_or_create_setup_dataset(client)
        _ensure_setup_example(client, str(dataset.id))

        read_back = list(client.list_examples(dataset_id=str(dataset.id), limit=5))
        if not read_back:
            print("[FAIL] Dataset 读回 Example 为空")
            return 1
        print(f"  [ok] 读回 Example 数量: {len(read_back)}")

        print()
        print("[OK] 阶段 0 验收通过。")
        print(f"     LangSmith → Datasets → 「{config.SETUP_TEST_DATASET_NAME}」")
        print(f"     Project 空间: {config.LANGSMITH_EVAL_PROJECT}")
        print("     下一步: python scripts/eval/cli.py import-jobs")
        return 0

    except Exception as exc:
        print(f"\n[FAIL] LangSmith 请求失败: {exc}")
        print("常见原因：API Key 无效、网络无法访问 api.smith.langchain.com")
        return 1
