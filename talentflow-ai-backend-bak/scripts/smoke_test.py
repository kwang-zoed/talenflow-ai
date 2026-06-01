#!/usr/bin/env python3
"""TalentFlow 全功能冒烟测试（需本地 MySQL + Redis + Celery Worker + uvicorn）"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field

import httpx
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"))
sys.path.insert(0, ROOT)

BASE = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8000/api/v1")
FRONTEND = os.getenv("SMOKE_FRONTEND_URL", "http://127.0.0.1:5173")
ADMIN_USER = os.getenv("SMOKE_ADMIN_USER", "zhangsan")
ADMIN_PASS = os.getenv("SMOKE_ADMIN_PASS", "123456")
USER_NAME = os.getenv("SMOKE_USER_NAME", "lisi")
USER_PASS = os.getenv("SMOKE_USER_PASS", "123456")
MENTOR_USER = os.getenv("SMOKE_MENTOR_USER", "wangwu")
MENTOR_PASS = os.getenv("SMOKE_MENTOR_PASS", "123456")


@dataclass
class Result:
    name: str
    ok: bool
    detail: str = ""
    skipped: bool = False


@dataclass
class Suite:
    results: list[Result] = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str = "", skipped: bool = False):
        self.results.append(Result(name, ok, detail, skipped))
        mark = "SKIP" if skipped else ("PASS" if ok else "FAIL")
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail else ""))

    def summary(self) -> int:
        passed = sum(1 for r in self.results if r.ok and not r.skipped)
        failed = sum(1 for r in self.results if not r.ok and not r.skipped)
        skipped = sum(1 for r in self.results if r.skipped)
        print("\n" + "=" * 60)
        print(f"合计: {len(self.results)}  通过: {passed}  失败: {failed}  跳过: {skipped}")
        print("=" * 60)
        for r in self.results:
            if not r.ok and not r.skipped:
                print(f"  FAIL: {r.name} — {r.detail}")
        return 1 if failed else 0


def login(client: httpx.Client, username: str, password: str) -> str | None:
    r = client.post(
        f"{BASE}/auth/login",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if r.status_code != 200:
        return None
    body = r.json()
    return body.get("access_token") or body.get("data", {}).get("access_token")


def poll_celery(client: httpx.Client, url: str, headers: dict, timeout: int = 90) -> dict:
    start = time.time()
    delay = 1.5
    while time.time() - start < timeout:
        r = client.get(url, headers=headers)
        data = r.json()
        if isinstance(data, dict) and "status" in data.get("data", {}):
            data = data["data"]
        status = data.get("status")
        if status == "success":
            return data
        if status == "error":
            raise RuntimeError(data.get("message", "Celery task error"))
        time.sleep(delay)
        delay = min(delay * 1.5, 5)
    raise TimeoutError(f"轮询超时: {url}")


def main() -> int:
    suite = Suite()
    print("TalentFlow 冒烟测试")
    print(f"  API: {BASE}")
    print(f"  Frontend: {FRONTEND}")
    print("=" * 60)

    with httpx.Client(timeout=30.0) as client:
        # --- 基础设施 ---
        try:
            r = client.get("http://127.0.0.1:8000/docs")
            suite.add("FastAPI /docs", r.status_code == 200, f"HTTP {r.status_code}")
        except Exception as e:
            suite.add("FastAPI /docs", False, str(e))

        try:
            r = client.get(FRONTEND)
            suite.add("Frontend 首页", r.status_code == 200, f"HTTP {r.status_code}")
        except Exception as e:
            suite.add("Frontend 首页", False, str(e))

        # --- 登录 ---
        admin_token = login(client, ADMIN_USER, ADMIN_PASS)
        suite.add("Admin 登录", admin_token is not None, f"user={ADMIN_USER}")

        user_token = login(client, USER_NAME, USER_PASS)
        suite.add("User 登录", user_token is not None, f"user={USER_NAME}")

        mentor_token = login(client, MENTOR_USER, MENTOR_PASS)
        suite.add("Mentor 登录", mentor_token is not None, f"user={MENTOR_USER}")

        admin_h = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}
        user_h = {"Authorization": f"Bearer {user_token}"} if user_token else {}
        mentor_h = {"Authorization": f"Bearer {mentor_token}"} if mentor_token else {}

        # --- Admin 查询（异步 SQLAlchemy）---
        if admin_token:
            for path, name in [
                ("/admin/users?limit=5", "Admin 用户列表"),
                ("/admin/jobs?limit=5", "Admin 职位列表"),
                ("/admin/resumes?page=1&size=5", "Admin 简历列表"),
                ("/admin/projects?limit=5", "Admin 任务列表"),
                ("/admin/stats/overview", "Admin 仪表盘 overview"),
                ("/admin/stats/resume-trend?days=7", "Admin 简历趋势"),
                ("/admin/stats/job-distribution", "Admin 职位分布"),
            ]:
                r = client.get(f"{BASE}{path}", headers=admin_h)
                suite.add(name, r.status_code == 200, f"HTTP {r.status_code}")

        # --- 废弃同步接口 410 ---
        if admin_token:
            r = client.post(f"{BASE}/admin/jobs/parse", headers=admin_h, files={"file": ("t.txt", b"x")})
            suite.add("废弃 POST /admin/jobs/parse → 410", r.status_code == 410, f"HTTP {r.status_code}")

        if user_token:
            uid = None
            try:
                from jose import jwt
                from app.core.config import settings

                uid = int(jwt.decode(user_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]).get("sub"))
            except Exception:
                pass
            if uid:
                r = client.get(f"{BASE}/user/recommend/{uid}", headers=user_h)
                suite.add("废弃 GET /user/recommend/{id} → 410", r.status_code == 410, f"HTTP {r.status_code}")

        # --- Mentor 查询 ---
        if mentor_token:
            for path, name in [
                ("/mentor/jobs?limit=5", "Mentor 职位列表"),
            ]:
                r = client.get(f"{BASE}{path}", headers=mentor_h)
                suite.add(name, r.status_code == 200, f"HTTP {r.status_code}")
            r = client.post(
                f"{BASE}/mentor/jobs/parse",
                headers=mentor_h,
                files={"file": ("t.txt", b"x")},
            )
            suite.add("废弃 POST /mentor/jobs/parse → 410", r.status_code == 410, f"HTTP {r.status_code}")

        # --- User 查询 ---
        if user_token:
            for path, name in [
                ("/user/job-list?limit=5", "User 职位列表"),
                ("/user/applications", "User 投递记录"),
                ("/user/tasks/?limit=5", "User 实战任务"),
            ]:
                r = client.get(f"{BASE}{path}", headers=user_h)
                suite.add(name, r.status_code == 200, f"HTTP {r.status_code}")

        # --- Celery 推荐（异步）---
        if user_token:
            try:
                from jose import jwt
                from app.core.config import settings

                uid = int(jwt.decode(user_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]).get("sub"))
                r = client.post(
                    f"{BASE}/user/recommend/submit",
                    headers=user_h,
                    json={"user_id": uid, "top_k": 3},
                )
                ok_submit = r.status_code == 200 and (r.json().get("task_id") or r.json().get("data", {}).get("task_id"))
                task_id = r.json().get("task_id") or r.json().get("data", {}).get("task_id")
                suite.add("推荐 submit", ok_submit, f"task_id={task_id}")

                if task_id:
                    data = poll_celery(client, f"{BASE}/user/recommend/status/{task_id}", user_h, timeout=120)
                    n = len(data.get("data") or [])
                    suite.add("推荐 status 轮询", True, f"返回 {n} 条")
            except Exception as e:
                suite.add("推荐 Celery 链路", False, str(e))

        # --- Celery 职位解析 submit（仅提交 + 状态接口可达）---
        if admin_token:
            try:
                content = b"Senior Python Engineer\nCompany: TestCo\nSalary: 20k-30k\nSkills: Python, FastAPI"
                r = client.post(
                    f"{BASE}/admin/jobs/parse/submit",
                    headers=admin_h,
                    files={"file": ("job_test.txt", content, "text/plain")},
                    data={"is_batch": "false"},
                )
                task_id = r.json().get("task_id") or r.json().get("data", {}).get("task_id")
                suite.add("职位解析 submit", r.status_code == 200 and bool(task_id), f"task_id={task_id}")

                if task_id:
                    sr = client.get(f"{BASE}/admin/jobs/parse/status/{task_id}", headers=admin_h)
                    suite.add("职位解析 status 接口", sr.status_code == 200, sr.json().get("status", ""))
            except Exception as e:
                suite.add("职位解析 Celery", False, str(e))

        # --- 简历解析 submit ---
        if admin_token:
            try:
                resume_txt = b"Name: Zhang San\nPhone: 13800000000\nEmail: z@test.com\nSkills: Java, Spring"
                r = client.post(
                    f"{BASE}/admin/resumes/parse/submit",
                    headers=admin_h,
                    files={"file": ("resume_test.txt", resume_txt, "text/plain")},
                )
                task_id = r.json().get("task_id") or r.json().get("data", {}).get("task_id")
                suite.add("简历解析 submit", r.status_code == 200 and bool(task_id), f"task_id={task_id}")
                if task_id:
                    sr = client.get(f"{BASE}/admin/resumes/parse/status/{task_id}", headers=admin_h)
                    suite.add("简历解析 status 接口", sr.status_code == 200, sr.json().get("status", ""))
            except Exception as e:
                suite.add("简历解析 Celery", False, str(e))

        # --- Smart Apply submit（仅验证接口，不等待 LLM 完成）---
        if user_token:
            try:
                jobs = client.get(f"{BASE}/user/job-list?limit=1", headers=user_h).json()
                job_list = jobs if isinstance(jobs, list) else jobs.get("data", jobs.get("items", []))
                if not job_list:
                    suite.add("智能投递 submit", True, "无职位可测，跳过", skipped=True)
                else:
                    job = job_list[0]
                    job_id = job.get("job_id") or job.get("id")
                    payload = {
                        "job_id": str(job_id),
                        "job_title": job.get("title", "test"),
                        "job_description": job.get("description", "test job"),
                        "resume_id": 1,
                        "user_id": 1,
                    }
                    r = client.post(f"{BASE}/user/smart-apply/submit", headers=user_h, json=payload)
                    body = r.json()
                    task_id = body.get("task_id")
                    suite.add(
                        "智能投递 submit",
                        r.status_code in (200, 201) and bool(task_id),
                        f"HTTP {r.status_code} task_id={task_id}",
                    )
                    if task_id:
                        sr = client.get(f"{BASE}/user/smart-apply/status/{task_id}", headers=user_h)
                        suite.add(
                            "智能投递 status 接口",
                            sr.status_code == 200 and sr.json().get("status") in ("processing", "success", "interrupted", "error"),
                            sr.json().get("status", ""),
                        )
            except Exception as e:
                suite.add("智能投递 API", False, str(e))

        # --- 模块 import 检查 ---
        try:
            import subprocess

            p = subprocess.run(
                [sys.executable, os.path.join(ROOT, "check_imports.py")],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            suite.add("check_imports.py", p.returncode == 0, p.stderr.strip()[:120] or "OK")
        except Exception as e:
            suite.add("check_imports.py", False, str(e))

    return suite.summary()


if __name__ == "__main__":
    raise SystemExit(main())
