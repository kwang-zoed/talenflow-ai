#!/usr/bin/env bash
# 【手动】强制重置库：导入 schema + seed（会覆盖/追加 SQL 中的 DDL，慎用）
# 日常 CI/CD 部署请用 deploy-server.sh（不会重复 init）
# 用法：./scripts/init-db.sh [schema.sql]
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

SCHEMA_FILE="${1:-scripts/schema/dandelion_tribe_schema.sql}"
[[ -f "$SCHEMA_FILE" ]] || SCHEMA_FILE="${1:-dandelion_tribe_schema.sql}"

echo "[init-db] 手动初始化（非 CI/CD 常规流程）"
if [[ -f "$SCHEMA_FILE" ]]; then
  source "$ROOT_DIR/scripts/lib/load-env.sh"
  load_dotenv .env
  echo "[init-db] 导入 $SCHEMA_FILE ..."
  docker exec -i talentflow-mysql mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" "${MYSQL_DATABASE:-dandelion_tribe}" < "$SCHEMA_FILE"
fi

bash "$ROOT_DIR/scripts/bootstrap-db.sh"
echo "[init-db] 完成"
