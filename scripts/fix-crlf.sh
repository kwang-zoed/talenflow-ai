#!/usr/bin/env bash
# 服务器上修复 Windows CRLF：./scripts/fix-crlf.sh
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

fix_file() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  sed -i 's/\r$//' "$f"
  echo "fixed: $f"
}

for f in .env .env.registry scripts/*.sh scripts/lib/*.sh; do
  fix_file "$f"
done

echo "完成。可执行: chmod +x scripts/*.sh && ./scripts/init-db.sh dandelion_tribe_schema.sql"
