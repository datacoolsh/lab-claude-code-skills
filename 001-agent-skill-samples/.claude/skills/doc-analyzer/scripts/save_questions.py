#!/usr/bin/env python3
"""
save_questions.py — 追问持久化工具
====================================

将用户在文档分析过程中提出的高价值追问保存到对应的问题模板文件中，
形成持续积累的问题库。每次分析同类文档时，AI 可以参考历史追问，
更精准地命中用户的关注点。

用法:
    python save_questions.py <模板类型> <追问内容> [--skill-dir <路径>]
    python save_questions.py meeting_minutes "上次遗留的预算问题本次是否推进了？"
    python save_questions.py policy_document "新政策对已签合同是否有溯及力？"

    # 批量添加（用 | 分隔多条追问）
    python save_questions.py work_report "问题1|问题2|问题3"

    # 查看某个模板的历史追问
    python save_questions.py meeting_minutes --list

模板类型:
    meeting_minutes   — 会议纪要
    leadership_speech — 领导讲话
    policy_document   — 政策文件
    work_report       — 工作报告
    plan_proposal     — 方案规划
    data_analysis     — 数据分析报告
    general           — 通用文档
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# 技能根目录（相对于此脚本的位置）
SKILL_DIR = Path(__file__).resolve().parent.parent
QUESTIONS_DIR = SKILL_DIR / "references" / "questions"

# 有效的模板类型列表
VALID_TEMPLATES = [
    "meeting_minutes",
    "leadership_speech",
    "policy_document",
    "work_report",
    "plan_proposal",
    "data_analysis",
    "general",
]

# 模板类型的中文名映射（用于输出提示）
TEMPLATE_NAMES = {
    "meeting_minutes": "会议纪要",
    "leadership_speech": "领导讲话",
    "policy_document": "政策文件",
    "work_report": "工作报告",
    "plan_proposal": "方案规划",
    "data_analysis": "数据分析报告",
    "general": "通用文档",
}


def get_template_path(template_type: str) -> Path:
    """获取模板文件的完整路径"""
    return QUESTIONS_DIR / f"{template_type}.md"


def read_existing_questions(template_path: Path) -> list[str]:
    """读取模板文件中已有的用户历史追问"""
    if not template_path.exists():
        return []

    content = template_path.read_text(encoding="utf-8")

    # 定位"用户历史追问"部分
    marker = "## 用户历史追问"
    if marker not in content:
        return []

    # 提取 marker 之后的所有以 "- " 开头的行
    after_marker = content.split(marker, 1)[1]
    questions = []
    for line in after_marker.strip().splitlines():
        line = line.strip()
        if line.startswith("- "):
            # 提取追问文本（去掉前缀的 "- " 和可能的时间戳标记）
            q_text = line[2:].strip()
            # 如果有时间戳格式 [YYYY-MM-DD]，提取纯文本部分
            if q_text.startswith("[") and "]" in q_text:
                q_text = q_text.split("]", 1)[1].strip()
            questions.append(q_text)

    return questions


def save_question(template_type: str, question: str, skill_dir: Path = None) -> bool:
    """
    将一条追问保存到对应的模板文件。

    参数:
        template_type: 模板类型标识符
        question: 追问内容
        skill_dir: 技能根目录（可选，默认使用脚本所在目录的上级）

    返回:
        bool: 是否成功保存（如果重复则返回 False）
    """
    questions_dir = (skill_dir or SKILL_DIR) / "references" / "questions"
    template_path = questions_dir / f"{template_type}.md"

    if not template_path.exists():
        print(f"❌ 模板文件不存在: {template_path}", file=sys.stderr)
        return False

    # 去除追问内容的首尾空白
    question = question.strip()
    if not question:
        print("⚠️ 追问内容为空，跳过", file=sys.stderr)
        return False

    # 检查是否重复
    existing = read_existing_questions(template_path)
    # 标准化比较（忽略标点和空格差异）
    normalized_existing = {
        q.replace(" ", "").replace("？", "").replace("?", "").lower() for q in existing
    }
    normalized_new = (
        question.replace(" ", "").replace("？", "").replace("?", "").lower()
    )

    if normalized_new in normalized_existing:
        print(f"⚠️ 追问已存在，跳过: {question[:50]}...")
        return False

    # 构造带时间戳的条目
    today = datetime.now().strftime("%Y-%m-%d")
    entry = f"- [{today}] {question}\n"

    # 读取完整文件内容
    content = template_path.read_text(encoding="utf-8")

    # 确保"用户历史追问"部分存在
    marker = "## 用户历史追问"
    if marker not in content:
        # 在文件末尾添加此部分
        content = content.rstrip() + f"\n\n---\n\n{marker}\n\n"

    # 追加到文件末尾
    with open(template_path, "a", encoding="utf-8") as f:
        f.write(entry)

    return True


def list_questions(template_type: str):
    """列出某个模板的所有历史追问"""
    template_path = get_template_path(template_type)
    questions = read_existing_questions(template_path)

    name = TEMPLATE_NAMES.get(template_type, template_type)
    print(f"\n📋 {name}模板 — 历史追问（共 {len(questions)} 条）")
    print("=" * 50)

    if not questions:
        print("  （暂无历史追问）")
        return

    for i, q in enumerate(questions, 1):
        print(f"  {i}. {q}")


def main():
    parser = argparse.ArgumentParser(
        description="追问持久化工具 — 将用户追问保存到问题模板",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
模板类型:
  meeting_minutes   — 会议纪要
  leadership_speech — 领导讲话
  policy_document   — 政策文件
  work_report       — 工作报告
  plan_proposal     — 方案规划
  data_analysis     — 数据分析报告
  general           — 通用文档

示例:
  python save_questions.py meeting_minutes "遗留问题是否有跟进？"
  python save_questions.py work_report "问题A|问题B|问题C"
  python save_questions.py policy_document --list
        """,
    )
    parser.add_argument("template_type", choices=VALID_TEMPLATES, help="模板类型标识符")
    parser.add_argument(
        "question", nargs="?", default=None, help="追问内容（用 | 分隔可批量添加）"
    )
    parser.add_argument(
        "--list", "-l", action="store_true", help="列出该模板的所有历史追问"
    )
    parser.add_argument(
        "--skill-dir",
        type=Path,
        default=None,
        help="技能根目录路径（默认: 脚本所在目录的上级）",
    )

    args = parser.parse_args()

    if args.list:
        list_questions(args.template_type)
        return

    if not args.question:
        parser.error("请提供追问内容，或使用 --list 查看历史追问")

    # 支持用 | 分隔的批量输入
    questions = [q.strip() for q in args.question.split("|") if q.strip()]

    saved_count = 0
    for q in questions:
        success = save_question(args.template_type, q, args.skill_dir)
        if success:
            name = TEMPLATE_NAMES.get(args.template_type, args.template_type)
            print(f"✅ 已保存到 [{name}] 模板: {q[:60]}{'...' if len(q) > 60 else ''}")
            saved_count += 1

    print(f"\n📊 本次保存: {saved_count}/{len(questions)} 条追问")


if __name__ == "__main__":
    main()
