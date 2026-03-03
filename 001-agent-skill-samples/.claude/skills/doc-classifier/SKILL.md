---
name: doc-classifier
description: >
  智能文档分类归档工具。当用户需要对一批混合文档进行分类、整理、归档时触发此技能。
  触发词包括："整理文档"、"文档分类"、"归档文件"、"分类整理"、"organize documents"、
  "classify files"、"sort documents"。也适用于用户有一堆混乱的文件（会议纪要、报告、
  合同、方案、附件、Excel数据表）需要按内容自动分类到结构化目录的场景。
  支持的文件类型：PDF、Word(.docx/.doc)、Excel(.xlsx/.xls/.csv)、
  PowerPoint(.pptx)、Markdown、纯文本、图片及压缩包附件。
  即使用户只是说"帮我整理一下这些文件"或"把文档归个类"也应触发此技能。
  不适用于：单文件阅读摘要、文件格式转换、文档创建。
---

# Doc Classifier — 智能文档分类归档

## 概述

本技能实现"环境准备→扫描→阅读→分类→归档→索引"的全流程文档整理。

两个核心设计原则：**环境自治**——通过 uv 管理虚拟环境和依赖，无需用户手动安装任何 Python 包；**速度优先**——通过批处理脚本一次性提取所有文档文本，避免逐文件串行处理。

---

## 第一步：环境准备（必须最先执行）

在执行任何文档操作之前，**必须**先确保 uv 虚拟环境就绪。本技能使用 uv 管理独立的 Python 虚拟环境，所有第三方依赖（pdfplumber、pandas、openpyxl 等）都安装在此环境中，不会污染系统 Python。

本技能完整支持 **Windows、macOS、Linux** 三个平台。

### 方式一：自动引导（推荐，全平台通用）

直接运行批量提取脚本即可。脚本内置了跨平台的自引导机制——启动时自动检测当前操作系统，定位或安装 uv，创建虚拟环境并安装全部依赖，然后切换到虚拟环境重新执行。整个过程对用户透明，无需手动干预。

```bash
# Linux / macOS / Windows（所有平台命令相同）
python <skill_path>/scripts/batch_extract.py <源文件夹路径> --output <skill_path>/tmp/extracted.json
```

脚本的自引导流程如下：检测当前 Python 是否在 `<skill_path>/.venv/` 中运行。如果不是，查找系统中的 `uv` 命令（找不到则自动安装——Windows 使用 PowerShell 安装脚本，macOS/Linux 使用 shell 安装脚本）。创建虚拟环境（自动适配平台路径：Windows 用 `Scripts\python.exe`，macOS/Linux 用 `bin/python`）。用 `uv pip install` 安装全部依赖。用虚拟环境的 Python 重新执行自身脚本。

### 方式二：手动引导（调试或定制化场景）

根据操作系统选择对应的引导脚本：

**Linux / macOS:**
```bash
# 创建环境 + 安装依赖 + 自动激活
source <skill_path>/scripts/setup_env.sh

# 后续命令在已激活的虚拟环境中执行
python <skill_path>/scripts/batch_extract.py <源文件夹路径>
```

**Windows PowerShell:**
```powershell
# 创建环境 + 安装依赖
.\scripts\setup_env.ps1

# 激活虚拟环境
& .\.venv\Scripts\Activate.ps1

# 运行提取脚本
python .\scripts\batch_extract.py <源文件夹路径>
```

**Windows CMD:**
```cmd
REM 自动调用 PowerShell 完成环境引导
scripts\setup_env.bat

REM 激活虚拟环境
.venv\Scripts\activate.bat

REM 运行提取脚本
python scripts\batch_extract.py <源文件夹路径>
```

### 方式三：uv run 一步到位

如果系统已安装 uv，可以直接使用 `uv run` 命令，它会自动处理虚拟环境和依赖：

```bash
uv run --project <skill_path> python <skill_path>/scripts/batch_extract.py <源文件夹路径>
```

### 依赖清单

所有依赖声明在 `pyproject.toml` 中，供 uv 自动解析安装：

| 包名 | 用途 | 为什么需要 |
|------|------|-----------|
| pdfplumber | PDF文本和表格提取 | pdftotext 命令行工具的 Python 备选方案 |
| pypdf | PDF元数据读取 | 提取标题、作者等分类辅助信息 |
| pandas | 数据读取与分析 | Excel/CSV/TSV 的列名和数据摘要提取 |
| openpyxl | XLSX读写引擎 | pandas 读取 .xlsx 的底层依赖 |
| xlrd | XLS旧版支持 | 处理 Excel 97-2003 格式(.xls) |
| markitdown | Office文档转Markdown | PPT/Word 的通用快速文本提取器 |
| chardet | 编码检测 | 自动识别 GBK/GB2312 等中文编码文件 |

### 可选系统工具（提速用，非必须）

以下工具如果已安装会被优先使用以加快提取速度，不安装也不影响功能（脚本会自动回退到 Python 库）：

| 工具 | 用途 | 安装方式 |
|------|------|---------|
| pdftotext | PDF 文本提取（最快） | Linux: `apt install poppler-utils`，macOS: `brew install poppler`，Windows: 下载 poppler for Windows |
| pandoc | Word/Markdown 转换 | Linux: `apt install pandoc`，macOS: `brew install pandoc`，Windows: `winget install pandoc` |
| LibreOffice | .doc 旧格式转换 | Linux: `apt install libreoffice`，macOS: `brew install --cask libreoffice`，Windows: 官网安装 |

### 虚拟环境位置与文件结构

环境创建后，技能目录结构如下：

```
doc-classifier/
├── SKILL.md                 # 本文件（技能指令）
├── pyproject.toml           # 依赖声明
├── tmp/                     # 临时文件
├── scripts/
│   ├── batch_extract.py     # 批量提取脚本（内置跨平台自引导）
│   ├── setup_env.sh         # 手动引导 — Linux / macOS
│   ├── setup_env.ps1        # 手动引导 — Windows PowerShell
│   └── setup_env.bat        # 手动引导 — Windows CMD（调用 ps1）
└── .venv/                   # uv 创建的虚拟环境（自动生成，不提交到 Git）
    ├── bin/python            # Linux/macOS 的 Python
    ├── Scripts/python.exe    # Windows 的 Python
    └── lib/                  # 已安装的依赖
```

### 跨平台兼容性说明

脚本在以下方面做了跨平台适配：

**虚拟环境路径**：自动检测操作系统，Windows 使用 `.venv\Scripts\python.exe`，macOS/Linux 使用 `.venv/bin/python`。

**uv 安装方式**：Windows 使用 `irm https://astral.sh/uv/install.ps1 | iex`（PowerShell），macOS/Linux 使用 `curl | sh`。

**进程重启机制**：使用 `subprocess.run + sys.exit` 代替 `os.execv`，后者在 Windows 上不会正确终止父进程。

**Python 命令**：Windows 上使用 `python`（Windows 可能没有 `python3` 命令），macOS/Linux 使用 `python3`（避免指向 Python 2）。

**LibreOffice 定位**：自动搜索各平台的安装路径——Linux 查找 `/usr/bin/soffice`，macOS 查找 `/Applications/LibreOffice.app/Contents/MacOS/soffice`，Windows 查找 `C:\Program Files\LibreOffice\program\soffice.exe`。

**文件编码**：使用 `chardet` 自动检测编码，处理 GBK/GB2312 等中文编码文件（在中文 Windows 上尤其常见）。

---

## 第二步：确认范围

在开始处理文档前，与用户确认三个参数：

**源目录**：待整理的文档在哪里？例如 `./raw-docs/`、`./downloads/`。

**输出根目录**：整理后的文件放哪？默认规则是在源目录同级创建 `referencess/` 文件夹。

**分类侧重**：全面分类，还是只关注特定类型（如只整理会议纪要）？

用户没指定则使用合理默认值，执行前确认。

---

## 第三步：扫描与批量提取

运行批量提取脚本（脚本会自动处理环境问题）：

```bash

python <skill_path>/scripts/batch_extract.py /path/to/source --output /<skill_path>/tmp/extracted.json
```

脚本针对每种文件类型使用最快的提取策略：

**PDF** 优先用 `pdftotext` 命令行工具（最快，直接提取文本流），失败则回退到 `pdfplumber`（Python库，处理复杂布局更稳定）。如果两者都提取为空，说明可能是扫描件，标记为"需OCR"。

**Word .docx** 优先用 `pandoc` 转纯文本（一条命令完成），失败则解压 docx 直接读 XML 中的文本节点。

**Word .doc（旧版）** 需要 LibreOffice 先转 .docx，再按上面的流程提取。这是最慢的路径，旧版 .doc 无法避免。

**Excel .xlsx/.xls/.csv** 用 `pandas` 只读 sheet 名、列名和前10行数据。分类判断不需要完整的数据内容，只需要知道这是什么类型的表格。

**PowerPoint .pptx** 用 `markitdown` 将幻灯片转为 Markdown 文本。失败则解压读 XML。

**Markdown/纯文本** 用 `chardet` 自动检测编码后直接读取前2000字符。

**图片/压缩包** 不提取文本，仅记录文件名和大小，标记为附件候选。压缩包会列出内部文件名清单。

提取完成后，向用户展示扫描摘要：

> "扫描完成：共发现 35 个文件（Word 15、PDF 8、Excel 5、PPT 3、图片 3、其他 1），已提取全部文本摘要，准备分类。"

---

## 第四步：内容分析与分类

加载 `extracted.json`，对每个文档沿四个维度进行分类判断。

### 类别维度（最核心）

根据文档的结构特征和关键词判断大类。

会议纪要类文档通常包含参会人员名单、会议议题列表、讨论记录、决议事项、待办任务及责任人。进一步按会议类型细分为周会、月会、专题会议、评审会、启动会等。

项目文档类包含项目计划、进度报告、需求规格、设计文档、测试报告。按项目阶段细分为立项、需求、设计、开发、测试、验收。

合同协议类包含法律条款、甲乙方信息、签署日期、合同金额。按类型细分为采购合同、服务协议、保密协议、框架协议。

报告类包含数据分析、工作总结、阶段性汇报。按周期细分为日报、周报、月报、季报、年报。

技术方案类包含架构设计、技术选型、实施方案、解决方案。

通知公告类包含政策通知、人事变动、制度发布。

培训材料类包含培训课件（通常是PPT）、学习手册、考核试题。

数据报表类主要是Excel文件，包含统计数据、财务数据、业务数据。

### 主体维度

识别文档关联的组织实体——公司名称、部门名称或项目名称。通过文档标题、页眉页脚、正文中反复出现的组织名称来判断。

### 时间维度

提取文档的时间信息。优先级：文件名中的日期 > 文档内容中的日期 > 文件修改时间。格式统一为 `YYYY-MM`。

### 子类型维度

在大类内部进一步细分，如会议纪要下的"周会"与"专题会议"，报告下的"月报"与"年报"。

### 附件识别与归属

一个文件被判定为附件需满足以下**任一**条件：它是图片/压缩包文件；文件名中包含"附件"字样；文件名与另一个文档高度关联（如 `XX会议_附件1.xlsx` 对应 `XX会议纪要.docx`）；它是独立数据文件且属于某主文档的补充材料。

附件归属判断：首先检查文件名关联（共享前缀或关键词），其次检查主文档内容中是否引用了该文件名，最后检查时间和主题关联性。附件放入所属分类的 `附件/` 子文件夹。

---

## 第五步：生成分类方案（必须等用户确认）

**在移动任何文件之前**，必须先向用户展示完整的分类方案：

```
references/
├── 会议纪要/
│   ├── ABC科技公司/
│   │   ├── 2025-01/
│   │   │   ├── 第1周_周会纪要.docx
│   │   │   ├── 第2周_周会纪要.docx
│   │   │   └── 附件/
│   │   │       └── 周会数据汇总.xlsx
│   │   └── 2025-02/
│   │       └── 需求评审会纪要.docx
│   └── XYZ项目组/
│       └── 2025-01/
│           └── 项目启动会纪要.docx
├── 数据报表/
│   └── 财务部/
│       └── 月度财务报表.xlsx
├── 未分类/
│   └── readme.txt
└── INDEX.md
```

提问用户："以上是建议的分类方案，是否需要调整？" **只有得到确认后才执行文件操作。**

目录层级自适应规则：类别下文件少于5个时省略月份层级；只有一个主体时省略主体层级；无法识别时间时省略时间层级。目录结构要**实用**，不为层次而层次。

---

## 第六步：执行文件归档

```bash
# 创建目录
mkdir -p "references/会议纪要/ABC科技公司/2025-01/附件"

# 默认用 cp（安全），用户确认后可自行删除原文件
cp "source/周会纪要_0106.docx" "references/会议纪要/ABC科技公司/2025-01/"
cp "source/周会数据.xlsx" "references/会议纪要/ABC科技公司/2025-01/附件/"
```

**安全策略**：默认 `cp`（复制）。仅在用户明确要求时使用 `mv`（移动）。

**文件名冲突**：目标已存在同名文件时追加序号，如 `文件名_2.docx`。

**保留原名**：默认保持原始文件名，除非用户要求统一命名。

---

## 第七步：生成索引报告

在输出根目录生成 `INDEX.md`，包含文件统计概览、分类明细表、附件关联表、未分类清单及原因。

```markdown
# 文档分类索引

> 生成时间: 2025-03-01 | 源目录: ./raw-docs/ | 总计: 35 文件（已分类: 33，未分类: 2）

## 📋 会议纪要（12 个文件）

### ABC科技公司

| 文件名 | 日期 | 会议类型 | 核心议题 | 待办数 |
|--------|------|---------|---------|-------|
| 第1周_周会纪要.docx | 2025-01-06 | 周会 | 项目进度review | 3 |
| ↳ 附件: 周会数据汇总.xlsx | | | | |

## ❓ 未分类（2 个文件）

| 文件名 | 原因 |
|--------|------|
| readme.txt | 非业务文档 |
```

---

## 边界情况处理

**无法读取的文件**（加密PDF、损坏文档、密码保护的Excel）放入 `未分类/`，索引中注明原因。

**混合内容文档**按**主要用途**分类，索引中标注次要类别。

**重复文件**（文本摘要高度相似）保留一个，索引中标注重复项。

**大批量文件（50+）** 批量提取脚本本身不受限制，AI分类时每批处理20个文件摘要。

**非中文文档**自动适配语言，用户可指定统一使用中文或英文类别名。

**uv 不可用的环境**：如果运行环境无法安装 uv（如某些受限服务器或企业内网），脚本会给出明确错误提示。此时可手动安装依赖后直接运行，在 Linux/macOS 上执行 `pip3 install pdfplumber pypdf pandas openpyxl xlrd markitdown chardet`，在 Windows 上执行 `pip install pdfplumber pypdf pandas openpyxl xlrd markitdown chardet`，然后用系统 Python 直接运行 `batch_extract.py`（脚本检测到已在虚拟环境或依赖已就绪时会跳过自引导）。

---

## 核心原则

执行文件操作前必须获得用户确认。默认用 `cp` 不用 `mv`。每次必须生成 INDEX.md。拿不准就放 `未分类/`。不碰用户指定范围外的文件。附件跟随主文档分类，放在 `附件/` 子文件夹。