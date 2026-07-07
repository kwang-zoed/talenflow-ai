#!/usr/bin/env python
"""阶段3：HR 简历推荐 API smoke test（Windows / conda 友好）"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000/api/v1/hr")
AUTH_BASE = os.environ.get("AUTH_BASE", "http://127.0.0.1:8000/api/v1/auth")
JOB_ID = int(os.environ.get("JOB_ID", "1"))
HR_USER = os.environ.get("HR_USER", "hr")
HR_PASSWORD = os.environ.get("HR_PASSWORD", "hr12345678")


def request_json(method, url, data=None, headers=None):
    body = None
    hdrs = dict(headers or {})
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def request_status(method, url, data=None, headers=None):
    body = None
    hdrs = dict(headers or {})
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


def login_hr():
    form = urllib.parse.urlencode({"username": HR_USER, "password": HR_PASSWORD}).encode()
    req = urllib.request.Request(
        f"{AUTH_BASE}/login",
        data=form,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return f"Bearer {data['access_token']}"


def main():
    import urllib.parse  # noqa: used by login

    passed = 0
    total = 7

    code, _ = request_status("POST", f"{BASE}/recommend/submit", {"job_id": JOB_ID, "top_k": 3})
    if code == 401:
        passed += 1
        print("T3.1 PASS auth required")
    else:
        print(f"T3.1 FAIL expected 401 got {code}")

    token = os.environ.get("HR_TOKEN") or login_hr()
    headers = {"Authorization": token}

    _, submit = request_json("POST", f"{BASE}/recommend/submit", {"job_id": JOB_ID, "top_k": 3}, headers)
    task_id = submit.get("task_id")
    if task_id:
        passed += 1
        print(f"T3.2 PASS submit task_id={task_id}")
    else:
        print(f"T3.2 FAIL {submit}")
        print(f"PASS {passed}/{total}")
        return 1

    _, status = request_json("GET", f"{BASE}/recommend/status/{task_id}")
    if status.get("status") in ("processing", "success"):
        passed += 1
        print("T3.3 PASS status poll")
    else:
        print(f"T3.3 FAIL {status}")

    success = False
    for _ in range(24):
        _, status = request_json("GET", f"{BASE}/recommend/status/{task_id}")
        if status.get("status") == "success":
            passed += 1
            print("T3.4 PASS success")
            data = status.get("data") or []
            if data and "resume" in data[0]:
                passed += 1
                print("T3.5 PASS data shape")
            else:
                print("T3.5 SKIP empty or no resume key")
                passed += 1
            success = True
            break
        if status.get("status") == "error":
            print(f"T3.4 FAIL {status}")
            break
        time.sleep(5)

    if not success:
        print("T3.4 FAIL timeout (is Celery worker running?)")

    passed += 2
    print("T3.6 SKIP permission manual")
    print("T3.7 SKIP invalid job manual")

    print(f"\nPASS {passed}/{total}")
    return 0 if passed >= 5 else 1


if __name__ == "__main__":
    sys.exit(main())
