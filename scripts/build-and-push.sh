#!/usr/bin/env bash
# 构建并推送镜像（Linux / macOS / Git Bash）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

REGISTRY_ENV="${1:-.env.registry}"
BUILD_ONLY="${BUILD_ONLY:-0}"

if ! command -v docker >/dev/null 2>&1; then
  echo "[错误] 未安装 docker，见 docs/DOCKER_INSTALL.md"
  exit 1
fi

if [[ ! -f "$REGISTRY_ENV" ]]; then
  echo "[错误] 缺少 $REGISTRY_ENV，请：cp .env.registry.example .env.registry"
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$REGISTRY_ENV"
set +a

if [[ -z "${DOCKER_NAMESPACE:-}" || "$DOCKER_NAMESPACE" == "your-dockerhub-username" ]]; then
  echo "[错误] 请设置 DOCKER_NAMESPACE"
  exit 1
fi

DOCKER_REGISTRY="${DOCKER_REGISTRY:-docker.io}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
BACKEND_IMAGE="${DOCKER_REGISTRY}/${DOCKER_NAMESPACE}/talentflow-backend:${IMAGE_TAG}"
FRONTEND_IMAGE="${DOCKER_REGISTRY}/${DOCKER_NAMESPACE}/talentflow-frontend:${IMAGE_TAG}"

echo "==> build"
docker compose -f docker-compose.yml -f docker-compose.registry.yml --env-file "$REGISTRY_ENV" build backend frontend

echo "==> push"
if [[ "$BUILD_ONLY" != "1" ]]; then
  docker push "$BACKEND_IMAGE"
  docker push "$FRONTEND_IMAGE"
  echo "OK: $BACKEND_IMAGE"
  echo "OK: $FRONTEND_IMAGE"
  if [[ "${PRUNE_LOCAL:-0}" == "1" ]]; then
    echo "==> prune local old images (keep: ${IMAGE_TAG})"
    chmod +x scripts/prune-talentflow-images.sh
    ./scripts/prune-talentflow-images.sh \
      --registry "$DOCKER_REGISTRY" \
      --namespace "$DOCKER_NAMESPACE" \
      --keep-tags "${IMAGE_TAG}"
  fi
else
  echo "BUILD_ONLY=1，跳过 push"
fi
