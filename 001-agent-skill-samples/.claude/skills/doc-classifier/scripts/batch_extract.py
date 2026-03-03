#!/usr/bin/env python3
"""
batch_extract.py — 批量文档文本提取器（UV 自引导版）
=====================================================

核心加速组件：一次性扫描源目录下所有文档，自动识别文件类型，
调用对应工具链提取文本摘要，输出结构化 JSON 供分类使用。

自引导机制：脚本启动时自动检测虚拟环境，不存在则调用 uv 创建并安装依赖，
然后重新用虚拟环境的 Python 执行自身。用户无需手动配置环境。

用法:
    python batch_extract.py <源文件夹> [--output extracted.json] [--max-chars 2000]

    # 也可以直接通过 uv run 执行（自动处理环境）:
    uv run --project <skill_dir> python scripts/batch_extract.py <源文件夹>
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Windows GBK 终端兼容：强制 stdout/stderr 使用 UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# =============================================================================
# UV 虚拟环境自引导
# =============================================================================
# 核心逻辑：检测当前 Python 是否在虚拟环境中运行，
# 如果不是，则自动创建 .venv 并用 venv 的 Python 重新执行本脚本。

SKILL_DIR = Path(__file__).resolve().parent.parent
VENV_DIR = SKILL_DIR / ".venv"

# --- 跨平台路径适配 ---
# Windows: .venv\Scripts\python.exe  |  Linux/Mac: .venv/bin/python
IS_WINDOWS = sys.platform == "win32"
if IS_WINDOWS:
    VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe"
    VENV_ACTIVATE = VENV_DIR / "Scripts" / "activate.bat"
else:
    VENV_PYTHON = VENV_DIR / "bin" / "python"
    VENV_ACTIVATE = VENV_DIR / "bin" / "activate"

# 所有第三方依赖的包名列表（用于 uv pip install）
REQUIRED_PACKAGES = [
    "pdfplumber",
    "pypdf",
    "pandas",
    "openpyxl",
    "xlrd",
    "markitdown",
    "chardet",
]


def _find_uv():
    """
    定位 uv 可执行文件。
    跨平台搜索：先用 shutil.which()（自动处理 PATH 和 .exe 后缀），
    再检查各平台的常见安装位置。
    """
    uv_path = shutil.which("uv")
    if uv_path:
        return uv_path

    # 各平台常见安装位置
    candidates = [
        Path.home() / ".local" / "bin" / "uv",  # Linux
        Path.home() / ".cargo" / "bin" / "uv",  # Linux/Mac (cargo install)
    ]
    if IS_WINDOWS:
        candidates.extend(
            [
                Path.home() / ".local" / "bin" / "uv.exe",
                Path.home() / ".cargo" / "bin" / "uv.exe",
                Path(os.environ.get("LOCALAPPDATA", ""))
                / "uv"
                / "uv.exe",  # Windows 默认安装位置
                Path(os.environ.get("USERPROFILE", "")) / ".local" / "bin" / "uv.exe",
            ]
        )

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def _install_uv():
    """
    自动安装 uv。
    Windows 使用 PowerShell 安装脚本，Linux/Mac 使用 shell 安装脚本。
    """
    print("[doc-classifier] 未检测到 uv，正在自动安装...", file=sys.stderr)

    if IS_WINDOWS:
        # Windows: 使用 PowerShell 官方安装脚本
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if powershell:
            subprocess.run(
                [
                    powershell,
                    "-ExecutionPolicy",
                    "ByPass",
                    "-c",
                    "irm https://astral.sh/uv/install.ps1 | iex",
                ],
                check=True,
            )
        else:
            print("[doc-classifier] 错误: 需要 PowerShell 来安装 uv", file=sys.stderr)
            print(
                "[doc-classifier] 请手动安装: https://docs.astral.sh/uv/",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        # Linux/Mac: 使用 curl 或 wget
        curl = shutil.which("curl")
        wget = shutil.which("wget")
        if curl:
            subprocess.run(
                "curl -LsSf https://astral.sh/uv/install.sh | sh",
                shell=True,
                check=True,
            )
        elif wget:
            subprocess.run(
                "wget -qO- https://astral.sh/uv/install.sh | sh", shell=True, check=True
            )
        else:
            print("[doc-classifier] 错误: 需要 curl 或 wget 来安装 uv", file=sys.stderr)
            print(
                "[doc-classifier] 请手动安装: https://docs.astral.sh/uv/",
                file=sys.stderr,
            )
            sys.exit(1)

    # 安装后更新 PATH（覆盖所有平台的安装路径）
    extra_paths = [
        str(Path.home() / ".local" / "bin"),
        str(Path.home() / ".cargo" / "bin"),
    ]
    if IS_WINDOWS:
        localappdata = os.environ.get("LOCALAPPDATA", "")
        if localappdata:
            extra_paths.append(str(Path(localappdata) / "uv"))
    os.environ["PATH"] = (
        os.pathsep.join(extra_paths) + os.pathsep + os.environ.get("PATH", "")
    )

    return _find_uv()


def _is_in_venv():
    """判断当前 Python 是否运行在目标虚拟环境中"""
    return (
        hasattr(sys, "prefix")
        and sys.prefix != sys.base_prefix
        and Path(sys.prefix).resolve() == VENV_DIR.resolve()
    )


def bootstrap_venv():
    """
    自引导入口：确保虚拟环境存在且依赖完整，然后用 venv Python 重新执行本脚本。

    执行流程:
    1. 如果已在目标 venv 中运行 → 直接返回，继续执行主逻辑
    2. 如果 venv 不存在 → 用 uv 创建 → 安装依赖
    3. 如果 venv 存在但可能缺依赖 → 跳过重复安装（靠 uv 的缓存加速）
    4. 用 venv 的 Python 重新执行本脚本，传递所有原始参数

    跨平台说明:
    - Windows 上使用 subprocess.run + sys.exit 代替 os.execv（后者在 Windows
      上不会终止父进程，导致双重执行）
    - uv venv 的 --python 参数在 Windows 上使用 "python" 而非 "python3"
      （Windows 不一定有 python3.exe）
    """
    # 已经在目标 venv 里了，直接返回
    if _is_in_venv():
        return

    # 定位或安装 uv
    uv = _find_uv()
    if not uv:
        uv = _install_uv()
    if not uv:
        print("[doc-classifier] 错误: 无法找到或安装 uv", file=sys.stderr)
        sys.exit(1)

    # 创建虚拟环境（如果不存在）
    # Windows 上 python3 命令可能不存在，统一用 "python"（uv 会自动选择最佳版本）
    python_spec = "python" if IS_WINDOWS else "python3"

    if not VENV_PYTHON.exists():
        print(f"[doc-classifier] 📦 创建虚拟环境: {VENV_DIR}")
        subprocess.run([uv, "venv", str(VENV_DIR), "--python", python_spec], check=True)
        print("[doc-classifier] ✅ 虚拟环境创建完成")

        # 新环境必须安装依赖
        print(f"[doc-classifier] 📥 安装依赖（{len(REQUIRED_PACKAGES)} 个包）...")
        subprocess.run(
            [uv, "pip", "install", "--python", str(VENV_PYTHON), "--quiet"]
            + REQUIRED_PACKAGES,
            check=True,
        )
        print("[doc-classifier] ✅ 依赖安装完成")
    else:
        # 环境已存在，快速检查核心依赖是否可用
        check_result = subprocess.run(
            [str(VENV_PYTHON), "-c", "import pdfplumber, pandas, openpyxl"],
            capture_output=True,
        )
        if check_result.returncode != 0:
            # 某些依赖缺失，重新安装（uv 有缓存，秒级完成）
            print("[doc-classifier] 🔄 检测到依赖缺失，正在修复...")
            subprocess.run(
                [uv, "pip", "install", "--python", str(VENV_PYTHON), "--quiet"]
                + REQUIRED_PACKAGES,
                check=True,
            )
            print("[doc-classifier] ✅ 依赖修复完成")

    # 用 venv 的 Python 重新执行本脚本，传递所有原始参数
    # 关键跨平台差异：不使用 os.execv()
    #   - Linux/Mac 上 os.execv 替换当前进程（完美）
    #   - Windows 上 os.execv 启动新进程但不终止旧进程（会导致双重输出）
    # 统一使用 subprocess.run + sys.exit，所有平台行为一致
    print("[doc-classifier] 🔄 切换到虚拟环境执行...")
    result = subprocess.run([str(VENV_PYTHON)] + sys.argv)
    sys.exit(result.returncode)


# --- 执行自引导（在任何第三方 import 之前） ---
bootstrap_venv()

# =============================================================================
# 以下代码保证在虚拟环境中运行，可以安全 import 第三方库
# =============================================================================

import chardet  # noqa: E402


# =============================================================================
# 文件类型映射
# =============================================================================

DOCUMENT_TYPES = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "doc",
    ".xlsx": "xlsx",
    ".xls": "xls",
    ".csv": "csv",
    ".tsv": "tsv",
    ".pptx": "pptx",
    ".ppt": "ppt",
    ".md": "markdown",
    ".txt": "text",
    ".rtf": "rtf",
}

ATTACHMENT_TYPES = {
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".bmp": "image",
    ".svg": "image",
    ".zip": "archive",
    ".rar": "archive",
    ".7z": "archive",
    ".tar": "archive",
    ".gz": "archive",
    ".json": "data",
}


def human_size(size_bytes):
    """字节数 → 人类可读格式"""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def run_cmd(cmd, timeout=30):
    """执行命令行工具，带超时保护"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", -1
    except FileNotFoundError:
        return "", -2


def detect_encoding(filepath):
    """使用 chardet 自动检测文件编码"""
    with open(filepath, "rb") as f:
        raw = f.read(10000)  # 读前10KB足够判断编码
    result = chardet.detect(raw)
    return result.get("encoding", "utf-8") or "utf-8"


# =============================================================================
# 各文件类型的文本提取器
# =============================================================================


def extract_pdf(filepath, max_chars):
    """PDF: pdftotext（快）→ pdfplumber（稳）"""
    text, code = run_cmd(["pdftotext", str(filepath), "-"], timeout=15)
    if code == 0 and text.strip():
        return text[:max_chars], "success", {"method": "pdftotext"}

    try:
        import pdfplumber

        text_parts = []
        with pdfplumber.open(str(filepath)) as pdf:
            for page in pdf.pages[:10]:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
                if sum(len(t) for t in text_parts) >= max_chars:
                    break
        full_text = "\n".join(text_parts)
        if full_text.strip():
            return full_text[:max_chars], "success", {"method": "pdfplumber"}
    except Exception:
        pass

    return "", "failed", {"error": "无法提取PDF文本，可能是扫描件或加密文件"}


def extract_docx(filepath, max_chars):
    """Word .docx: pandoc（快）→ 解压XML（备选）"""
    text, code = run_cmd(
        ["pandoc", str(filepath), "-t", "plain", "--wrap=none"], timeout=15
    )
    if code == 0 and text.strip():
        return text[:max_chars], "success", {"method": "pandoc"}

    try:
        import zipfile
        import re

        with zipfile.ZipFile(str(filepath)) as z:
            if "word/document.xml" in z.namelist():
                xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
                text = re.sub(r"<[^>]+>", " ", xml)
                text = re.sub(r"\s+", " ", text).strip()
                if text:
                    return text[:max_chars], "success", {"method": "xml_extract"}
    except Exception:
        pass

    return "", "failed", {"error": "无法提取Word文档文本"}


def extract_doc(filepath, max_chars):
    """
    Word .doc（旧版）: LibreOffice转docx → 再提取。
    跨平台: LibreOffice 在不同系统上的可执行文件路径不同。
    """
    import tempfile

    # 跨平台定位 LibreOffice 可执行文件
    soffice_cmd = _find_soffice()
    if not soffice_cmd:
        return "", "failed", {"error": "未找到 LibreOffice，无法转换 .doc 文件"}

    with tempfile.TemporaryDirectory() as tmpdir:
        _, code = run_cmd(
            [
                soffice_cmd,
                "--headless",
                "--convert-to",
                "docx",
                "--outdir",
                tmpdir,
                str(filepath),
            ],
            timeout=30,
        )
        if code == 0:
            converted = list(Path(tmpdir).glob("*.docx"))
            if converted:
                return extract_docx(converted[0], max_chars)

    return "", "failed", {"error": "LibreOffice 转换 .doc 失败"}


def _find_soffice():
    """
    跨平台定位 LibreOffice soffice 可执行文件。
    - Linux:   soffice (PATH) 或 /usr/bin/soffice
    - Mac:     /Applications/LibreOffice.app/Contents/MacOS/soffice
    - Windows: C:\\Program Files\\LibreOffice\\program\\soffice.exe
    """
    # 先用 PATH 查找（所有平台通用）
    found = shutil.which("soffice")
    if found:
        return found

    # 各平台特定路径
    if IS_WINDOWS:
        candidates = [
            Path(os.environ.get("PROGRAMFILES", "C:\\Program Files"))
            / "LibreOffice"
            / "program"
            / "soffice.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"))
            / "LibreOffice"
            / "program"
            / "soffice.exe",
        ]
    elif sys.platform == "darwin":
        candidates = [
            Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
        ]
    else:
        candidates = [
            Path("/usr/bin/soffice"),
            Path("/usr/local/bin/soffice"),
            Path("/snap/bin/soffice"),
        ]

    for c in candidates:
        if c.exists():
            return str(c)
    return None

    return "", "failed", {"error": "无法转换.doc文件，需要LibreOffice"}


def extract_xlsx(filepath, max_chars):
    """Excel: 用 pandas 读 sheet名 + 列名 + 前几行（分类不需要完整数据）"""
    try:
        import pandas as pd

        xl = pd.ExcelFile(str(filepath))
        parts = [f"Sheet列表: {', '.join(xl.sheet_names)}"]

        for sheet_name in xl.sheet_names[:5]:
            try:
                df = pd.read_excel(xl, sheet_name=sheet_name, nrows=10)
                parts.append(f"\n--- Sheet: {sheet_name} ---")
                parts.append(f"列名: {', '.join(str(c) for c in df.columns)}")
                parts.append(f"行数(预估): {len(df)}+")
                parts.append(df.head(5).to_string(index=False))
            except Exception:
                parts.append(f"\n--- Sheet: {sheet_name} --- (读取失败)")

        text = "\n".join(parts)
        return (
            text[:max_chars],
            "success",
            {"method": "pandas", "sheet_names": xl.sheet_names},
        )
    except Exception as e:
        return "", "failed", {"error": f"Excel读取失败: {str(e)}"}


def extract_csv(filepath, max_chars):
    """CSV/TSV: 读列名 + 前几行"""
    sep = "\t" if filepath.suffix.lower() == ".tsv" else ","
    for enc in [None, "gbk", "gb2312"]:
        try:
            import pandas as pd

            kwargs = {"sep": sep, "nrows": 20, "on_bad_lines": "skip"}
            if enc:
                kwargs["encoding"] = enc
            df = pd.read_csv(str(filepath), **kwargs)
            parts = [
                f"列名: {', '.join(str(c) for c in df.columns)}",
                f"行数(预估): {len(df)}+",
                df.head(10).to_string(index=False),
            ]
            method = f"pandas{'_' + enc if enc else ''}"
            return "\n".join(parts)[:max_chars], "success", {"method": method}
        except Exception:
            continue
    return "", "failed", {"error": "CSV读取失败（尝试了多种编码）"}


def extract_pptx(filepath, max_chars):
    """PPT: markitdown（快）→ 解压XML（备选）"""
    text, code = run_cmd(
        [str(VENV_PYTHON), "-m", "markitdown", str(filepath)], timeout=20
    )
    if code == 0 and text.strip():
        return text[:max_chars], "success", {"method": "markitdown"}

    try:
        import zipfile
        import re

        texts = []
        with zipfile.ZipFile(str(filepath)) as z:
            slides = sorted(
                f
                for f in z.namelist()
                if f.startswith("ppt/slides/slide") and f.endswith(".xml")
            )
            for sf in slides[:20]:
                xml = z.read(sf).decode("utf-8", errors="ignore")
                t = re.sub(r"<[^>]+>", " ", xml)
                t = re.sub(r"\s+", " ", t).strip()
                if t:
                    texts.append(t)
        text = "\n---\n".join(texts)
        if text.strip():
            return text[:max_chars], "success", {"method": "xml_extract"}
    except Exception:
        pass

    return "", "failed", {"error": "无法提取PPT文本"}


def extract_text_file(filepath, max_chars):
    """纯文本/Markdown: 自动检测编码后读取"""
    encoding = detect_encoding(filepath)
    try:
        text = filepath.read_text(encoding=encoding)
        return (
            text[:max_chars],
            "success",
            {"method": "direct_read", "encoding": encoding},
        )
    except Exception:
        # chardet 检测失败时的回退
        for enc in ["utf-8", "gbk", "latin-1"]:
            try:
                text = filepath.read_text(encoding=enc)
                return (
                    text[:max_chars],
                    "success",
                    {"method": "direct_read", "encoding": enc},
                )
            except Exception:
                continue
    return "", "failed", {"error": "无法以任何编码读取文本文件"}


def extract_archive_listing(filepath):
    """
    压缩包: 列出内部文件名（不解压）。
    跨平台: 优先使用 Python zipfile（所有平台），回退到系统命令。
    """
    # 第一优先级：Python zipfile（全平台可用，无需外部工具）
    try:
        import zipfile

        if zipfile.is_zipfile(str(filepath)):
            with zipfile.ZipFile(str(filepath)) as z:
                names = z.namelist()
                listing = f"包含 {len(names)} 个文件:\n" + "\n".join(names[:30])
                return (
                    listing,
                    "success",
                    {"method": "zipfile", "file_count": len(names)},
                )
    except Exception:
        pass

    # 第二优先级：系统命令（根据平台选择可用工具）
    cli_cmds = [["7z", "l", str(filepath)]]  # 7-Zip 全平台可用
    if not IS_WINDOWS:
        cli_cmds.insert(0, ["unzip", "-l", str(filepath)])  # unzip 仅 Linux/Mac
    else:
        # Windows: tar 命令支持部分格式
        cli_cmds.append(["tar", "-tf", str(filepath)])

    for cmd in cli_cmds:
        text, code = run_cmd(cmd, timeout=10)
        if code == 0 and text.strip():
            return text[:1000], "success", {"method": "cli"}

    return f"压缩包: {filepath.name}", "partial", {"error": "无法列出压缩包内容"}


# =============================================================================
# 提取器路由
# =============================================================================

EXTRACTORS = {
    "pdf": extract_pdf,
    "docx": extract_docx,
    "doc": extract_doc,
    "xlsx": extract_xlsx,
    "xls": extract_xlsx,
    "csv": extract_csv,
    "tsv": extract_csv,
    "pptx": extract_pptx,
    "ppt": extract_pptx,
    "markdown": extract_text_file,
    "text": extract_text_file,
    "rtf": extract_text_file,
}


def is_attachment_candidate(filepath):
    """判断文件是否为附件候选"""
    suffix = filepath.suffix.lower()
    name = filepath.name.lower()
    if suffix in ATTACHMENT_TYPES:
        return True
    if "附件" in name or "attachment" in name:
        return True
    return False


# =============================================================================
# 主流程
# =============================================================================


def scan_and_extract(source_dir, output_path, max_chars=2000):
    """扫描源目录，提取所有文档的文本摘要"""
    source = Path(source_dir).resolve()
    if not source.is_dir():
        print(f"错误: 目录不存在 — {source}", file=sys.stderr)
        sys.exit(1)

    all_files = sorted(
        f for f in source.rglob("*") if f.is_file() and not f.name.startswith(".")
    )

    print(f"📂 扫描目录: {source}")
    print(f"📄 发现文件: {len(all_files)} 个")

    type_counter = defaultdict(int)
    results = []

    for filepath in all_files:
        suffix = filepath.suffix.lower()
        relative_path = str(filepath.relative_to(source))

        file_type = DOCUMENT_TYPES.get(suffix) or ATTACHMENT_TYPES.get(
            suffix, "unknown"
        )
        type_counter[file_type] += 1

        stat = filepath.stat()
        file_info = {
            "path": relative_path,
            "filename": filepath.name,
            "type": file_type,
            "suffix": suffix,
            "size_bytes": stat.st_size,
            "size_human": human_size(stat.st_size),
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "is_attachment_candidate": is_attachment_candidate(filepath),
            "text_preview": "",
            "extract_status": "skipped",
            "extract_error": None,
            "metadata": {},
        }

        if file_type in EXTRACTORS:
            print(f"  📖 {filepath.name} ({file_type})...", end=" ", flush=True)
            try:
                text, status, meta = EXTRACTORS[file_type](filepath, max_chars)
                file_info["text_preview"] = text
                file_info["extract_status"] = status
                file_info["metadata"] = meta
                if status != "success":
                    file_info["extract_error"] = meta.get("error", "未知错误")
                icon = "✅" if status == "success" else "⚠️"
                print(f"{icon} ({len(text)} 字符)")
            except Exception as e:
                file_info["extract_status"] = "error"
                file_info["extract_error"] = str(e)
                print(f"❌ ({str(e)[:60]})")

        elif file_type in ("image", "archive"):
            if file_type == "archive":
                text, status, meta = extract_archive_listing(filepath)
                file_info["text_preview"] = text
                file_info["extract_status"] = status
                file_info["metadata"] = meta
            file_info["is_attachment_candidate"] = True
        else:
            file_info["extract_status"] = "unsupported"
            file_info["extract_error"] = f"不支持的文件类型: {suffix}"

        results.append(file_info)

    # 构建输出 JSON
    output = {
        "source_dir": str(source),
        "scan_time": datetime.now().isoformat(),
        "total_files": len(all_files),
        "summary": dict(type_counter),
        "files": results,
    }

    output_file = Path(output_path)
    output_file.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 打印摘要
    print(f"\n{'=' * 50}")
    print(f"✅ 提取完成!")
    print(f"   总文件数: {len(all_files)}")
    for ftype, count in sorted(type_counter.items(), key=lambda x: -x[1]):
        print(f"   {ftype}: {count} 个")
    success = sum(1 for f in results if f["extract_status"] == "success")
    failed = sum(1 for f in results if f["extract_status"] in ("failed", "error"))
    print(f"   成功: {success}, 失败: {failed}")
    print(f"   输出: {output_file}")

    return output


def main():
    parser = argparse.ArgumentParser(description="批量文档文本提取器（UV自引导）")
    parser.add_argument("source_dir", help="源文件夹路径")
    parser.add_argument(
        "--output",
        "-o",
        default="extracted.json",
        help="输出JSON路径 (默认: extracted.json)",
    )
    parser.add_argument(
        "--max-chars",
        "-m",
        type=int,
        default=2000,
        help="每个文件提取的最大字符数 (默认: 2000)",
    )
    args = parser.parse_args()
    scan_and_extract(args.source_dir, args.output, args.max_chars)


if __name__ == "__main__":
    main()
