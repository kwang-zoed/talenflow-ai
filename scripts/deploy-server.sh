#!/usr/bin/env bash
# 云服务器：Hub 拉镜像 + 启动；仅在数据库为空时 bootstrap admin/hr（不重复初始化）
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# Windows 检出脚本可能是 CRLF，Linux 上先转 LF
find scripts -type f -name '*.sh' -exec sed -i 's/\r$//' {} + 2>/dev/null || true

COMPOSE=(docker compose \
  -f docker-compose.yml \
  -f docker-compose.pull.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.hub-entrypoint-fix.yml)
ENV_FILES=(--env-file .env)

if [[ ! -f .env ]]; then
  echo "[deploy-server] 缺少 .env，请：cp .env.production.example .env && nano .env"
  exit 1
fi

if [[ -f .env.registry ]]; then
  ENV_FILES+=(--env-file .env.registry)
fi

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "[deploy-server] git pull（仅更新 compose/脚本，不重置数据库）..."
  git pull --ff-only || true
fi

echo "[deploy-server] pull 镜像..."
"${COMPOSE[@]}" "${ENV_FILES[@]}" pull

echo "[deploy-server] 启动服务（数据卷 mysql_data 保留）..."
"${COMPOSE[@]}" "${ENV_FILES[@]}" up -d --remove-orphans

echo "[deploy-server] 等待 backend 健康..."
for _ in $(seq 1 36); do
  if "${COMPOSE[@]}" "${ENV_FILES[@]}" ps backend 2>/dev/null | grep -q healthy; then
    echo "[deploy-server] backend 已就绪"
    break
  fi
  sleep 5
done

# 仅首次空库时 seed；已有 admin/hr 则 bootstrap 直接跳过
if [[ -x scripts/bootstrap-db.sh ]]; then
  bash scripts/bootstrap-db.sh || true
fi

"${COMPOSE[@]}" "${ENV_FILES[@]}" ps

PUBLIC_IP="${PUBLIC_IP:-$(curl -fsS --max-time 3 ifconfig.me 2>/dev/null || true)}"
echo ""
echo "部署完成。数据持久化在 Docker volume mysql_data，不会因 git 部署而清空。"
echo "  前端：http://${PUBLIC_IP:-<公网IP>}/"
echo "  管理：http://${PUBLIC_IP:-<公网IP>}/admin"
