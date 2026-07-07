#!/usr/bin/env bash
# 查看 Docker MySQL 状态与 users 表
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# shellcheck source=scripts/lib/load-env.sh
source "$ROOT_DIR/scripts/lib/load-env.sh"
load_dotenv .env

PW="${MYSQL_ROOT_PASSWORD:?}"
DB="${MYSQL_DATABASE:-dandelion_tribe}"

echo "=== MySQL 容器 ==="
docker ps --filter name=talentflow-mysql --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "=== 表列表 ==="
docker exec talentflow-mysql mysql -uroot -p"${PW}" -e "USE ${DB}; SHOW TABLES;"

echo ""
echo "=== users ==="
docker exec talentflow-mysql mysql -uroot -p"${PW}" -e \
  "SELECT id, username, email, role, is_active FROM ${DB}.users;"
