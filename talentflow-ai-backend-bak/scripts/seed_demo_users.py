#!/usr/bin/env python3
"""
初始化演示账号（管理员 + HR）。可重复执行，已存在则跳过。

用法（项目根目录 / 服务器 workspace）：
  docker exec talentflow-api python scripts/seed_demo_users.py

若 Hub 镜像尚无本脚本，先拷贝进容器：
  docker cp talentflow-ai-backend-bak/scripts/seed_demo_users.py talentflow-api:/app/scripts/seed_demo_users.py
"""
from __future__ import annotations

import sys

from app.core import security
from app.core.database import SessionLocal
from app.models.user import User

# role: 0 求职者, 1 管理员, 2 HR
SEED_USERS = [
    {
        "username": "admin",
        "email": "admin@talentflow.local",
        "password": "admin12345",
        "role": 1,
        "full_name": "系统管理员",
    },
    {
        "username": "hr",
        "email": "hr@talentflow.local",
        "password": "hr12345678",
        "role": 2,
        "full_name": "HR导师",
    },
]


def seed() -> int:
    db = SessionLocal()
    created = 0
    try:
        for item in SEED_USERS:
            exists = (
                db.query(User)
                .filter(
                    (User.username == item["username"]) | (User.email == item["email"])
                )
                .first()
            )
            if exists:
                print(f"[skip] {item['username']} 已存在 (id={exists.id}, role={exists.role})")
                continue

            user = User(
                username=item["username"],
                email=item["email"],
                password=security.get_password_hash(item["password"]),
                role=item["role"],
                full_name=item["full_name"],
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            created += 1
            role_label = {1: "管理员", 2: "HR"}.get(item["role"], str(item["role"]))
            print(f"[ok] {item['username']} id={user.id} role={role_label}")
        return created
    finally:
        db.close()


def main() -> None:
    try:
        n = seed()
    except Exception as exc:
        print(f"[fatal] {exc}", file=sys.stderr)
        sys.exit(1)

    print("")
    print("默认账号（请登录后尽快修改密码）：")
    print("  管理员  admin / admin12345  -> /admin")
    print("  HR      hr    / hr12345678 -> HR 相关页面")
    print(f"新建 {n} 个用户。")


if __name__ == "__main__":
    main()
