---
name: mail-sender
description: 当用户需要发送邮件时触发该技能，并返回邮件发送结果
---

## 概述
技能用于发送邮件，并返回邮件发送结果。

## 环境配置
1. 检查虚拟环境.venv是否存在，如果不存在，则在项目根目录下执行命令：`uv init --name skills`
2. 激活虚拟环境：`source .venv/bin/activate`;windows系统，则执行命令：`.venv\Scripts\activate.bat`
3. 安装依赖包：`uv add yagmail`

## 技能流程
1. 检查 `.env` 文件是否存在，如不存在，复制 `.env.example` 为 `.env` 并配置发件人信息
2. 获取用户输入的邮件内容（收件人、主题、正文等）
3. 调用脚本发送邮件：`uv run python mail_sender.py --to ... --subject ... --text ...`
4. 返回邮件发送结果给用户

## 邮件表单

发送邮件时，需要收集以下信息：

| 字段 | 参数名 | 必填 | 说明 |
|------|--------|------|------|
| 收件人 | to | ✅ | 收件人邮箱地址，支持多个（逗号分隔或重复使用） |
| 主题 | subject | ✅ | 邮件主题 |
| 正文 | text | ✅ | 邮件正文（纯文本格式） |
| HTML正文 | html | ❌ | HTML 格式的邮件正文（可选） |
| 抄送 | cc | ❌ | 抄送收件人，支持多个 |
| 密送 | bcc | ❌ | 密送收件人，支持多个 |
| 附件 | attach | ❌ | 附件文件路径，支持多个 |

## 发件人配置（.env）

发件人信息从 `.env` 文件读取，需要配置以下环境变量：

```env
# SMTP 服务器配置
SMTP_HOST=smtp.gmail.com      # SMTP 服务器地址
SMTP_PORT=587                  # 端口（587=STARTTLS, 465=SSL）
SMTP_USER=your_email@gmail.com # 发件人邮箱地址
SMTP_PASS=your_app_password    # 应用专用密码（非登录密码）
SMTP_TIMEOUT=30                # 连接超时时间（秒）
```

**Gmail 用户注意：**
- `SMTP_PASS` 必须使用[应用专用密码](https://myaccount.google.com/apppasswords)，不是 Gmail 登录密码
- 需要先启用两步验证才能创建应用专用密码

## 调用示例

```bash
# 基本用法
uv run python mail_sender.py \
  --to "recipient@example.com" \
  --subject "测试邮件" \
  --text "这是邮件正文"

# 带附件
uv run python mail_sender.py \
  --to "recipient@example.com" \
  --subject "报告" \
  --text "请查收附件" \
  --attach "/path/to/report.pdf"

# 多收件人 + 抄送 + 密送
uv run python mail_sender.py \
  --to "a@example.com,b@example.com" \
  --cc "cc@example.com" \
  --bcc "bcc@example.com" \
  --subject "会议通知" \
  --text "会议内容..."
```

## 返回结果

脚本输出 JSON 格式的结果：

**成功：**
```json
{"ok": true, "stage": "sent", "message": "email_sent", "elapsed_ms": 1234, "to": ["recipient@example.com"]}
```

**失败：**
```json
{"ok": false, "stage": "error", "error_type": "SMTPAuthenticationError", "error": "认证失败"}
```
