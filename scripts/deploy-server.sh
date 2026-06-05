#!/usr/bin/env bash
# 云服务器：从 Docker Hub 拉镜像并启动（生产模式）
# 在项目根目录执行：chmod +x scripts/deploy-server.sh && ./scripts/deploy-server.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

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
else
  echo "[deploy-server] 警告：缺少 .env.registry，将使用 compose 默认镜像名（需设置 DOCKER_NAMESPACE）"
fi

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "[deploy-server] git pull..."
  git pull --ff-only || true
fi

echo "[deploy-server] pull 镜像..."
"${COMPOSE[@]}" "${ENV_FILES[@]}" pull

echo "[deploy-server] 启动服务..."
"${COMPOSE[@]}" "${ENV_FILES[@]}" up -d --remove-orphans

echo "[deploy-server] 等待 backend 健康..."
for _ in $(seq 1 36); do
  if "${COMPOSE[@]}" "${ENV_FILES[@]}" ps backend 2>/dev/null | grep -q healthy; then
    echo "[deploy-server] backend 已就绪"
    break
  fi
  sleep 5
done

if docker ps --format '{{.Names}}' | grep -q '^talentflow-api$'; then
  echo "[deploy-server] 初始化演示账号（admin / hr，已存在则跳过）..."
  if docker exec talentflow-api test -f /app/scripts/seed_demo_users.py 2>/dev/null; then
    docker exec talentflow-api python scripts/seed_demo_users.py || true
  else
    echo "[deploy-server] 提示：镜像内无 seed 脚本，可 docker cp talentflow-ai-backend-bak/scripts/seed_demo_users.py talentflow-api:/app/scripts/"
  fi
fi

"${COMPOSE[@]}" "${ENV_FILES[@]}" ps

PUBLIC_IP="${PUBLIC_IP:-$(curl -fsS --max-time 3 ifconfig.me 2>/dev/null || true)}"
echo ""
echo "部署完成。"
echo "  前端：http://${PUBLIC_IP:-<公网IP>}/"
echo "  管理：http://${PUBLIC_IP:-<公网IP>}/admin"
echo "  默认账号见 talentflow-ai-backend-bak/scripts/seed_demo_users.py"
echo "  日志：${COMPOSE[*]} ${ENV_FILES[*]} logs -f backend celery-worker"
