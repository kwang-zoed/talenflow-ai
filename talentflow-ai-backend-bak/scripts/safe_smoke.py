"""无需登录凭证的安全冒烟检查"""
import httpx

client = httpx.Client(timeout=15)
checks = [
    ("FastAPI /docs", "GET", "http://127.0.0.1:8000/docs", None, 200),
    ("OpenAPI schema", "GET", "http://127.0.0.1:8000/openapi.json", None, 200),
    ("Frontend", "GET", "http://127.0.0.1:5173/", None, 200),
    ("Admin 未授权拦截", "GET", "http://127.0.0.1:8000/api/v1/admin/users", None, 401),
    ("User 未授权拦截", "GET", "http://127.0.0.1:8000/api/v1/user/job-list", None, 401),
    ("废弃推荐 401/403", "GET", "http://127.0.0.1:8000/api/v1/user/recommend/1", None, {401, 403}),
]

passed = failed = 0
for name, method, url, _, expect in checks:
    r = client.request(method, url)
    ok = r.status_code in expect if isinstance(expect, set) else r.status_code == expect
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {name} — HTTP {r.status_code}")
    passed += ok
    failed += not ok

print(f"\n通过 {passed}/{passed+failed}")
raise SystemExit(1 if failed else 0)
