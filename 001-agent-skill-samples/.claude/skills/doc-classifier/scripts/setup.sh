#!/usr/bin/env bash
# ==============================================================================
# setup_env.sh — Doc Classifier 环境引导脚本（Linux / macOS）
# ==============================================================================
#
# 功能: 检测 uv → 检查虚拟环境 → 不存在则创建 → 安装所有依赖
# 设计: 幂等执行，重复运行安全无副作用
# 平台: Linux 和 macOS（Windows 请使用 setup_env.ps1 或 setup_env.bat）
#
# 用法:
#   source scripts/setup_env.sh          # 创建环境 + 激活（推荐）
#   bash scripts/setup_env.sh            # 仅创建环境，不激活
#
# 虚拟环境位置: <skill_dir>/.venv/
# ==============================================================================

set -euo pipefail

# --- 定位 Skill 根目录（相对于此脚本的位置） ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$SKILL_DIR/.venv"
PYPROJECT="$SKILL_DIR/pyproject.toml"

# --- 检测操作系统 ---
OS_TYPE="$(uname -s)"
case "$OS_TYPE" in
    Linux*)  PLATFORM="linux";;
    Darwin*) PLATFORM="macos";;
    MINGW*|MSYS*|CYGWIN*)
        echo "[doc-classifier] 检测到 Windows 环境（Git Bash / MSYS2 / Cygwin）"
        echo "[doc-classifier] 建议使用 PowerShell 脚本: scripts\\setup_env.ps1"
        echo "[doc-classifier] 或者直接运行: python scripts/batch_extract.py <源目录>"
        echo "[doc-classifier] （脚本内置自引导机制，会自动处理环境）"
        echo "[doc-classifier] 继续尝试在当前 shell 中执行..."
        PLATFORM="windows_compat";;
    *)
        echo "[doc-classifier] 未知操作系统: $OS_TYPE，按 Linux 方式处理"
        PLATFORM="linux";;
esac

# --- 颜色输出 ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[doc-classifier]${NC} $*"; }
warn()  { echo -e "${YELLOW}[doc-classifier]${NC} $*"; }
error() { echo -e "${RED}[doc-classifier]${NC} $*" >&2; }

info "📌 操作系统: $OS_TYPE ($PLATFORM)"

# =============================================================================
# Step 1: 检测 uv 是否可用
# =============================================================================

# macOS 用户可能通过 Homebrew 安装 uv，补充 Homebrew 路径
if [ "$PLATFORM" = "macos" ]; then
    # Homebrew 在 Apple Silicon 和 Intel Mac 上路径不同
    export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
else
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

if ! command -v uv &>/dev/null; then
    warn "未检测到 uv，正在自动安装..."
    if command -v curl &>/dev/null; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    elif command -v wget &>/dev/null; then
        wget -qO- https://astral.sh/uv/install.sh | sh
    else
        error "无法安装 uv: 需要 curl 或 wget"
        error "请手动安装: https://docs.astral.sh/uv/getting-started/installation/"
        if [ "$PLATFORM" = "macos" ]; then
            error "macOS 用户也可以使用: brew install uv"
        fi
        exit 1
    fi
    # 重新加载 PATH
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    if ! command -v uv &>/dev/null; then
        error "uv 安装失败，请手动安装后重试"
        exit 1
    fi
    info "✅ uv 安装成功: $(uv --version)"
fi

info "🔧 uv 版本: $(uv --version)"

# =============================================================================
# Step 2: 检查虚拟环境是否存在
# =============================================================================
if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/python" ]; then
    info "✅ 虚拟环境已存在: $VENV_DIR"
    VENV_EXISTED=true
else
    info "📦 虚拟环境不存在，正在创建..."
    # macOS 和 Linux 都用 python3（macOS 自带的 python 命令可能指向旧版 Python 2）
    uv venv "$VENV_DIR" --python python3
    info "✅ 虚拟环境创建完成: $VENV_DIR"
    VENV_EXISTED=false
fi

PYTHON="$VENV_DIR/bin/python"

# =============================================================================
# Step 3: 安装/同步依赖
# =============================================================================
info "📥 正在同步依赖..."

uv pip install \
    --python "$PYTHON" \
    --quiet \
    pdfplumber pypdf pandas openpyxl xlrd markitdown chardet \
    || {
        warn "批量安装失败，尝试逐个安装..."
        for pkg in pdfplumber pypdf pandas openpyxl xlrd markitdown chardet; do
            uv pip install --python "$PYTHON" --quiet "$pkg" 2>/dev/null || \
                warn "  ⚠️ $pkg 安装失败（对应文件类型将使用备选方案）"
        done
    }

info "✅ 依赖安装完成"

# =============================================================================
# Step 4: 验证关键依赖可用性
# =============================================================================
info "🔍 验证关键依赖..."

VERIFY_RESULT=$($PYTHON -c "
import sys
deps = {
    'pdfplumber':  'PDF文本提取',
    'pypdf':       'PDF元数据',
    'pandas':      'Excel/CSV数据读取',
    'openpyxl':    'XLSX读写引擎',
    'xlrd':        'XLS旧版支持',
    'markitdown':  'Office文档转Markdown',
    'chardet':     '编码检测',
}
ok, fail = [], []
for mod, desc in deps.items():
    try:
        __import__(mod)
        ok.append(f'  ✅ {mod} — {desc}')
    except ImportError:
        fail.append(f'  ❌ {mod} — {desc}')
for line in ok:
    print(line)
for line in fail:
    print(line)
if fail:
    sys.exit(1)
" 2>&1) || {
    warn "部分依赖验证失败:"
    echo "$VERIFY_RESULT"
    warn "脚本仍可运行，缺失的依赖将使用备选方案"
}

echo "$VERIFY_RESULT"

# =============================================================================
# Step 5: 检测系统级工具（可选加速）
# =============================================================================
info "🔍 检测系统级工具（可选加速）..."

check_tool() {
    if command -v "$1" &>/dev/null; then
        echo -e "  ✅ $1 — $2"
    else
        echo -e "  ⚠️  $1 — $2 （未安装，将使用Python备选方案）"
    fi
}

check_tool "pdftotext" "PDF文本提取（poppler-utils，速度最快）"
check_tool "pandoc"    "Word/Markdown文档转换"

# LibreOffice: macOS 路径与 Linux 不同
if command -v soffice &>/dev/null; then
    echo -e "  ✅ soffice — LibreOffice，.doc旧格式转换"
elif [ "$PLATFORM" = "macos" ] && [ -f "/Applications/LibreOffice.app/Contents/MacOS/soffice" ]; then
    echo -e "  ✅ LibreOffice.app — .doc旧格式转换（macOS应用）"
else
    echo -e "  ⚠️  soffice — LibreOffice，.doc旧格式转换（未安装）"
    if [ "$PLATFORM" = "macos" ]; then
        echo -e "      提示: brew install --cask libreoffice"
    else
        echo -e "      提示: sudo apt install libreoffice-common (Ubuntu/Debian)"
    fi
fi

# =============================================================================
# Step 6: 输出环境信息
# =============================================================================
echo ""
info "=========================================="
info "🎉 环境就绪！"
info "  平台:       $OS_TYPE ($PLATFORM)"
info "  Python:     $($PYTHON --version)"
info "  虚拟环境:   $VENV_DIR"
info "  激活命令:   source $VENV_DIR/bin/activate"
info "  提取脚本:   $PYTHON $SKILL_DIR/scripts/batch_extract.py <源目录>"
info "=========================================="

# --- 如果是 source 方式调用，自动激活虚拟环境 ---
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    source "$VENV_DIR/bin/activate"
    info "✅ 虚拟环境已自动激活"
fi