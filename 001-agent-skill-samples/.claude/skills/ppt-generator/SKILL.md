---
name: ppt-generator
description: >
  基于 Web 的 PPT 生成器，采用"先积累、后生成"的两阶段工作流。
  第一阶段：用户输入 "add ppt"、"添加ppt" 时，将当前对话内容暂存到临时文件，
  可多次调用以累积素材。
  第二阶段：用户输入 "show ppt"、"显示ppt"、"生成ppt" 时，读取所有累积内容，
  重新整理为 PPT 叙事风格，生成 Reveal.js 格式的 HTML 演示文稿。
  输出文件命名：日期_对话标题.html（如 20260301_Q1产品规划.html）。
  支持代码高亮、Markdown 格式、响应式布局，输出单个 HTML 文件可直接在浏览器中播放。
  采用正式商务简洁风格主题（深蓝/灰白专业配色）、思源黑体/微软雅黑中文字体体系。
---

# PPT Generator — Web 演示文稿生成器

## 概述

本技能采用**"先积累、后生成"**的两阶段工作流：

1. **`add ppt`（积累阶段）**：用户在对话过程中随时调用，将当前轮的关键内容暂存
2. **`show ppt`（生成阶段）**：用户准备好后调用，一次性整理所有素材并生成演示文稿

这种设计让用户可以在多轮对话中逐步积累 PPT 素材，而不是被迫在单次交互中一次性提供
所有内容。最终生成时，AI 会对所有素材进行重新组织，确保符合 PPT 叙事逻辑。

核心设计原则：
- **渐进式积累**：多次 `add ppt` 灵活收集素材，不打断对话节奏
- **叙事重组**：`show ppt` 时不是简单拼接，而是重新整理为符合 PPT 表达的内容
- **专业一致**：严格遵循商务汇报设计规范（配色、字体、排版）
- **即开即用**：输出单文件，双击即可在浏览器中演示

---

## 触发方式

### 积累阶段（暂存内容）
- `add ppt` / `添加ppt`

### 生成阶段（整理并输出）
- `show ppt` / `显示ppt`
- `生成ppt` / `make ppt`
- `create presentation` / `创建演示`

---

## 工作流程

### 第一阶段：`add ppt` — 内容暂存

用户在对话中输入 `add ppt` 时，执行以下操作：

**1. 提取当前轮的关键内容**

从最近一轮问答（用户提问 + Claude 回答）中提取核心信息，精简为适合 PPT 展示的
素材片段。提取时注意：
- 保留关键数据、结论、代码示例
- 去除对话性语言（"让我来看看"、"好的"等）
- 保留结构化信息（列表、表格、步骤）

**2. 追加到暂存文件**

将提取的内容追加写入 `<skill_path>/tmp/ppt_staging.md`，格式如下：

```markdown
<!-- SECTION: 2026-03-01 14:30 -->
## [从内容自动推断的小标题]

[提取的核心内容，Markdown 格式]

<!-- END SECTION -->
```

每次 `add ppt` 追加一个 `SECTION` 块。如果暂存文件不存在则创建。

**3. 向用户确认**

```
✅ 已添加到 PPT 素材库

📝 本次添加：[内容摘要，不超过一句话]
📊 当前累计：3 个内容片段
💡 继续对话后可再次 "add ppt"，或输入 "show ppt" 生成演示文稿
```

### 第二阶段：`show ppt` — 整理与生成

用户输入 `show ppt` 时，执行以下操作：

**1. 读取暂存文件**

读取 `<skill_path>/tmp/ppt_staging.md` 中所有累积的 `SECTION` 块。

如果暂存文件不存在或为空，提示用户：
```
⚠️ 暂无 PPT 素材。请先在对话中使用 "add ppt" 添加内容。
```

**2. 确认标题**

向用户确认 PPT 标题：
- 默认：从所有素材中自动推断一个概括性标题
- 用户可自定义

```
🎯 PPT 生成确认

📄 素材片段：5 个
📝 内容预览：
  1. 用户认证方案
  2. JWT Token 实现
  3. 安全最佳实践
  4. 性能优化建议
  5. 部署方案

📌 建议标题：用户认证系统设计方案
🗂️  文件名：20260301_用户认证系统设计方案.html

确认生成？可以修改标题。
```

**3. 内容重组**

这是关键步骤——**不是简单拼接暂存内容，而是重新组织为符合 PPT 叙事逻辑的结构**：

- **合并相关内容**：将同一主题的多个片段合并
- **建立叙事线**：按"背景 → 问题 → 方案 → 实施 → 总结"或类似逻辑重排
- **精简表达**：PPT 每页内容精炼，避免大段文字
- **提炼要点**：长段落转化为要点列表
- **补充过渡**：在章节之间添加逻辑过渡

重组后的内容写入 `<skill_path>/tmp/ppt_organized.md`，然后传入生成管线。

**4. 生成后清理暂存文件**

生成成功后，将 `tmp/ppt_staging.md` 重命名为 `tmp/ppt_staging_<日期>.md.bak`
（保留备份），然后清空暂存文件，为下一次素材积累做准备。

---

### 生成管线：内容解析与分页

`show ppt` 的第 3 步将重组后的 Markdown 传入以下管线：

使用 `scripts/markdown_parser.py` 将 Markdown 内容解析为幻灯片数据结构。

#### 分页规则

**规则 1：按二级标题分页**
```markdown
## 第一部分
内容...

## 第二部分
内容...
```
→ 生成 2 页幻灯片

**规则 2：按分隔符分页**
```markdown
内容 A

---

内容 B
```
→ 生成 2 页幻灯片

**规则 3：智能分段**
- 单页内容超过 300 字时，按段落自动拆分
- 代码块独立成页
- 列表项超过 7 条时拆分为多页

#### 特殊内容处理

**代码块**：使用 `code.html` 布局模板，启用语法高亮
**列表**：使用 `bullets.html` 布局模板，一次性显示所有列表项
**左右分栏**（`::: split ... ||| ... :::`）：使用 `split.html` 布局模板

---

### 生成管线：应用品牌样式与输出

使用 `templates/anthropic-theme.html` 作为基础模板。运行生成脚本：

```bash
python <skill_path>/scripts/generate_ppt.py \
  --content <skill_path>/tmp/ppt_organized.md \
  --title "演示标题" \
  --output <skill_path>/output/<YYYYMMDD>_<对话标题>.html
```

**输出文件命名规则**：`<YYYYMMDD>_<对话标题>.html`
- 日期部分：使用当天日期，格式 YYYYMMDD（如 20260301）
- 标题部分：从确认的 PPT 标题中提取，移除特殊字符，空格替换为下划线
- 示例：`20260301_Q1产品规划.html`、`20260301_用户认证方案.html`

生成完成后，向用户展示：

```
✅ PPT 生成成功！

📁 文件路径：output/20260301_用户认证方案.html
📊 幻灯片数：8 页
📝 素材来源：5 个对话片段
🎨 应用主题：Business Professional Theme

🚀 打开方式：双击文件在浏览器中打开

⌨️  操作说明：
  - 方向键/空格键：翻页
  - Esc：总览视图
  - F：全屏模式
  - S：演讲者模式
```

---

## 技术实现细节

### 依赖管理

**无需 Node.js 环境**，所有资源通过 CDN 加载：

```html
<!-- Reveal.js 核心 -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.css">
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5/dist/reveal.js"></script>

<!-- 代码高亮插件 -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5/plugin/highlight/monokai.css">
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5/plugin/highlight/highlight.js"></script>

<!-- Markdown 插件（可选） -->
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5/plugin/markdown/markdown.js"></script>

<!-- 字体 -->
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&family=Lora:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
```

### 幻灯片数据结构

Python 脚本内部使用的数据结构：

```python
slides = [
    {
        "layout": "title",        # 布局类型
        "title": "主标题",
        "subtitle": "副标题"
    },
    {
        "layout": "content",
        "title": "页面标题",
        "content": "Markdown 格式的内容",
        "accent_color": "orange"  # 本页强调色
    },
    {
        "layout": "code",
        "title": "代码示例",
        "language": "python",
        "code": "def hello():\n    print('Hello')"
    }
]
```

### Reveal.js 配置

```javascript
Reveal.initialize({
  // 主题配置
  width: 1280,
  height: 720,
  margin: 0.1,

  // 控件
  controls: true,
  progress: true,
  center: true,
  hash: true,

  // 过渡效果
  transition: 'slide',  // none/fade/slide/convex/concave/zoom

  // 插件
  plugins: [RevealHighlight, RevealMarkdown]
});
```

---

## 布局模板说明

### 1. title.html（标题页）
用于第一页，展示主标题和副标题。

```html
<section class="title-slide">
  <h1>{{title}}</h1>
  <p class="subtitle">{{subtitle}}</p>
  <p class="meta">{{date}} | 算酷团队</p>
</section>
```

### 2. content.html（通用内容页）
适用于普通文本内容。

```html
<section>
  <h2>{{title}}</h2>
  <div class="content">
    {{content}}  <!-- Markdown 渲染后的 HTML -->
  </div>
</section>
```

### 3. code.html（代码展示页）
专门用于代码块展示。

```html
<section>
  <h2>{{title}}</h2>
  <pre><code class="language-{{language}}" data-trim>
{{code}}
  </code></pre>
</section>
```

### 4. bullets.html（列表页）
用于要点列表，一次性显示所有条目。

```html
<section>
  <h2>{{title}}</h2>
  <ul>
    {{#bullets}}
    <li>{{.}}</li>
    {{/bullets}}
  </ul>
</section>
```

### 5. split.html（左右分栏页）
用于对比展示。

```html
<section>
  <h2>{{title}}</h2>
  <div class="split-layout">
    <div class="left">{{left_content}}</div>
    <div class="right">{{right_content}}</div>
  </div>
</section>
```

---

## 高级功能（可扩展）

### 演讲者备注
在 Markdown 中使用特殊语法添加备注（按 S 键查看）：

```markdown
## 幻灯片标题

内容...

Note:
这是只有演讲者能看到的备注。
```

### 嵌入媒体
支持图片、视频嵌入：

```markdown
## 架构图

![系统架构](https://example.com/arch.png)

<video src="demo.mp4" controls></video>
```

---

## 边界情况处理

**极短内容（< 50 字）**：
- 仅生成标题页，将内容作为副标题展示

**极长内容（> 5000 字）**：
- 警告用户内容过长，建议精简或分段
- 自动按段落智能分页（每页不超过 300 字）

**包含大量代码**：
- 代码块自动调整字号以适应页面
- 超长代码添加滚动条

**特殊字符处理**：
- HTML 标签自动转义（防止破坏布局）
- Markdown 中的 `<` `>` `&` 等字符正确渲染

**无标题内容**：
- 使用"幻灯片 1"、"幻灯片 2" 作为默认标题

**重复生成**：
- 文件名冲突时自动追加序号（`20260301_方案_2.html`）

**`add ppt` 时无对话内容**：
- 如果当前轮没有实质性问答内容，提示用户先进行对话后再添加

**暂存文件已有大量内容**：
- `show ppt` 时如果素材超过 10 个片段，建议用户确认是否全部纳入

---

## 输出规范

### 文件命名
- 格式：`<YYYYMMDD>_<对话标题>.html`
- 日期：当天日期，8 位数字
- 标题：从 PPT 标题推断，移除特殊字符，空格替换为下划线，截断至 40 字符
- 示例：`20260301_Q1产品规划.html`、`20260301_用户认证方案.html`

### 文件大小
- 单文件通常 < 100KB（不含嵌入的媒体文件）
- CDN 资源按需加载，离线可用需手动下载依赖

### 浏览器兼容性
- 现代浏览器全支持（Chrome、Firefox、Safari、Edge）
- 移动端浏览器支持触摸滑动

---

## 与其他技能的协作

**与 doc-analyzer 协作**：
- 分析文档后，用户可要求"将这份分析结果生成 PPT"
- 自动将结构化分析内容转换为幻灯片

**与 doc-classifier 协作**：
- 对分类后的文档批量生成索引演示
- 用 PPT 形式展示文档分类统计

---

## 核心原则

1. **`add ppt` 轻量快速** — 只做内容提取和暂存，不打断对话节奏
2. **`show ppt` 重新整理** — 不是简单拼接，而是重新组织叙事结构
3. **生成前必须确认标题** — 避免生成用户不需要的内容
4. **输出单文件，无依赖** — 用户可直接分享和播放
5. **严格遵循商务汇报规范** — 配色、字体、排版保持专业一致
6. **内容为王，效果适度** — 不过度使用动画，保持专业感

---

## 文件结构参考

```
ppt-generator/
├── SKILL.md                          # 本文件（AI 指令）
├── README.md                         # 用户使用文档
├── .gitignore
├── templates/
│   ├── anthropic-theme.html          # 主模板
│   └── slide-layouts/
│       ├── title.html
│       ├── content.html
│       ├── code.html
│       ├── bullets.html
│       └── split.html
├── scripts/
│   ├── generate_ppt.py               # 主生成脚本
│   ├── markdown_parser.py            # 内容解析器
│   └── utils.py                      # 工具函数
├── tmp/                              # 临时文件
│   ├── ppt_staging.md               # 素材暂存文件（add ppt 追加写入）
│   └── ppt_organized.md             # 重组后的内容（show ppt 生成前写入）
└── output/                           # 生成的 PPT 文件（日期_标题.html）
```

---

## 使用示例

### 场景 1：多轮对话积累后生成 PPT

```
用户: 如何实现 JWT 认证？
Claude: [详细回答 JWT 认证的实现方法...]

用户: add ppt
Claude: ✅ 已添加到 PPT 素材库
  📝 本次添加：JWT 认证实现原理与流程
  📊 当前累计：1 个内容片段

用户: Token 刷新机制怎么设计？
Claude: [详细回答 Token 刷新机制...]

用户: add ppt
Claude: ✅ 已添加到 PPT 素材库
  📝 本次添加：Token 刷新机制设计方案
  📊 当前累计：2 个内容片段

用户: 安全方面有什么注意事项？
Claude: [详细回答安全最佳实践...]

用户: add ppt
Claude: ✅ 已添加到 PPT 素材库
  📝 本次添加：JWT 安全最佳实践
  📊 当前累计：3 个内容片段

用户: show ppt
Claude:
  🎯 PPT 生成确认
  📄 素材片段：3 个
  📌 建议标题：JWT 认证系统设计方案
  🗂️  文件名：20260301_JWT认证系统设计方案.html
  确认生成？

用户: 确认
Claude: ✅ 已生成 output/20260301_JWT认证系统设计方案.html（12 页）
```

### 场景 2：单次添加后立即生成

```
用户: 帮我分析一下这个数据库性能问题
Claude: [详细分析...]

用户: add ppt
Claude: ✅ 已添加（1 个片段）

用户: show ppt
Claude: [整理并生成 PPT]
```

### 场景 3：配合 doc-analyzer 使用

```
用户: 帮我分析这个会议纪要
Claude: [使用 doc-analyzer 分析文档...]

用户: add ppt
Claude: ✅ 已添加分析结果到 PPT 素材库

用户: show ppt
Claude: [将分析结果整理为 PPT 叙事格式并生成]
```
