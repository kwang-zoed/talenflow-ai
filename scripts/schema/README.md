# 将完整库结构 SQL 放在此目录（提交到 Git 后，CI/CD 首次部署会自动导入一次）

```bash
# 从本机复制（只需做一次，然后 git add commit）
cp /path/to/dandelion_tribe_schema.sql scripts/schema/dandelion_tribe_schema.sql
```

首次 SSH 部署流程：

1. `bootstrap-db.sh` 发现无 `users` 表 → 导入本文件（仅一次）
2. `users` 表为空 → 创建 `admin` / `hr`
3. 之后每次 git push 部署：**跳过**，数据在 `mysql_data` volume 中持久化

**切勿** `docker compose down -v`（会删除 volume 和数据）。
