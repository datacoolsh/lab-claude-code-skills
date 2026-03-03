---
name: gh-secrets-setup
description: "使用 gh CLI 批量创建/更新 GitHub Actions secrets。从 .env 文件读取服务器、应用、数据库等配置，自动设置为仓库 secrets。支持 SSH 私钥文件路径自动读取。当用户提到 'GitHub secrets'、'gh secret'、'设置 CI/CD secrets'、'配置部署密钥' 时触发此 skill。"
---

# GitHub Actions Secrets 配置 Skill

从 .env 文件批量创建/更新 GitHub Actions repository secrets。

---

## 前置条件

- 已安装 `gh` CLI 并完成认证 (`gh auth login`)
- 当前目录是 git 仓库，或在 .env 中指定 `GITHUB_REPO`
- .env 文件存在且包含要设置的 secrets

---

## 工作流程

### Step 1: 检查环境

1. 验证 `gh` CLI 已安装且已认证
2. 确认目标仓库（当前目录或 GITHUB_REPO 指定）
3. 确认 .env 文件存在

### Step 2: 解析 .env 文件

读取 .env 文件，解析所有 KEY=value 对：
- 忽略空行和 # 开头的注释行
- 处理特殊字段 `SERVER_SSH_KEY`：读取文件路径指向的私钥内容
- 排除 `GITHUB_REPO`（仅用于指定目标仓库，不创建为 secret）

### Step 3: 批量创建/更新 Secrets

对每个解析出的 KEY=value：
```bash
gh secret set KEY --body "value" [--repo owner/repo]
```

- `--body` 用于传递 secret 值
- 如果 .env 中指定了 `GITHUB_REPO`，添加 `--repo` 参数
- `gh secret set` 自动处理创建/更新逻辑

### Step 4: 验证结果
```bash
gh secret list [--repo owner/repo]
```

列出已创建的 secrets 确认设置成功。

---

## 脚本位置

执行脚本: `scripts/setup_secrets.sh`

---

## 使用示例

1. 复制 .env.sample 为 .env
2. 填写实际配置值
3. 运行: `bash scripts/setup_secrets.sh`

---

## 注意事项

- SSH 私钥路径支持 `~` 展开
- 所有值都会被 trim 处理
- 已存在的 secrets 会被覆盖更新
- 敏感信息不会在终端输出