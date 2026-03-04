---
name: check-uv-setup
description: 当执行python脚本时、使用uv执行python脚本时、当前环境中没有uv，执行检查uv的设置。
---

## 概述

检查当前环境是否已安装 uv，若未安装则引导用户完成安装；同时提供项目初始化和脚本执行的标准流程。

## 检查 uv 是否已安装

```bash
uv --version
```

若命令不存在，则按以下步骤安装。

## 安装 uv

**macOS / Linux（推荐）：**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows（PowerShell）：**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**包管理器（可选）：**
```bash
# Homebrew (macOS)
brew install uv

# WinGet (Windows)
winget install --id=astral-sh.uv -e
```

安装后验证：
```bash
uv --version
uv self update   # 通过独立安装器安装时，可自更新
```

## 新项目初始化

```bash
uv init --python 3.12      # 创建 pyproject.toml、.python-version、main.py
uv sync                     # 创建 .venv 并同步依赖
```

## 依赖管理

```bash
uv add requests             # 添加依赖（自动更新 pyproject.toml 和 uv.lock）
uv add --dev pytest         # 添加开发依赖
uv remove requests          # 移除依赖
uv lock --upgrade-package requests   # 升级指定包
uv sync                     # 同步环境（与 pyproject.toml 保持一致）
```

> **注意**：`uv.lock` 由 uv 自动管理，应纳入版本控制，不要手动编辑。

## 运行脚本

优先使用 `uv run`，它会在执行前自动验证依赖同步状态：

```bash
uv run python script.py         # 推荐：自动激活虚拟环境
uv run script.py                # 对有 shebang 的脚本
uv run --with rich script.py    # 临时添加依赖后运行
```

**绝对不要使用**裸 `python script.py`（可能命中系统 Python）。

## 独立脚本（PEP 723 内联元数据）

对于独立脚本，推荐使用内联依赖声明：

```bash
uv add --script example.py 'requests<3' 'rich'
```

自动在脚本头部生成：
```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "requests<3",
#   "rich",
# ]
# ///
```

锁定脚本依赖（可重现执行）：
```bash
uv lock --script example.py
```
