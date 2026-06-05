#!/usr/bin/env bash
# 导入空库 schema 并 seed 管理员/HR（首次部署）
# 用法：./scripts/init-db.sh [schema.sql路径]
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

SCHEMA_FILE="${1:-dandelion_tribe_schema.sql}"

if [[ ! -f .env ]]; then
  echo "[init-db] 缺少 .env"
  exit 1
fi

# shellcheck disable=SC1091
set -a
source .env
set +a

MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:?请在 .env 设置 MYSQL_ROOT_PASSWORD}"
MYSQL_DATABASE="${MYSQL_DATABASE:-dandelion_tribe}"

if [[ -f "$SCHEMA_FILE" ]]; then
  echo "[init-db] 导入 $SCHEMA_FILE ..."
  docker exec -i talentflow-mysql mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" "${MYSQL_DATABASE}" < "$SCHEMA_FILE"
else
  echo "[init-db] 未找到 $SCHEMA_FILE，跳过 schema 导入"
fi

if docker exec talentflow-api test -f /app/scripts/seed_demo_users.py 2>/dev/null; then
  docker exec talentflow-api python scripts/seed_demo_users.py
else
  echo "[init-db] 请先拷贝 seed 脚本或更新 backend 镜像"
  exit 1
fi

echo "[init-db] 完成"
