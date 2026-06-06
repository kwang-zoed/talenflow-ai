#!/usr/bin/env bash
# 从 .env 加载变量（兼容 Windows CRLF，不依赖 python/dotenv）
load_dotenv() {
  local env_file="${1:-.env}"
  if [[ ! -f "$env_file" ]]; then
    echo "load_dotenv: 找不到 $env_file" >&2
    return 1
  fi
  local line key val
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      key="${BASH_REMATCH[1]}"
      val="${BASH_REMATCH[2]}"
      val="${val#\"}"
      val="${val%\"}"
      val="${val#\'}"
      val="${val%\'}"
      export "${key}=${val}"
    fi
  done < "$env_file"
}
