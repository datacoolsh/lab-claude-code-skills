#!/usr/bin/env python3
"""
PPT 生成器 — 将 Markdown 内容渲染为 Anthropic 品牌风格的 Reveal.js HTML。

用法：
    # 从 Markdown 文件生成
    python generate_ppt.py --content docs/intro.md --title "项目介绍" --output output/intro.html

    # 从字符串生成
    python generate_ppt.py --content "## Hello\nWorld" --title "测试" --output output/test.html

    # 指定日期和副标题
    python generate_ppt.py --content docs/intro.md --title "项目介绍" \
        --subtitle "2026 Q1 规划" --date "2026-03-01" --output output/intro.html

纯标准库实现，无第三方依赖。
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# 导入同目录的解析器
sys.path.insert(0, str(Path(__file__).parent))
from markdown_parser import MarkdownParser


# ── HTML 模板 ─────────────────────────────────────────────────────────
# 内联完整的 Anthropic 品牌主题，确保输出单文件独立运行。

HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&family=Lora:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5/plugin/highlight/monokai.css">
    <style>
        :root {{
            --anthropic-dark: #141413;
            --anthropic-light: #faf9f5;
            --anthropic-mid-gray: #b0aea5;
            --anthropic-light-gray: #e8e6dc;
            --anthropic-orange: #d97757;
            --anthropic-blue: #6a9bcc;
            --anthropic-green: #788c5d;
            --font-heading: 'Poppins', Arial, sans-serif;
            --font-body: 'Lora', Georgia, serif;
            --font-mono: 'JetBrains Mono', 'Consolas', monospace;
        }}
        .reveal {{
            font-family: var(--font-body);
            font-size: 28px;
            color: var(--anthropic-dark);
            background-color: var(--anthropic-light);
        }}
        .reveal .slides {{ text-align: left; }}
        .reveal h1,.reveal h2,.reveal h3,.reveal h4,.reveal h5,.reveal h6 {{
            font-family: var(--font-heading);
            font-weight: 600;
            color: var(--anthropic-dark);
            margin-bottom: 0.5em;
            line-height: 1.2;
            text-transform: none;
        }}
        .reveal h1 {{ font-size: 2.6em; }}
        .reveal h2 {{ font-size: 1.8em; margin-top: 0; }}
        .reveal h3 {{ font-size: 1.4em; }}
        .reveal p {{ line-height: 1.6; margin-bottom: 0.6em; }}
        .reveal strong,.reveal b {{ color: var(--anthropic-orange); font-weight: 600; }}
        .reveal em {{ color: var(--anthropic-mid-gray); }}
        .reveal a {{ color: var(--anthropic-blue); text-decoration: none; }}
        .reveal a:hover {{ border-bottom: 2px solid var(--anthropic-blue); }}
        .reveal ul,.reveal ol {{ margin-left: 1.2em; margin-bottom: 0.8em; }}
        .reveal li {{ margin-bottom: 0.35em; line-height: 1.5; }}
        .reveal ul li::marker {{ color: var(--anthropic-orange); }}
        .reveal ol li::marker {{ color: var(--anthropic-blue); font-weight: 600; }}
        .reveal code {{
            font-family: var(--font-mono);
            background: var(--anthropic-light-gray);
            padding: 0.15em 0.35em;
            border-radius: 4px;
            color: var(--anthropic-dark);
            font-size: 0.85em;
        }}
        .reveal pre {{
            background: var(--anthropic-dark);
            border-left: 6px solid var(--anthropic-orange);
            padding: 1em;
            border-radius: 8px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.18);
            margin: 0.8em 0;
            width: 100%;
            box-sizing: border-box;
        }}
        .reveal pre code {{
            background: transparent;
            color: var(--anthropic-light);
            padding: 0;
            font-size: 0.7em;
            line-height: 1.6;
            max-height: 460px;
        }}
        .reveal blockquote {{
            background: var(--anthropic-light-gray);
            border-left: 5px solid var(--anthropic-blue);
            padding: 0.8em 1.2em;
            margin: 0.8em 0;
            font-style: italic;
            color: #555;
            border-radius: 0 6px 6px 0;
        }}
        .reveal table {{ border-collapse: collapse; width: 100%; margin: 0.8em 0; font-size: 0.85em; }}
        .reveal th {{
            background: var(--anthropic-orange);
            color: var(--anthropic-light);
            font-family: var(--font-heading);
            font-weight: 600;
            padding: 0.55em 0.8em;
            text-align: left;
        }}
        .reveal td {{ border-bottom: 1px solid var(--anthropic-light-gray); padding: 0.55em 0.8em; }}
        .reveal tr:nth-child(even) {{ background: rgba(232,230,220,0.3); }}
        /* 标题页 */
        .reveal .title-slide {{
            text-align: center;
            display: flex !important;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            height: 100%;
        }}
        .reveal .title-slide h1 {{
            font-size: 3em;
            margin-bottom: 0.2em;
            border-bottom: none;
            background: linear-gradient(135deg, var(--anthropic-dark) 0%, #3a3a38 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .reveal .title-slide .subtitle {{
            font-size: 1.3em;
            color: var(--anthropic-mid-gray);
            font-family: var(--font-body);
            margin-bottom: 1.5em;
            font-weight: 400;
        }}
        .reveal .title-slide .meta {{
            font-size: 0.85em;
            color: var(--anthropic-mid-gray);
            font-family: var(--font-mono);
            letter-spacing: 0.05em;
        }}
        .reveal .title-slide .brand-bar,
        .reveal .end-slide .brand-bar {{
            display: flex; gap: 0; height: 6px; border-radius: 3px;
            overflow: hidden; margin: 1.5em auto 0; width: 240px;
        }}
        .reveal .title-slide .brand-bar span:nth-child(1),
        .reveal .end-slide .brand-bar span:nth-child(1) {{ flex:1; background: var(--anthropic-orange); }}
        .reveal .title-slide .brand-bar span:nth-child(2),
        .reveal .end-slide .brand-bar span:nth-child(2) {{ flex:1; background: var(--anthropic-blue); }}
        .reveal .title-slide .brand-bar span:nth-child(3),
        .reveal .end-slide .brand-bar span:nth-child(3) {{ flex:1; background: var(--anthropic-green); }}
        /* 顶部装饰条 */
        .reveal .slides section {{ padding-top: 28px; }}
        .reveal .slides section::before {{
            content: ''; position: absolute; top: 0; left: 0;
            width: 100%; height: 8px; z-index: 10;
        }}
        .reveal .slides section:nth-child(3n+1)::before {{ background: var(--anthropic-orange); }}
        .reveal .slides section:nth-child(3n+2)::before {{ background: var(--anthropic-blue); }}
        .reveal .slides section:nth-child(3n+3)::before {{ background: var(--anthropic-green); }}
        .reveal .title-slide::before,
        .reveal .end-slide::before {{ display: none; }}
        /* 分栏 */
        .split-layout {{
            display: grid; grid-template-columns: 1fr 1fr;
            gap: 2em; align-items: start; margin-top: 0.5em;
        }}
        .split-layout .col {{
            padding: 1em; background: rgba(232,230,220,0.2); border-radius: 8px;
        }}
        .split-layout .col h3 {{ font-size: 1.1em; margin-bottom: 0.4em; padding-bottom: 0.3em; }}
        .split-layout .col:first-child h3 {{ border-bottom: 3px solid var(--anthropic-orange); }}
        .split-layout .col:last-child h3 {{ border-bottom: 3px solid var(--anthropic-blue); }}
        /* 结束页 */
        .reveal .end-slide {{
            text-align: center;
            display: flex !important;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            height: 100%;
            background: var(--anthropic-dark);
            color: var(--anthropic-light);
        }}
        .reveal .end-slide h2 {{ color: var(--anthropic-light); font-size: 2.5em; margin-bottom: 0.3em; }}
        .reveal .end-slide p {{ color: var(--anthropic-mid-gray); }}
        .reveal .end-slide .brand-bar {{ width: 200px; height: 5px; }}
        /* 控件 */
        .reveal .controls {{ color: var(--anthropic-orange); }}
        .reveal .progress {{ color: var(--anthropic-orange); height: 4px; }}
        .reveal .slide-number {{
            color: var(--anthropic-mid-gray);
            font-family: var(--font-mono);
            font-size: 0.75em;
            background: transparent;
        }}
    </style>
</head>
<body>
    <div class="reveal">
        <div class="slides">
{slides_html}
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/reveal.js@5/plugin/highlight/highlight.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/reveal.js@5/plugin/markdown/markdown.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/reveal.js@5/plugin/notes/notes.js"></script>
    <script>
        Reveal.initialize({{
            width: 1280, height: 720, margin: 0.08,
            minScale: 0.2, maxScale: 2.0,
            controls: true, progress: true, center: false,
            hash: true, slideNumber: 'c/t',
            transition: 'slide', transitionSpeed: 'default',
            backgroundTransition: 'fade',
            keyboard: true, overview: true, touch: true,
            fragments: false, fragmentInURL: false,
            autoSlide: 0, mouseWheel: false, showNotes: false,
            plugins: [RevealHighlight, RevealMarkdown, RevealNotes]
        }});
        Reveal.addKeyBinding({{ keyCode: 72, key: 'H', description: '返回首页' }}, function() {{
            Reveal.slide(0);
        }});
    </script>
</body>
</html>'''


# ── Slide 渲染器 ──────────────────────────────────────────────────────

def render_slide(slide: Dict[str, Any]) -> str:
    """将单个 slide 数据渲染为 <section> HTML。"""
    layout = slide.get('layout', 'content')
    renderer = RENDERERS.get(layout, _render_content)
    return renderer(slide)


def _render_title(s: Dict[str, Any]) -> str:
    title = s.get('title', '')
    subtitle = s.get('subtitle', '')
    date = s.get('date', '')
    meta_parts = []
    if date:
        meta_parts.append(date)
    meta_parts.append('算酷团队')
    meta = ' &nbsp;|&nbsp; '.join(meta_parts)

    sub_html = f'<p class="subtitle">{subtitle}</p>' if subtitle else ''
    return (
        f'            <section class="title-slide">\n'
        f'                <h1>{title}</h1>\n'
        f'                {sub_html}\n'
        f'                <p class="meta">{meta}</p>\n'
        f'                <div class="brand-bar"><span></span><span></span><span></span></div>\n'
        f'            </section>'
    )


def _render_content(s: Dict[str, Any]) -> str:
    title = s.get('title', '')
    content = s.get('content', '')
    title_html = f'<h2>{title}</h2>\n                ' if title else ''
    return (
        f'            <section>\n'
        f'                {title_html}'
        f'{content}\n'
        f'            </section>'
    )


def _render_code(s: Dict[str, Any]) -> str:
    title = s.get('title', '')
    lang = s.get('language', 'text')
    code = s.get('code', '')
    prefix = s.get('prefix', '')
    prefix_html = f'{prefix}\n                ' if prefix else ''
    return (
        f'            <section>\n'
        f'                <h2>{title}</h2>\n'
        f'                {prefix_html}'
        f'<pre><code class="language-{lang}" data-trim data-noescape>\n'
        f'{code}\n'
        f'                </code></pre>\n'
        f'            </section>'
    )


def _render_bullets(s: Dict[str, Any]) -> str:
    title = s.get('title', '')
    items = s.get('items', [])
    li_html = '\n'.join(
        f'                    <li>{item}</li>' for item in items
    )
    return (
        f'            <section>\n'
        f'                <h2>{title}</h2>\n'
        f'                <ul>\n{li_html}\n                </ul>\n'
        f'            </section>'
    )


def _render_split(s: Dict[str, Any]) -> str:
    title = s.get('title', '')
    left = s.get('left', '')
    right = s.get('right', '')
    return (
        f'            <section>\n'
        f'                <h2>{title}</h2>\n'
        f'                <div class="split-layout">\n'
        f'                    <div class="col">{left}</div>\n'
        f'                    <div class="col">{right}</div>\n'
        f'                </div>\n'
        f'            </section>'
    )


def _render_end(s: Dict[str, Any]) -> str:
    title = s.get('title', 'Thank You')
    subtitle = s.get('subtitle', '算酷团队')
    return (
        f'            <section class="end-slide" data-background-color="#141413">\n'
        f'                <h2>{title}</h2>\n'
        f'                <p style="font-size:1.1em;">{subtitle}</p>\n'
        f'                <div class="brand-bar"><span></span><span></span><span></span></div>\n'
        f'            </section>'
    )


RENDERERS = {
    'title': _render_title,
    'content': _render_content,
    'code': _render_code,
    'bullets': _render_bullets,
    'split': _render_split,
    'end': _render_end,
}


# ── 生成器核心 ────────────────────────────────────────────────────────

class PPTGenerator:
    """将 Markdown 内容生成为 Anthropic 品牌风格的 Reveal.js HTML 文件。"""

    def __init__(self):
        self.parser = MarkdownParser()

    def generate(self, content: str, title: str,
                 output_path: str,
                 subtitle: str = '',
                 date: str = '') -> str:
        """
        主流程：解析 → 渲染 → 写入文件。
        返回输出文件的绝对路径。
        """
        # 1. 解析 Markdown
        slides = self.parser.parse(
            content, title=title, subtitle=subtitle, date=date
        )

        # 2. 渲染每一页
        sections = [render_slide(s) for s in slides]
        slides_html = '\n\n'.join(sections)

        # 3. 组装完整 HTML
        final_html = HTML_TEMPLATE.format(
            title=title,
            slides_html=slides_html,
        )

        # 4. 写入文件
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(final_html, encoding='utf-8')

        return str(out.resolve())

    def generate_from_file(self, md_path: str, title: str,
                           output_path: str, **kwargs) -> str:
        """从 Markdown 文件读取内容并生成 PPT。"""
        content = Path(md_path).read_text(encoding='utf-8')
        return self.generate(content, title, output_path, **kwargs)


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='生成 Anthropic 品牌风格的 Web PPT'
    )
    parser.add_argument(
        '--content', required=True,
        help='Markdown 内容字符串，或 .md 文件路径'
    )
    parser.add_argument('--title', default='Presentation', help='PPT 主标题')
    parser.add_argument('--subtitle', default='', help='PPT 副标题')
    parser.add_argument('--date', default='', help='日期（如 2026-03-01）')
    parser.add_argument('--output', required=True, help='输出 HTML 文件路径')
    args = parser.parse_args()

    gen = PPTGenerator()

    # 判断 --content 是文件还是字符串
    content_path = Path(args.content)
    if content_path.is_file():
        result = gen.generate_from_file(
            str(content_path), args.title, args.output,
            subtitle=args.subtitle, date=args.date,
        )
    else:
        result = gen.generate(
            args.content, args.title, args.output,
            subtitle=args.subtitle, date=args.date,
        )

    slide_count = result  # 这里只是路径
    # 重新计算页数
    gen2 = PPTGenerator()
    p = Path(args.content)
    text = p.read_text(encoding='utf-8') if p.is_file() else args.content
    slides = gen2.parser.parse(text, title=args.title)

    print(f'PPT 生成成功！')
    print(f'文件路径：{result}')
    print(f'幻灯片数：{len(slides)} 页')
    print(f'打开方式：双击文件或在浏览器中访问')


if __name__ == '__main__':
    main()
