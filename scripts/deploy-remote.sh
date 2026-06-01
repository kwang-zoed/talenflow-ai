#!/usr/bin/env bash
# 远程服务器一键部署（在项目根目录执行）
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  echo "[deploy] 错误：缺少 .env，请先 cp .env.example .env 并填写生产配置"
  exit 1
fi

COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.prod.yml)

echo "[deploy] 拉取/更新代码（若使用 git）..."
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git pull --ff-only || true
fi

echo "[deploy] 构建并启动（生产模式）..."
docker compose "${COMPOSE_FILES[@]}" up -d --build --remove-orphans

echo "[deploy] 等待 backend 健康..."
for i in $(seq 1 30); do
  if docker compose "${COMPOSE_FILES[@]}" ps backend | grep -q healthy; then
    echo "[deploy] backend 已就绪"
    break
  fi
  sleep 5
done

docker compose "${COMPOSE_FILES[@]}" ps

echo ""
echo "部署完成。访问：http://$(hostname -I | awk '{print $1}')"
echo "查看日志：docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f backend celery-worker"
