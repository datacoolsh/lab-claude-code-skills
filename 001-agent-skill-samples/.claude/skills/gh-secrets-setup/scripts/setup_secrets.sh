#!/bin/bash
set -e

ENV_FILE="${1:-.env}"
REPO_FLAG=""

# 检查 .env 文件
if [[ ! -f "$ENV_FILE" ]]; then
    echo "错误: 找不到 $ENV_FILE"
    exit 1
fi

# 检查 gh CLI
if ! command -v gh &> /dev/null; then
    echo "错误: 未安装 gh CLI"
    exit 1
fi

# 检查 gh 认证状态
if ! gh auth status &> /dev/null; then
    echo "错误: gh CLI 未认证，请先运行 gh auth login"
    exit 1
fi

# 解析 GITHUB_REPO（如果指定）
GITHUB_REPO=$(grep -E "^GITHUB_REPO=" "$ENV_FILE" | cut -d'=' -f2- | xargs)
if [[ -n "$GITHUB_REPO" ]]; then
    REPO_FLAG="--repo $GITHUB_REPO"
    echo "目标仓库: $GITHUB_REPO"
else
    echo "目标仓库: 当前目录"
fi

# 逐行解析 .env 并创建 secrets
while IFS= read -r line || [[ -n "$line" ]]; do
    # 跳过空行和注释
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    
    # 解析 KEY=value
    KEY=$(echo "$line" | cut -d'=' -f1 | xargs)
    VALUE=$(echo "$line" | cut -d'=' -f2- | xargs)
    
    # 跳过 GITHUB_REPO（不作为 secret）
    [[ "$KEY" == "GITHUB_REPO" ]] && continue
    
    # 处理 SSH_KEY：读取文件内容
    if [[ "$KEY" == "SERVER_SSH_KEY" ]]; then
        KEY_PATH="${VALUE/#\~/$HOME}"
        if [[ -f "$KEY_PATH" ]]; then
            VALUE=$(cat "$KEY_PATH")
        else
            echo "警告: SSH 密钥文件不存在: $VALUE"
            continue
        fi
    fi
    
    # 创建/更新 secret
    echo "设置 secret: $KEY"
    echo "$VALUE" | gh secret set "$KEY" $REPO_FLAG --body -
    
done < "$ENV_FILE"

echo ""
echo "完成！已创建的 secrets:"
gh secret list $REPO_FLAG