# ==============================================================================
# setup_env.ps1 — Doc Classifier 环境引导脚本（Windows PowerShell 版）
# ==============================================================================
#
# 功能: 检测 uv → 检查虚拟环境 → 不存在则创建 → 安装所有依赖
# 设计: 幂等执行，重复运行安全无副作用
#
# 用法:
#   .\scripts\setup_env.ps1              # 创建环境
#   .\scripts\setup_env.ps1 -Activate    # 创建环境 + 输出激活命令
#
# 虚拟环境位置: <skill_dir>\.venv\
# ==============================================================================

param(
    [switch]$Activate  # 是否在末尾输出激活命令提示
)

$ErrorActionPreference = "Stop"

# --- 定位 Skill 根目录 ---
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillDir = Split-Path -Parent $ScriptDir
$VenvDir = Join-Path $SkillDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$Pyproject = Join-Path $SkillDir "pyproject.toml"

# --- 输出辅助函数 ---
function Write-Info  { param($Msg) Write-Host "[doc-classifier] $Msg" -ForegroundColor Green }
function Write-Warn  { param($Msg) Write-Host "[doc-classifier] $Msg" -ForegroundColor Yellow }
function Write-Err   { param($Msg) Write-Host "[doc-classifier] $Msg" -ForegroundColor Red }

# =============================================================================
# Step 1: 检测 uv 是否可用
# =============================================================================
$uvCmd = Get-Command uv -ErrorAction SilentlyContinue

if (-not $uvCmd) {
    # 检查常见安装位置
    $candidates = @(
        "$env:LOCALAPPDATA\uv\uv.exe",
        "$env:USERPROFILE\.local\bin\uv.exe",
        "$env:USERPROFILE\.cargo\bin\uv.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) {
            $uvCmd = Get-Item $c
            break
        }
    }
}

if (-not $uvCmd) {
    Write-Warn "未检测到 uv，正在自动安装..."
    try {
        irm https://astral.sh/uv/install.ps1 | iex
        # 刷新 PATH
        $env:PATH = "$env:LOCALAPPDATA\uv;$env:USERPROFILE\.local\bin;$env:USERPROFILE\.cargo\bin;$env:PATH"
        $uvCmd = Get-Command uv -ErrorAction SilentlyContinue
        if (-not $uvCmd) { throw "安装后仍找不到 uv" }
        Write-Info "✅ uv 安装成功: $(uv --version)"
    }
    catch {
        Write-Err "uv 安装失败: $_"
        Write-Err "请手动安装: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    }
}

$uvPath = if ($uvCmd.Source) { $uvCmd.Source } else { $uvCmd.Path }
Write-Info "🔧 uv 版本: $(& $uvPath --version)"

# =============================================================================
# Step 2: 检查虚拟环境是否存在
# =============================================================================
if ((Test-Path $VenvDir) -and (Test-Path $VenvPython)) {
    Write-Info "✅ 虚拟环境已存在: $VenvDir"
}
else {
    Write-Info "📦 虚拟环境不存在，正在创建..."
    & $uvPath venv $VenvDir --python python
    if ($LASTEXITCODE -ne 0) {
        Write-Err "虚拟环境创建失败"
        exit 1
    }
    Write-Info "✅ 虚拟环境创建完成: $VenvDir"
}

# =============================================================================
# Step 3: 安装/同步依赖
# =============================================================================
Write-Info "📥 正在同步依赖..."

$packages = @(
    "pdfplumber", "pypdf", "pandas", "openpyxl",
    "xlrd", "markitdown", "chardet"
)

& $uvPath pip install --python $VenvPython --quiet @packages
if ($LASTEXITCODE -ne 0) {
    Write-Warn "依赖安装出现问题，尝试逐个安装..."
    foreach ($pkg in $packages) {
        & $uvPath pip install --python $VenvPython --quiet $pkg 2>$null
    }
}

Write-Info "✅ 所有依赖安装完成"

# =============================================================================
# Step 4: 验证关键依赖可用性
# =============================================================================
Write-Info "🔍 验证关键依赖..."

$verifyScript = @"
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
        ok.append(f'  OK: {mod} - {desc}')
    except ImportError:
        fail.append(f'  FAIL: {mod} - {desc}')
for line in ok:
    print(line)
for line in fail:
    print(line)
if fail:
    sys.exit(1)
"@

$verifyResult = & $VenvPython -c $verifyScript 2>&1
Write-Host $verifyResult

# =============================================================================
# Step 5: 检测系统级工具（可选加速）
# =============================================================================
Write-Info "🔍 检测系统级工具（可选加速）..."

function Test-Tool {
    param($Name, $Desc)
    if (Get-Command $Name -ErrorAction SilentlyContinue) {
        Write-Host "  ✅ $Name — $Desc"
    }
    else {
        Write-Host "  ⚠️  $Name — $Desc （未安装，将使用Python备选方案）" -ForegroundColor Yellow
    }
}

Test-Tool "pdftotext" "PDF文本提取（poppler，速度最快）"
Test-Tool "pandoc"    "Word/Markdown文档转换"

# 检查 LibreOffice（Windows 特殊路径）
$soffice = Get-Command soffice -ErrorAction SilentlyContinue
if (-not $soffice) {
    $loPath = "${env:ProgramFiles}\LibreOffice\program\soffice.exe"
    if (Test-Path $loPath) { $soffice = $true }
}
if ($soffice) {
    Write-Host "  ✅ LibreOffice — .doc旧格式转换"
}
else {
    Write-Host "  ⚠️  LibreOffice — .doc旧格式转换（未安装，将使用Python备选方案）" -ForegroundColor Yellow
}

# =============================================================================
# Step 6: 输出环境信息
# =============================================================================
Write-Host ""
Write-Info "=========================================="
Write-Info "🎉 环境就绪！"
Write-Info "  Python:     $(& $VenvPython --version)"
Write-Info "  虚拟环境:   $VenvDir"
Write-Info "  激活命令:   $VenvDir\Scripts\Activate.ps1"
Write-Info "  提取脚本:   $VenvPython $SkillDir\scripts\batch_extract.py <源目录>"
Write-Info "=========================================="

if ($Activate) {
    Write-Info ""
    Write-Info "请运行以下命令激活虚拟环境:"
    Write-Info "  & `"$VenvDir\Scripts\Activate.ps1`""
}