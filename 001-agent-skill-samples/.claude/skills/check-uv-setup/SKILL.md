---
name: check-uv-setup
description: 当执行python脚本时、使用uv执行python脚本时、当前环境中没有uv，执行检查uv的设置。
---

## 概述



## 安装uv
linux/macOS系统：
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

windows系统：
```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## uv初始化虚拟环境
示例：
```bash
uv python install 3.12
uv python pin 3.12
uv venv {project_root_path}/.venv
uv sync
```
如果当前环境已激活：
```bash
uv add --active "mcp[cli]" httpx
uv sync --active
```
