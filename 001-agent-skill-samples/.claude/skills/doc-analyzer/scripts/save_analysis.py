#!/usr/bin/env python3
"""
save_analysis.py — 分析结果持久化工具
=======================================

将文档分析结果保存为结构化的 Markdown 文件，存储在 references/history/ 目录下，
按日期和文档类型组织。这确保每次分析的成果不会随着会话结束而丢失，
可以作为后续分析的参考和团队知识资产。

存储路径规则:
    references/history/<YYYY-MM-DD>/<文档类型>_<标题>.md

示例:
    references/history/2025-03-01/周例会_Q1产品规划与资源协调.md
    references/history/2025-03-01/政策文件_关于加强数据安全管理的通知.md
    references/history/2025-01-15/工作报告_研发部2024年度总结.md

用法:
    # 方式一：通过命令行参数
    python save_analysis.py --type 会议纪要 --title "Q1产品规划讨论" --content "分析内容..."

    # 方式二：从 stdin 读取分析内容（适合长文本）
    echo "分析内容..." | python save_analysis.py --type 会议纪要 --title "Q1产品规划讨论" --stdin

    # 方式三：从文件读取分析内容
    python save_analysis.py --type 会议纪要 --title "Q1产品规划讨论" --from-file /tmp/analysis.md

    # 指定日期（默认使用当天）
    python save_analysis.py --type 周例会 --title "Sprint回顾" --date 2025-02-28 --content "..."

    # 查看历史记录
    python save_analysis.py --list
    python save_analysis.py --list --date 2025-03-01
    python save_analysis.py --list --type 会议纪要
"""

import argparse
import hashlib
import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path


# =============================================================================
# 路径常量
# =============================================================================

SKILL_DIR = Path(__file__).resolve().parent.parent
HISTORY_DIR = SKILL_DIR / "references" / "history"


# =============================================================================
# 文档类型 → 文件名前缀映射
# =============================================================================
# 用户可以使用中文类型名或英文模板名，脚本统一映射为中文前缀

TYPE_ALIASES = {
    # 中文名 → 中文前缀（直接使用）
    "会议纪要": "会议纪要",
    "周例会": "周例会",
    "月会": "月会",
    "专题会议": "专题会议",
    "评审会": "评审会",
    "启动会": "启动会",
    "领导讲话": "领导讲话",
    "政策文件": "政策文件",
    "工作报告": "工作报告",
    "周报": "周报",
    "月报": "月报",
    "季报": "季报",
    "年报": "年报",
    "方案规划": "方案规划",
    "数据分析": "数据分析",
    "数据分析报告": "数据分析报告",
    "通用": "通用",
    # 英文模板名 → 中文前缀
    "meeting_minutes": "会议纪要",
    "leadership_speech": "领导讲话",
    "policy_document": "政策文件",
    "work_report": "工作报告",
    "plan_proposal": "方案规划",
    "data_analysis": "数据分析报告",
    "general": "通用",
}


# =============================================================================
# 文件名处理
# =============================================================================


def sanitize_filename(name: str) -> str:
    r"""
    将用户输入的标题转换为安全的文件名。

    处理策略:
    - 保留中文字符（中文在文件名中完全合法）
    - 移除 / \ : * ? " < > | 等文件系统保留字符
    - 将连续空白替换为单个下划线
    - 去除首尾空白和特殊字符
    - 截断到合理长度（80 字符，避免 Windows 的 260 字符路径限制）
    """
    # 移除文件系统不安全的字符
    unsafe_chars = r'[/\\:*?"<>|\r\n\t]'
    name = re.sub(unsafe_chars, "", name)

    # 将空白序列替换为下划线
    name = re.sub(r"\s+", "_", name.strip())

    # 移除首尾的特殊字符（点、下划线等）
    name = name.strip("._- ")

    # 截断到合理长度
    if len(name) > 80:
        name = name[:80].rstrip("_")

    # 如果处理后为空，使用默认名称
    if not name:
        name = "untitled"

    return name


def resolve_type_prefix(doc_type: str) -> str:
    """
    将用户输入的文档类型解析为文件名前缀。
    支持中文名称和英文模板标识符。
    """
    # 先查映射表
    prefix = TYPE_ALIASES.get(doc_type.strip())
    if prefix:
        return prefix

    # 如果不在映射表中，直接使用用户输入（清理后作为前缀）
    return sanitize_filename(doc_type)


# =============================================================================
# 分析结果保存
# =============================================================================


def save_analysis(
    doc_type: str,
    title: str,
    content: str,
    date: str = None,
    source_file: str = None,
    skill_dir: Path = None,
) -> Path:
    """
    将分析结果保存为 Markdown 文件。

    参数:
        doc_type:     文档类型（中文名或英文模板名）
        title:        文档标题（用于生成文件名）
        content:      分析结果的完整 Markdown 内容
        date:         日期字符串 YYYY-MM-DD（默认当天）
        source_file:  原始文档路径（可选，记录在元信息中）
        skill_dir:    技能根目录（默认自动检测）

    返回:
        Path: 保存的文件路径
    """
    history_dir = (skill_dir or SKILL_DIR) / "references" / "history"

    # 解析日期
    if date:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            print(f"⚠️ 日期格式不合法: {date}，使用当天日期", file=sys.stderr)
            date = None
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    # 构建目录路径: references/history/YYYY-MM-DD/
    date_dir = history_dir / date
    date_dir.mkdir(parents=True, exist_ok=True)

    # 构建文件名: <文档类型>_<标题>.md
    type_prefix = resolve_type_prefix(doc_type)
    safe_title = sanitize_filename(title)
    filename = f"{type_prefix}_{safe_title}.md"
    filepath = date_dir / filename

    # 处理文件名冲突（同一天、同类型、同标题的文档可能分析多次）
    if filepath.exists():
        # 检查内容是否相同（只比较正文部分，排除 frontmatter 中的时间戳差异）
        existing_text = filepath.read_text(encoding="utf-8")
        existing_body = _strip_frontmatter(existing_text)
        existing_hash = hashlib.md5(existing_body.encode()).hexdigest()[:12]
        new_hash = hashlib.md5(content.strip().encode()).hexdigest()[:12]

        if existing_hash == new_hash:
            print(f"⚠️ 相同的分析结果已存在: {filepath.name}，跳过保存")
            return filepath

        # 内容不同，追加序号
        counter = 2
        while filepath.exists():
            filename = f"{type_prefix}_{safe_title}_{counter}.md"
            filepath = date_dir / filename
            counter += 1

    # 构建带元信息的完整内容
    header = _build_header(doc_type, title, date, source_file)
    full_content = header + content

    # 写入文件
    filepath.write_text(full_content, encoding="utf-8")

    return filepath


def _build_header(doc_type: str, title: str, date: str, source_file: str = None) -> str:
    """构建分析文件的元信息头部"""
    lines = [
        f"---",
        f"doc_type: {doc_type}",
        f"title: {title}",
        f"analysis_date: {date}",
        f"created_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    if source_file:
        lines.append(f"source_file: {source_file}")
    lines.append("---")
    lines.append("")

    return "\n".join(lines) + "\n"


def _strip_frontmatter(text: str) -> str:
    """
    移除 Markdown 文件的 YAML frontmatter，只返回正文部分。
    用于内容去重时排除 created_at 等时间戳字段的干扰。
    """
    if not text.startswith("---"):
        return text.strip()
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text.strip()
    return parts[2].strip()


# =============================================================================
# 历史记录查询
# =============================================================================


def list_history(date: str = None, doc_type: str = None):
    """列出历史分析记录"""
    if not HISTORY_DIR.exists():
        print("📂 暂无历史分析记录")
        return

    # 收集所有记录
    records = []
    date_dirs = sorted(HISTORY_DIR.iterdir()) if HISTORY_DIR.is_dir() else []

    for date_dir in date_dirs:
        if not date_dir.is_dir():
            continue
        dir_date = date_dir.name

        # 日期过滤
        if date and dir_date != date:
            continue

        for f in sorted(date_dir.glob("*.md")):
            # 读取 frontmatter 中的元信息
            meta = _read_frontmatter(f)
            record_type = meta.get("doc_type", "未知")

            # 类型过滤
            if doc_type:
                type_prefix = resolve_type_prefix(doc_type)
                if type_prefix not in record_type and doc_type not in record_type:
                    continue

            size = f.stat().st_size
            records.append(
                {
                    "date": dir_date,
                    "type": record_type,
                    "title": meta.get("title", f.stem),
                    "file": f.name,
                    "size": _human_size(size),
                    "path": str(f.relative_to(SKILL_DIR)),
                }
            )

    # 输出
    if not records:
        filter_desc = ""
        if date:
            filter_desc += f" 日期={date}"
        if doc_type:
            filter_desc += f" 类型={doc_type}"
        print(f"📂 未找到匹配的历史记录{filter_desc}")
        return

    print(f"\n📋 历史分析记录（共 {len(records)} 条）")
    print("=" * 70)

    current_date = None
    for r in records:
        if r["date"] != current_date:
            current_date = r["date"]
            print(f"\n📅 {current_date}")
            print("-" * 40)

        print(f"  [{r['type']}] {r['title']}")
        print(f"    → {r['path']} ({r['size']})")


def _read_frontmatter(filepath: Path) -> dict:
    """读取 Markdown 文件的 YAML frontmatter"""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return {}

    if not content.startswith("---"):
        return {}

    # 提取 frontmatter 块
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}

    meta = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()

    return meta


def _human_size(size_bytes: int) -> str:
    """字节数 → 人类可读格式"""
    for unit in ["B", "KB", "MB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.0f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} GB"


# =============================================================================
# CLI 入口
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="分析结果持久化工具 — 保存文档分析到 references/history/",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
存储路径:
  references/history/<YYYY-MM-DD>/<文档类型>_<标题>.md

示例:
  python save_analysis.py --type 周例会 --title "Q1产品规划讨论" --content "分析内容"
  python save_analysis.py --type 会议纪要 --title "Sprint回顾" --stdin < analysis.md
  python save_analysis.py --type 政策文件 --title "数据安全管理" --from-file /tmp/result.md
  python save_analysis.py --list
  python save_analysis.py --list --date 2025-03-01
  python save_analysis.py --list --type 会议纪要
        """,
    )

    # 保存模式参数
    parser.add_argument(
        "--type", "-t", help="文档类型（如：周例会、会议纪要、工作报告）"
    )
    parser.add_argument("--title", "-T", help="文档标题（用于生成文件名）")
    parser.add_argument("--content", "-c", help="分析内容（直接传入）")
    parser.add_argument("--stdin", action="store_true", help="从 stdin 读取分析内容")
    parser.add_argument("--from-file", "-f", type=Path, help="从文件读取分析内容")
    parser.add_argument("--date", "-d", help="日期 YYYY-MM-DD（默认当天）")
    parser.add_argument("--source", "-s", help="原始文档路径（可选，记录在元信息中）")
    parser.add_argument("--skill-dir", type=Path, default=None, help="技能根目录路径")

    # 查询模式参数
    parser.add_argument("--list", "-l", action="store_true", help="列出历史分析记录")

    args = parser.parse_args()

    # 查询模式
    if args.list:
        list_history(date=args.date, doc_type=args.type)
        return

    # 保存模式 — 参数校验
    if not args.type:
        parser.error("请指定文档类型: --type <类型>")
    if not args.title:
        parser.error("请指定文档标题: --title <标题>")

    # 获取分析内容
    content = None
    if args.content:
        content = args.content
    elif args.stdin:
        content = sys.stdin.read()
    elif args.from_file:
        if not args.from_file.exists():
            parser.error(f"文件不存在: {args.from_file}")
        content = args.from_file.read_text(encoding="utf-8")
    else:
        parser.error("请提供分析内容: --content, --stdin, 或 --from-file")

    if not content or not content.strip():
        parser.error("分析内容为空")

    # 执行保存
    filepath = save_analysis(
        doc_type=args.type,
        title=args.title,
        content=content,
        date=args.date,
        source_file=args.source,
        skill_dir=args.skill_dir,
    )

    print(f"✅ 分析结果已保存: {filepath.relative_to(SKILL_DIR)}")
    print(f"   完整路径: {filepath}")


if __name__ == "__main__":
    main()
