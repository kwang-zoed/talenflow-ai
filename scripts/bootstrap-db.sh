#!/usr/bin/env bash
# 首次部署时：缺表则导入 schema（仅一次）；users 为空则创建 admin/hr
# 后续 git/CI 部署：已有数据则跳过，依赖 Docker volume mysql_data 持久化
#
# 环境变量：
#   SKIP_DB_BOOTSTRAP=1  完全跳过（deploy-server.sh 会读取）
#   SCHEMA_FILE          指定 schema 路径
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "${SKIP_DB_BOOTSTRAP:-0}" == "1" ]]; then
  echo "[bootstrap-db] SKIP_DB_BOOTSTRAP=1，跳过"
  exit 0
fi

# shellcheck source=scripts/lib/load-env.sh
source "$ROOT_DIR/scripts/lib/load-env.sh"
load_dotenv .env

MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:?请在 .env 设置 MYSQL_ROOT_PASSWORD}"
MYSQL_DATABASE="${MYSQL_DATABASE:-dandelion_tribe}"

pick_schema_file() {
  local candidates=(
    "${SCHEMA_FILE:-}"
    "${ROOT_DIR}/scripts/schema/dandelion_tribe_schema.sql"
    "${ROOT_DIR}/dandelion_tribe_schema.sql"
  )
  for f in "${candidates[@]}"; do
    [[ -n "$f" && -f "$f" ]] && { echo "$f"; return 0; }
  done
  return 1
}

if ! docker ps --format '{{.Names}}' | grep -q '^talentflow-mysql$'; then
  echo "[bootstrap-db] talentflow-mysql 未运行，跳过"
  exit 0
fi

if ! docker ps --format '{{.Names}}' | grep -q '^talentflow-api$'; then
  echo "[bootstrap-db] talentflow-api 未运行，跳过"
  exit 0
fi

TABLE_COUNT="$(docker exec talentflow-mysql mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" -N -e \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${MYSQL_DATABASE}';" 2>/dev/null || echo 0)"

USERS_EXISTS="$(docker exec talentflow-mysql mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" -N -e \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${MYSQL_DATABASE}' AND table_name='users';" 2>/dev/null || echo 0)"

USER_COUNT=0
if [[ "${USERS_EXISTS}" -gt 0 ]]; then
  USER_COUNT="$(docker exec talentflow-mysql mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" -N -e \
    "SELECT COUNT(*) FROM ${MYSQL_DATABASE}.users;" 2>/dev/null || echo 0)"
fi

echo "[bootstrap-db] 表数量=${TABLE_COUNT} users表=${USERS_EXISTS} users行数=${USER_COUNT}"

# 已有用户 → 不做任何初始化（数据在 mysql_data volume 里持久化）
if [[ "${USER_COUNT}" -gt 0 ]]; then
  echo "[bootstrap-db] 已有账号，跳过（不会重复初始化）"
  exit 0
fi

# 首次：无 users 表 → 导入 schema（仅当库基本为空或缺 users 表）
if [[ "${USERS_EXISTS}" -eq 0 ]]; then
  SCHEMA_PATH=""
  SCHEMA_PATH="$(pick_schema_file)" || true
  if [[ -n "${SCHEMA_PATH}" ]]; then
    echo "[bootstrap-db] 首次导入 schema: ${SCHEMA_PATH}"
    docker exec -i talentflow-mysql mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" "${MYSQL_DATABASE}" < "${SCHEMA_PATH}"
  else
    echo "[bootstrap-db] 警告：无 users 表且未找到 schema 文件，跳过建表"
    echo "  请放置 scripts/schema/dandelion_tribe_schema.sql 后重新部署"
    exit 0
  fi
fi

# 首次：users 为空 → 创建 admin / hr（不依赖镜像内 seed 脚本）
echo "[bootstrap-db] 首次写入 admin / hr ..."
docker exec -i talentflow-api python - <<'PY'
from app.core.database import SessionLocal
from app.core import security
from app.models.user import User

SEED = [
    ("admin", "admin@talentflow.local", "admin12345", 1, "系统管理员"),
    ("hr", "hr@talentflow.local", "hr12345678", 2, "HR导师"),
]
db = SessionLocal()
try:
    for username, email, pwd, role, full_name in SEED:
        if db.query(User).filter(User.username == username).first():
            print(f"[skip] {username}")
            continue
        u = User(
            username=username,
            email=email,
            password=security.get_password_hash(pwd),
            role=role,
            full_name=full_name,
            is_active=True,
        )
        db.add(u)
        db.commit()
        print(f"[ok] {username} role={role}")
finally:
    db.close()
PY

echo "[bootstrap-db] 完成（后续部署不会重复执行）"
