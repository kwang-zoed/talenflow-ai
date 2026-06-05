#!/usr/bin/env bash
# 远程服务器部署入口
#
# 模式：
#   pull（默认）  从 Docker Hub 拉镜像 → ./scripts/deploy-server.sh
#   build         在服务器本地构建 → 使用 prod compose + --build
#
# 用法：
#   DEPLOY_MODE=pull ./scripts/deploy-remote.sh
#   DEPLOY_MODE=build ./scripts/deploy-remote.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

MODE="${DEPLOY_MODE:-pull}"

case "$MODE" in
  pull|server|hub)
    exec "$ROOT_DIR/scripts/deploy-server.sh"
    ;;
  build)
    ;;
  *)
    echo "未知 DEPLOY_MODE=$MODE，可选：pull | build"
    exit 1
    ;;
esac

if [[ ! -f .env ]]; then
  echo "[deploy] 错误：缺少 .env，请先 cp .env.production.example .env"
  exit 1
fi

COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.prod.yml)

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git pull --ff-only || true
fi

echo "[deploy] 本地构建并启动（生产模式）..."
docker compose "${COMPOSE_FILES[@]}" up -d --build --remove-orphans

for _ in $(seq 1 30); do
  if docker compose "${COMPOSE_FILES[@]}" ps backend | grep -q healthy; then
    echo "[deploy] backend 已就绪"
    break
  fi
  sleep 5
done

docker compose "${COMPOSE_FILES[@]}" ps
echo ""
echo "部署完成。访问：http://$(curl -fsS --max-time 2 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')/"
