# 认证与角色分流序列图

> 预览：安装 **Markdown Preview Mermaid Support**，打开本文件 `Ctrl+Shift+V`；或复制 `mermaid` 到 [Mermaid Live Editor](https://mermaid.live)。

---

## 30 秒读懂

**登录**：前端 FormData → `POST /auth/login` → 校验密码 → 签发 JWT → 存 `localStorage` + Pinia → 按 `role` 跳转。  
**注册**：`POST /auth/register` → 校验用户名与租户 → 写库。  
**路由守卫**：后续访问受保护路由时，守卫读 token 与 role，拦截越权访问。

角色约定：`0` 求职者 · `1` 平台管理员 · `2` HR/导师。

---

## 登录与角色分流序列图

```mermaid
sequenceDiagram
    autonumber
    actor U as 用户
    participant FE as LoginView
    participant Store as userStore
    participant LS as localStorage
    participant API as FastAPI auth
    participant DB as MySQL
    participant RT as Vue Router

    U->>FE: 输入用户名密码
    FE->>FE: 表单校验
    FE->>API: POST /api/v1/auth/login FormData
    API->>DB: get_user_by_username
    DB-->>API: User 记录
    API->>API: verify_password

    alt 密码错误或用户不存在
        API-->>FE: 401 用户名或密码错误
        FE->>U: ElMessage 提示
    else 账号已封禁
        API-->>FE: 403 账号已被封禁
    else 登录成功
        API->>API: create_access_token 30min
        API-->>FE: access_token + user 含 role
        FE->>LS: token + user JSON
        FE->>Store: setToken setUserInfo
        FE->>U: 登录成功

        alt role = 1 管理员
            FE->>RT: push /admin
            RT->>RT: beforeEach 校验 role=1
            RT->>U: AdminDashboard
        else role = 2 HR
            FE->>RT: push /hr
            RT->>RT: beforeEach 校验 role=2
            RT->>U: HrDashboard
        else role = 0 求职者
            FE->>RT: push /
            RT->>U: /dashboard/tasks
        end
    end
```

---

## 注册序列图

```mermaid
sequenceDiagram
    autonumber
    actor U as 用户
    participant FE as 注册页
    participant API as FastAPI auth
    participant DB as MySQL

    U->>FE: 填写用户名密码租户
    FE->>API: POST /api/v1/auth/register JSON
    API->>DB: get_user_by_username

    alt 用户名已存在
        API-->>FE: 400 用户名已存在
    else 未选 tenant_id
        API-->>FE: 400 必须选择所属租户
    else 注册成功
        API->>DB: create_user
        DB-->>API: 新用户
        API-->>FE: 201 UserCreate
        FE->>U: 跳转登录页
    end
```

---

## 路由守卫序列图（已登录用户访问受保护页）

```mermaid
sequenceDiagram
    autonumber
    participant RT as Vue Router
    participant Store as userStore
    participant LS as localStorage
    participant U as 用户浏览器

    U->>RT: 导航到目标路由 to
    RT->>Store: 读 token role
    RT->>LS: 兜底读 token

    alt 目标为 /login 且已有 token
        RT->>RT: 按 role 重定向
        Note right of RT: 1→/admin 2→/hr 0→/dashboard/tasks
    else requiresAuth 且无 token
        RT->>U: redirect /login
    else 访问 /admin 但 role 不是 1
        RT->>U: redirect /dashboard/tasks
    else 访问 /hr 但 role 不是 2
        RT->>U: redirect /dashboard/tasks
    else 通过
        RT->>U: 渲染目标页面
    end
```

---

## 后续请求的 JWT 校验

受保护 API 通过 `Depends(get_current_user)` 解析 `Authorization: Bearer {token}`，与登录序列独立；失败返回 `401`。

| 角色 | 典型 API 前缀 |
|------|---------------|
| 求职者 | `/api/v1/user/*`、`/api/v1/resume/*` |
| 管理员 | `/api/v1/admin/*` |
| HR/导师 | `/api/v1/mentor/*`、`/api/v1/hr/*` |

---

## 与其它文档

| 文档 | 内容 |
|------|------|
| [use-case.md](./use-case.md) | 登录/注册用例 |
| [function-structure.md](./function-structure.md) | 公共认证模块 |
| **本文件** | 登录注册与前端分流的时序 |

---

## 文档命名约定

- 文件名：`docs/auth-sequence.md`
- 一级标题：`# 认证与角色分流序列图`
