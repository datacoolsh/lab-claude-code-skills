#!/usr/bin/env python3
"""
Markdown → 幻灯片解析器

将 Markdown 文本解析为结构化的幻灯片数据列表。
纯标准库实现，无第三方依赖。

分页规则：
  1. # 一级标题 → 标题页
  2. ## 二级标题 → 新内容页
  3. --- 分隔符 → 强制分页
  4. 代码块自动识别为 code 布局
  5. 纯列表内容识别为 bullets 布局
  6. ::: split ... ||| ... ::: → 分栏布局
  7. 单页超过 MAX_CHARS_PER_SLIDE 字时自动拆分
"""

import re
import html as html_mod
from typing import List, Dict, Any, Optional

MAX_CHARS_PER_SLIDE = 600
MAX_BULLETS_PER_SLIDE = 7


# ── Markdown → HTML 内联转换 ──────────────────────────────────────────

def _inline(text: str) -> str:
    """将 Markdown 内联语法转换为 HTML（粗体、斜体、行内代码、链接、图片）"""
    # 行内代码（先处理，防止内部被其它规则干扰）
    text = re.sub(r'`([^`]+?)`', r'<code>\1</code>', text)
    # 图片（必须在链接之前）
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1">', text)
    # 链接
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    # 粗体
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
    # 斜体
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<em>\1</em>', text)
    return text


def _block_to_html(block: str) -> str:
    """
    将一个文本块（不含标题、不含代码块、不含分隔符）转换为 HTML。
    支持：段落、引用、无序列表、有序列表、表格。
    """
    lines = block.strip().split('\n')
    if not lines:
        return ''

    parts: List[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # ── 引用块 ──
        if line.startswith('> '):
            quote_lines = []
            while i < len(lines) and lines[i].startswith('> '):
                quote_lines.append(_inline(lines[i][2:]))
                i += 1
            parts.append(
                '<blockquote>' + '<br>'.join(quote_lines) + '</blockquote>'
            )
            continue

        # ── 无序列表 ──
        if re.match(r'^[\-\*]\s+', line):
            items: List[str] = []
            while i < len(lines) and re.match(r'^[\-\*]\s+', lines[i]):
                items.append(_inline(re.sub(r'^[\-\*]\s+', '', lines[i])))
                i += 1
            parts.append(
                '<ul>' + ''.join(f'<li>{it}</li>' for it in items) + '</ul>'
            )
            continue

        # ── 有序列表 ──
        if re.match(r'^\d+\.\s+', line):
            items = []
            while i < len(lines) and re.match(r'^\d+\.\s+', lines[i]):
                items.append(_inline(re.sub(r'^\d+\.\s+', '', lines[i])))
                i += 1
            parts.append(
                '<ol>' + ''.join(f'<li>{it}</li>' for it in items) + '</ol>'
            )
            continue

        # ── 表格 ──
        if '|' in line and i + 1 < len(lines) and re.match(r'^[\s|:-]+$', lines[i + 1]):
            header_cells = [c.strip() for c in line.strip('| ').split('|')]
            i += 2  # 跳过分隔行
            rows: List[List[str]] = []
            while i < len(lines) and '|' in lines[i]:
                row_cells = [c.strip() for c in lines[i].strip('| ').split('|')]
                rows.append(row_cells)
                i += 1
            thead = '<tr>' + ''.join(f'<th>{_inline(c)}</th>' for c in header_cells) + '</tr>'
            tbody_rows = ''.join(
                '<tr>' + ''.join(f'<td>{_inline(c)}</td>' for c in row) + '</tr>'
                for row in rows
            )
            parts.append(f'<table><thead>{thead}</thead><tbody>{tbody_rows}</tbody></table>')
            continue

        # ── 空行跳过 ──
        if not line.strip():
            i += 1
            continue

        # ── 子标题（### 及以下） ──
        h_match = re.match(r'^(#{3,6})\s+(.+)$', line)
        if h_match:
            h_level = len(h_match.group(1))
            h_text = _inline(h_match.group(2).strip())
            parts.append(f'<h{h_level}>{h_text}</h{h_level}>')
            i += 1
            continue

        # ── 普通段落（收集连续非空行） ──
        para_lines = []
        while i < len(lines) and lines[i].strip() and not lines[i].startswith('> ') \
                and not re.match(r'^[\-\*]\s+', lines[i]) \
                and not re.match(r'^\d+\.\s+', lines[i]) \
                and not re.match(r'^#{3,6}\s+', lines[i]):
            para_lines.append(lines[i])
            i += 1
        if para_lines:
            parts.append('<p>' + _inline(' '.join(para_lines)) + '</p>')

    return '\n'.join(parts)


# ── 核心解析器 ────────────────────────────────────────────────────────

class MarkdownParser:
    """将 Markdown 文本解析为幻灯片数据列表"""

    def parse(self, text: str, title: Optional[str] = None,
              subtitle: Optional[str] = None,
              date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        主入口。返回 [{"layout": "...", ...}, ...] 列表。
        """
        # 规范化换行
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # 第一步：拆分为原始片段（按 ## / --- 分割）
        raw_sections = self._split_sections(text)

        # 第二步：逐片段生成 slide 数据
        slides: List[Dict[str, Any]] = []

        for idx, sec in enumerate(raw_sections):
            sec_slides = self._section_to_slides(sec, idx)
            slides.extend(sec_slides)

        # 如果第一页不是 title 类型，自动插入标题页
        if not slides or slides[0].get('layout') != 'title':
            title_slide = {
                'layout': 'title',
                'title': title or '演示文稿',
                'subtitle': subtitle or '',
                'date': date or '',
            }
            slides.insert(0, title_slide)
        else:
            # 用参数覆盖已解析的标题页
            if title:
                slides[0]['title'] = title
            if subtitle:
                slides[0]['subtitle'] = subtitle
            if date:
                slides[0]['date'] = date

        # 自动追加结束页
        slides.append({
            'layout': 'end',
            'title': 'Thank You',
            'subtitle': 'Powered by Claude Code',
        })

        return slides

    # ── 分段 ──────────────────────────────────────────────────────

    def _split_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        按 # 标题 和 --- 分隔符，将 Markdown 拆分为若干片段。
        每个片段 = {"heading_level": int|None, "heading": str, "body": str}
        """
        sections: List[Dict[str, Any]] = []
        current_body_lines: List[str] = []
        current_heading: Optional[str] = None
        current_level: Optional[int] = None

        lines = text.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]

            # 代码块：原样收集，不在其中做分页
            if line.strip().startswith('```'):
                current_body_lines.append(line)
                i += 1
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    current_body_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    current_body_lines.append(lines[i])  # 结束的 ```
                    i += 1
                continue

            # ::: split 块：原样收集
            if line.strip() == '::: split':
                current_body_lines.append(line)
                i += 1
                while i < len(lines) and lines[i].strip() != ':::':
                    current_body_lines.append(lines[i])
                    i += 1
                if i < len(lines):
                    current_body_lines.append(lines[i])
                    i += 1
                continue

            # --- 分隔符（至少 3 个 -，单独成行，且不是表格分隔行）
            if re.match(r'^-{3,}\s*$', line) and not (
                i > 0 and '|' in lines[i - 1]
            ):
                # 保存当前段落
                sections.append({
                    'heading_level': current_level,
                    'heading': current_heading,
                    'body': '\n'.join(current_body_lines),
                })
                current_body_lines = []
                current_heading = None
                current_level = None
                i += 1
                continue

            # 标题行
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if heading_match:
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()

                # 一级或二级标题 → 新段落
                if level <= 2:
                    # 先保存之前的
                    if current_heading is not None or any(l.strip() for l in current_body_lines):
                        sections.append({
                            'heading_level': current_level,
                            'heading': current_heading,
                            'body': '\n'.join(current_body_lines),
                        })
                    current_heading = heading_text
                    current_level = level
                    current_body_lines = []
                    i += 1
                    continue
                else:
                    # 三级及以下标题保留在 body 中
                    current_body_lines.append(line)
                    i += 1
                    continue

            # 普通行
            current_body_lines.append(line)
            i += 1

        # 收尾
        if current_heading is not None or any(l.strip() for l in current_body_lines):
            sections.append({
                'heading_level': current_level,
                'heading': current_heading,
                'body': '\n'.join(current_body_lines),
            })

        return sections

    # ── 片段 → Slide(s) ──────────────────────────────────────────

    def _section_to_slides(self, sec: Dict[str, Any],
                           idx: int) -> List[Dict[str, Any]]:
        """将单个片段转换为一个或多个 slide 数据。"""
        level = sec['heading_level']
        heading = sec['heading'] or ''
        body = sec['body'].strip()

        # ── 一级标题 → 标题页 ──
        if level == 1:
            # 如果 body 中有文本，取第一个非空行做副标题
            sub = ''
            if body:
                first_line = body.split('\n')[0].strip()
                if first_line and not first_line.startswith('```'):
                    sub = first_line
            return [{
                'layout': 'title',
                'title': heading,
                'subtitle': sub,
                'date': '',
            }]

        # ── 检测 split 布局 ──
        if '::: split' in body:
            return [self._parse_split(heading, body)]

        # ── 检测代码块 ──
        code_blocks = list(re.finditer(r'```(\w*)\n(.*?)```', body, re.DOTALL))
        if code_blocks:
            return self._parse_code_section(heading, body, code_blocks)

        # ── 检测纯列表 ──
        non_empty_lines = [l for l in body.split('\n') if l.strip()]
        if non_empty_lines and all(
            re.match(r'^[\-\*]\s+', l) or re.match(r'^\d+\.\s+', l)
            for l in non_empty_lines
        ):
            return self._parse_bullets_section(heading, body)

        # ── 普通内容页 ──
        return self._parse_content_section(heading, body)

    # ── 各布局解析 ────────────────────────────────────────────────

    def _parse_split(self, heading: str, body: str) -> Dict[str, Any]:
        """解析 ::: split ... ||| ... ::: 分栏布局"""
        match = re.search(
            r'::: split\s*\n(.*?)\|\|\|(.*?):::',
            body, re.DOTALL
        )
        if match:
            left = _block_to_html(match.group(1).strip())
            right = _block_to_html(match.group(2).strip())
        else:
            left = _block_to_html(body)
            right = ''

        return {
            'layout': 'split',
            'title': heading,
            'left': left,
            'right': right,
        }

    def _parse_code_section(self, heading: str, body: str,
                            code_blocks: list) -> List[Dict[str, Any]]:
        """
        包含代码块的段落。
        策略：如果有前导文本 + 代码块，合在一页；多个代码块拆分。
        """
        slides: List[Dict[str, Any]] = []

        # 提取代码块之外的文本
        remaining = body
        for cb in reversed(code_blocks):
            remaining = remaining[:cb.start()] + remaining[cb.end():]
        prefix_html = _block_to_html(remaining.strip())

        for i, cb in enumerate(code_blocks):
            lang = cb.group(1) or 'text'
            code = cb.group(2).strip()
            slide: Dict[str, Any] = {
                'layout': 'code',
                'title': heading if i == 0 else f'{heading}（续）',
                'language': lang,
                'code': html_mod.escape(code),
            }
            # 第一个代码块带前导文本
            if i == 0 and prefix_html:
                slide['prefix'] = prefix_html
            slides.append(slide)

        return slides if slides else [{'layout': 'content', 'title': heading, 'content': ''}]

    def _parse_bullets_section(self, heading: str,
                               body: str) -> List[Dict[str, Any]]:
        """纯列表内容。超过 MAX_BULLETS_PER_SLIDE 条时拆页。"""
        items: List[str] = []
        for line in body.split('\n'):
            line = line.strip()
            if re.match(r'^[\-\*]\s+', line):
                items.append(_inline(re.sub(r'^[\-\*]\s+', '', line)))
            elif re.match(r'^\d+\.\s+', line):
                items.append(_inline(re.sub(r'^\d+\.\s+', '', line)))

        slides: List[Dict[str, Any]] = []
        for chunk_idx in range(0, len(items), MAX_BULLETS_PER_SLIDE):
            chunk = items[chunk_idx:chunk_idx + MAX_BULLETS_PER_SLIDE]
            page_title = heading
            if chunk_idx > 0:
                page_title = f'{heading}（续）'
            slides.append({
                'layout': 'bullets',
                'title': page_title,
                'items': chunk,
            })

        return slides if slides else [{'layout': 'content', 'title': heading, 'content': ''}]

    def _parse_content_section(self, heading: str,
                                body: str) -> List[Dict[str, Any]]:
        """普通内容。超过 MAX_CHARS_PER_SLIDE 字符时按段落拆页。"""
        if not body.strip():
            if heading:
                return [{'layout': 'content', 'title': heading, 'content': ''}]
            return []

        content_html = _block_to_html(body)

        # 如果内容不长，直接一页
        plain_len = len(re.sub(r'<[^>]+>', '', content_html))
        if plain_len <= MAX_CHARS_PER_SLIDE:
            return [{'layout': 'content', 'title': heading, 'content': content_html}]

        # 按段落拆分
        paragraphs = re.split(r'\n\n+', body.strip())
        slides: List[Dict[str, Any]] = []
        current_paras: List[str] = []
        current_len = 0

        for para in paragraphs:
            para_len = len(para)
            if current_len + para_len > MAX_CHARS_PER_SLIDE and current_paras:
                html = _block_to_html('\n\n'.join(current_paras))
                page_title = heading if not slides else f'{heading}（续）'
                slides.append({'layout': 'content', 'title': page_title, 'content': html})
                current_paras = []
                current_len = 0
            current_paras.append(para)
            current_len += para_len

        if current_paras:
            html = _block_to_html('\n\n'.join(current_paras))
            page_title = heading if not slides else f'{heading}（续）'
            slides.append({'layout': 'content', 'title': page_title, 'content': html})

        return slides


# ── 命令行测试 ────────────────────────────────────────────────────────

if __name__ == '__main__':
    sample = r"""
# Claude Code 功能介绍
智能编程助手

## 核心能力

Claude Code 是一个**强大的命令行工具**，可以帮助开发者高效完成各种编程任务。

> "让 AI 做苦力，人类做决策。"

## 主要功能

- 代码生成与补全
- 代码审查与重构
- Bug 诊断与修复
- 文档编写与维护
- 测试用例生成
- 项目架构设计
- Git 操作辅助
- 多语言支持

## 技术实现

```python
from anthropic import Anthropic

client = Anthropic()

def ask_claude(prompt: str) -> str:
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
```

## 性能对比

| 指标 | Claude Code | 传统IDE |
| ---- | ----------- | ------- |
| 代码生成速度 | 极快 | 手动 |
| 上下文理解 | 全项目级别 | 单文件 |
| 重构能力 | 智能重构 | 搜索替换 |
| 学习曲线 | 低 | 中等 |

## 左右对比

::: split
### 优势
- 自然语言交互
- 理解项目上下文
- 多文件协同操作
|||
### 适用场景
- 快速原型开发
- 代码审查辅助
- 复杂 Bug 诊断
:::

---

## 总结

Claude Code 通过 AI 能力**大幅提升**开发者的编程效率，让团队能够专注于更有创造性的工作。
"""

    import json
    parser = MarkdownParser()
    slides = parser.parse(sample, title='Claude Code 功能介绍', date='2026-03-01')
    print(json.dumps(slides, indent=2, ensure_ascii=False))
    print(f'\n共生成 {len(slides)} 页幻灯片')
