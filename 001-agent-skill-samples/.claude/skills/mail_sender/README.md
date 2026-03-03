# Mail Sender - Gmail 配置指南

这个技能支持通过 Gmail SMTP 发送邮件。

## 快速开始

### 1. 创建 Gmail 应用专用密码

**重要:** 不能使用你的 Gmail 登录密码,必须使用应用专用密码。

#### 步骤:

1. **启用两步验证**
   - 访问 https://myaccount.google.com/security
   - 找到"两步验证"并启用

2. **创建应用专用密码**
   - 访问 https://myaccount.google.com/apppasswords
   - 选择应用: "邮件"
   - 选择设备: 你的设备类型
   - 点击"生成"
   - 复制生成的 16 位密码 (格式: xxxx xxxx xxxx xxxx)

### 2. 配置环境变量

复制 `.env.example` 为 `.env`:

```bash
cp .env.example .env
```

编辑 `.env` 文件:

```env
SMTP_USER=your_email@gmail.com
SMTP_PASS=your_16_char_app_password
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
```

### 3. 使用示例

```bash
# 发送简单邮件
python mail_sender.py \
  --to recipient@example.com \
  --subject "测试邮件" \
  --text "这是邮件正文"

# 发送带附件的邮件
python mail_sender.py \
  --to recipient@example.com \
  --subject "带附件的邮件" \
  --text "请查收附件" \
  --attach /path/to/file.pdf

# 发送 HTML 邮件
python mail_sender.py \
  --to recipient@example.com \
  --subject "HTML 邮件" \
  --text "纯文本版本" \
  --html "<h1>HTML 版本</h1><p>这是 HTML 邮件</p>"

# 发送给多个收件人
python mail_sender.py \
  --to user1@example.com,user2@example.com \
  --cc user3@example.com \
  --bcc user4@example.com \
  --subject "群发邮件" \
  --text "邮件内容"
```

## Gmail SMTP 配置说明

### 端口选择

Gmail 支持两种端口:

- **587 (推荐)**: 使用 STARTTLS 加密
  - 更广泛的兼容性
  - 先建立未加密连接,然后升级到 TLS

- **465**: 使用 SSL/TLS 加密
  - 从一开始就使用加密连接
  - 某些网络可能会阻止此端口

### 常见问题

#### 1. 认证失败

**错误**: `Authentication failed` 或 `Username and Password not accepted`

**解决方案**:
- 确认使用的是应用专用密码,不是 Gmail 登录密码
- 检查是否启用了两步验证
- 重新生成应用专用密码

#### 2. 连接超时

**错误**: `Connection timed out`

**解决方案**:
- 检查网络连接
- 确认防火墙没有阻止 SMTP 端口 (587 或 465)
- 尝试切换端口 (587 ↔ 465)

#### 3. 邮件发送频率限制

Gmail 有发送频率限制:
- 个人账户: 每天 500 封
- Google Workspace: 每天 2000 封

超出限制会收到错误: `Daily sending quota exceeded`

## 输出格式

脚本输出 JSON 格式的状态信息:

### 成功发送
```json
{
  "ok": true,
  "stage": "sent",
  "message": "email_sent",
  "elapsed_ms": 1234,
  "to": ["recipient@example.com"],
  "cc": [],
  "bcc": [],
  "attachments": []
}
```

### 发送失败
```json
{
  "ok": false,
  "stage": "error",
  "error_type": "SMTPAuthenticationError",
  "error": "Username and Password not accepted",
  "elapsed_ms": 567
}
```

## 安全提示

1. **永远不要**提交 `.env` 文件到版本控制系统
2. `.env` 文件已经在 `.gitignore` 中
3. 定期更换应用专用密码
4. 不要在代码中硬编码密码
5. 使用 `.env.example` 作为配置模板

## 依赖

- Python 3.7+
- yagmail
- python-dotenv

安装依赖:
```bash
pip install -r requirements.txt
```
