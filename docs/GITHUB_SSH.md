# 项目目录内 GitHub SSH 密钥

密钥放在 **`.github-keys/`**（已加入 `.gitignore`，不会进 Git）。

## 一键生成

```powershell
cd C:\Users\kzd\Desktop\talentflow-ai
.\scripts\setup-github-ssh.ps1
```

终端会打印 **公钥** → 复制到 https://github.com/settings/keys → **New SSH key**。

## 测试 + 设置远程

```powershell
.\scripts\setup-github-ssh.ps1 -TestOnly
.\scripts\setup-github-ssh.ps1 -SetRemote -GitHubUser kwang-zoed -RepoName talentflow-ai
```

注意仓库名是 `talentflow-ai` 还是 `talenflow-ai`，与 GitHub 上保持一致。

## 推送

```powershell
.\scripts\git-push-ssh.ps1
```

或手动：

```powershell
$env:GIT_SSH_COMMAND = "ssh -i `"$PWD\.github-keys\id_ed25519`" -o IdentitiesOnly=yes"
git push -u origin master
```

## 仍失败时

SSH 也依赖网络访问 GitHub；若超时，需开 **代理/VPN**，或对 Git 配置 `http.proxy`（HTTPS）/ 代理软件 TUN 模式。
