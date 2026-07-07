#!/usr/bin/env python3
"""
向数据库批量插入演示简历（默认 100 条），可重复执行（已存在则跳过）。

用法（在 talentflow-ai-backend-bak 目录）：
  python scripts/seed_resumes.py
  python scripts/seed_resumes.py --count 100 --reindex
  python scripts/seed_resumes.py --cleanup   # 删除本脚本写入的数据
"""
from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core import security
from app.core.database import SessionLocal
from app.models.bootstrap import load_all_models
from app.models.resume import Resume
from app.models.user import User

load_all_models()

SEED_SOURCE = "seed_batch_100"
SEED_USER_PREFIX = "seed_candidate_"
SEED_RESUME_NAME_PREFIX = "seed_resume_"

TITLES = [
    "Python后端工程师",
    "Java开发工程师",
    "Golang开发工程师",
    "前端开发工程师",
    "Vue前端工程师",
    "React前端工程师",
    "算法工程师",
    "机器学习工程师",
    "数据分析师",
    "大数据开发工程师",
    "DevOps工程师",
    "运维工程师",
    "测试开发工程师",
    "Android开发工程师",
    "iOS开发工程师",
    "全栈工程师",
    "区块链开发工程师",
    "嵌入式开发工程师",
    "网络安全工程师",
    "产品经理",
]

SKILL_POOLS = [
    ["Python", "FastAPI", "Django", "MySQL", "Redis", "Docker"],
    ["Java", "Spring Boot", "MyBatis", "Kafka", "MySQL", "Maven"],
    ["Go", "Gin", "gRPC", "Protobuf", "K8s", "Docker"],
    ["JavaScript", "Vue3", "TypeScript", "Webpack", "Node.js", "CSS"],
    ["React", "TypeScript", "Next.js", "Tailwind", "GraphQL"],
    ["PyTorch", "TensorFlow", "NLP", "Python", "Pandas", "Scikit-learn"],
    ["Spark", "Hadoop", "Hive", "Flink", "Python", "SQL"],
    ["Linux", "Shell", "Ansible", "Prometheus", "Grafana", "Nginx"],
    ["Selenium", "Pytest", "JMeter", "Python", "CI/CD"],
    ["Kotlin", "Android", "Jetpack", "Retrofit"],
    ["Swift", "iOS", "UIKit", "CoreData"],
    ["Solidity", "Ethereum", "Web3", "Go"],
    ["C", "C++", "RTOS", "MCU"],
    ["渗透测试", "Wireshark", "Python", "Linux"],
    ["Axure", "需求分析", "数据分析", "SQL"],
]

SURNAMES = list("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜")
GIVEN = list("伟芳娜敏静丽强磊洋勇军杰娟涛明超秀英华文辉力明建国建华志强俊杰磊洋鑫鹏宇浩轩梓涵子涵一诺欣怡")

EDUCATIONS = ["本科 · 计算机科学", "硕士 · 软件工程", "本科 · 电子信息", "硕士 · 人工智能", "本科 · 数学与应用数学"]
COMPANIES = ["星云科技", "未来智能", "蒲公英网络", "云帆信息", "智联软件", "数澜科技", "极客工坊", "蓝海数据"]


def _rand_name(rng: random.Random) -> str:
    return rng.choice(SURNAMES) + rng.choice(GIVEN) + (rng.choice(GIVEN) if rng.random() > 0.6 else "")


def _build_resume_payload(idx: int, user_id: int, rng: random.Random) -> Resume:
    title = TITLES[idx % len(TITLES)]
    skills = SKILL_POOLS[idx % len(SKILL_POOLS)]
    years = rng.randint(1, 12)
    company = rng.choice(COMPANIES)
    name = _rand_name(rng)

    work = (
        f"{company} | {title} | {2026 - years}-至今\n"
        f"- 负责核心业务模块开发与性能优化\n"
        f"- 参与微服务拆分与 CI/CD 流程建设\n"
        f"- 技术栈：{', '.join(skills[:4])}"
    )
    project = (
        f"企业级招聘推荐平台 | 核心开发\n"
        f"- 基于 RAG 的简历职位匹配模块\n"
        f"- 使用 {skills[0]} + Redis 缓存优化检索延迟\n"
        f"- QPS 提升约 40%"
    )
    summary = (
        f"{years} 年{title}经验，熟悉 {', '.join(skills)}。"
        f"具备良好的沟通协作能力与业务理解能力，追求稳定可维护的代码质量。"
    )

    return Resume(
        user_id=user_id,
        name=f"{SEED_RESUME_NAME_PREFIX}{idx:03d}_{name}",
        phone=f"138{rng.randint(10000000, 99999999)}",
        email=f"seed{idx:03d}@demo.talentflow.local",
        title=title,
        education=rng.choice(EDUCATIONS),
        experience_years=years,
        skills=skills,
        summary=summary,
        work_experience=work,
        project_experience=project,
        status="Active",
        is_default=1,
        source=SEED_SOURCE,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def _ensure_candidate_users(db, count: int, rng: random.Random) -> list[int]:
    user_ids: list[int] = []
    for i in range(1, count + 1):
        username = f"{SEED_USER_PREFIX}{i:03d}"
        user = db.query(User).filter(User.username == username).first()
        if not user:
            user = User(
                username=username,
                email=f"{username}@demo.talentflow.local",
                password=security.get_password_hash("candidate123"),
                role=0,
                full_name=f"演示候选人{i:03d}",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        user_ids.append(user.id)
    return user_ids


def seed_resumes(total: int = 100) -> int:
    db = SessionLocal()
    created = 0
    try:
        existing = db.query(Resume).filter(Resume.source == SEED_SOURCE).count()
        if existing >= total:
            print(f"[skip] 已有 {existing} 条种子简历（source={SEED_SOURCE}）")
            return 0

        rng = random.Random(42)
        # 每 5 份简历对应 1 个候选人用户
        user_count = max(20, (total + 4) // 5)
        user_ids = _ensure_candidate_users(db, user_count, rng)

        start_idx = existing + 1
        for i in range(start_idx, total + 1):
            user_id = user_ids[(i - 1) % len(user_ids)]
            resume = _build_resume_payload(i, user_id, rng)
            db.add(resume)
            created += 1
            if created % 20 == 0:
                db.commit()
        db.commit()
        return created
    finally:
        db.close()


def cleanup() -> int:
    db = SessionLocal()
    removed = 0
    try:
        removed = (
            db.query(Resume)
            .filter(Resume.source == SEED_SOURCE)
            .delete(synchronize_session=False)
        )
        db.commit()
        print(f"[cleanup] 删除简历 {removed} 条")
        return removed
    finally:
        db.close()


def maybe_reindex() -> None:
    try:
        from scripts.reindex_resumes import reindex_all

        n = reindex_all()
        print(f"[reindex] 简历向量索引已重建，条目数={n}")
    except Exception as exc:
        print(f"[warn] 重建索引失败（可稍后手动执行 python scripts/reindex_resumes.py）: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="批量插入演示简历")
    parser.add_argument("--count", type=int, default=100, help="目标简历数量")
    parser.add_argument("--reindex", action="store_true", help="插入后重建简历向量索引")
    parser.add_argument("--cleanup", action="store_true", help="删除本脚本插入的数据")
    args = parser.parse_args()

    try:
        if args.cleanup:
            cleanup()
            if args.reindex:
                maybe_reindex()
            return

        n = seed_resumes(args.count)
        print(f"[ok] 新增简历 {n} 条（source={SEED_SOURCE}）")
        if args.reindex or n > 0:
            maybe_reindex()
    except Exception as exc:
        print(f"[fatal] {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
