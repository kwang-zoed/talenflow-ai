#!/bin/sh
set -e

MYSQL_HOST="${MYSQL_SERVER:-mysql}"
MYSQL_PORT="${MYSQL_PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-123456}"

echo "[entrypoint] waiting for MySQL at ${MYSQL_HOST}:${MYSQL_PORT}..."

python <<'PY'
import os, sys, time
import pymysql

host = os.getenv("MYSQL_SERVER", "mysql")
port = int(os.getenv("MYSQL_PORT", "3306"))
user = os.getenv("MYSQL_USER", "root")
password = os.getenv("MYSQL_PASSWORD", "123456")

for i in range(60):
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            connect_timeout=3,
        )
        conn.close()
        print("[entrypoint] MySQL is ready")
        sys.exit(0)
    except Exception as exc:
        print(f"[entrypoint] MySQL not ready ({i + 1}/60): {exc}")
        time.sleep(2)

print("[entrypoint] MySQL wait timeout")
sys.exit(1)
PY

exec "$@"
