#!/usr/bin/env bash
# 删除本地旧 talentflow 镜像，保留指定 tag（逗号分隔）
# 例: ./scripts/prune-talentflow-images.sh --namespace kwangzoed --keep-tags latest,abc123

set -euo pipefail

REGISTRY="docker.io"
NAMESPACE=""
KEEP_TAGS="latest"
DRY_RUN=0

usage() {
  echo "Usage: $0 --namespace USER [--registry docker.io] [--keep-tags latest,sha] [--dry-run]"
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --registry) REGISTRY="$2"; shift 2 ;;
    --namespace) NAMESPACE="$2"; shift 2 ;;
    --keep-tags) KEEP_TAGS="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage ;;
    *) echo "Unknown: $1"; usage ;;
  esac
done

[[ -n "$NAMESPACE" ]] || usage

should_keep() {
  local tag="$1"
  IFS=',' read -ra arr <<< "$KEEP_TAGS"
  for k in "${arr[@]}"; do
    k="$(echo "$k" | xargs)"
    [[ "$tag" == "$k" ]] && return 0
  done
  return 1
}

prune_repo() {
  local repo="$1"
  echo "==> Prune ${repo}"
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    ref="${line%% *}"
    tag="${ref##*:}"
    if should_keep "$tag"; then
      echo "  keep  $ref"
      continue
    fi
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "  [dry] rm $ref"
    else
      echo "  rm    $ref"
      docker rmi -f "$ref" 2>/dev/null || true
    fi
  done < <(docker images "$repo" --format '{{.Repository}}:{{.Tag}} {{.ID}}' 2>/dev/null | grep -v '<none>' || true)
}

for name in talentflow-backend talentflow-frontend; do
  prune_repo "${REGISTRY}/${NAMESPACE}/${name}"
done

if [[ "$DRY_RUN" -eq 0 ]]; then
  docker image prune -f >/dev/null 2>&1 || true
  echo "==> docker image prune -f done"
fi
