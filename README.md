# 软件工程文档编写 Skill

给 Agent 用的软件工程文档编写指令：封面、变更履历、章节大纲、编号规则和检查清单都以 `文档示例/` 里的模板为准。

本仓库既是 **Cursor / Claude Code skill**，也带一套可复制的 Word / Excel / PPT 模板。

## 为什么旧版经常「不生效」

旧结构有这些问题，现已对掉：

| 问题 | 现况 |
|---|---|
| `SKILL.md` 放在子目录 `software-engineering-docs/`，克隆到 skills 目录后发现不了 | 根目录就是 `SKILL.md` |
| description 只概述「提供指导」，Agent 当可选参考 | description 用 MUST + 中英触发词 |
| 正文是目录说明，没有强制工作流 | 先路由 → 读规范 → 读章节 → 自检 |
| 模板路径写成项目根目录 `01 计划阶段/` | 统一为 `文档示例/...`，且相对 **skill 根目录** |
| `writing-guidelines.md` 只在文末链接，经常不读 | 工作流第 2 步必读 |
| 没有各文档「必写章节 / 必写表 / 固定句式」 | 见 `references/` |

## 只有一个 skill

名称始终是 **`software-engineering-docs`**。仓库是源码，安装目录才是 Agent 真正加载的位置。每种工具只装一份：

| 你用的工具 | 只保留这一份 |
|---|---|
| Cursor | `~/.cursor/skills/software-engineering-docs` |
| Claude Code | `~/.claude/skills/software-engineering-docs` |

不要在 Cursor 里同时放 `~/.cursor/skills` 和 `~/.claude/skills` 两份同名 skill，列表里会显示成「两个」。

## 安装

把**整个仓库**克隆到 skills 目录（需要 `文档示例/` 才能套模板）：

```bash
# Cursor（个人 skill，所有项目可用）
git clone <本仓库 URL> ~/.cursor/skills/software-engineering-docs

# Claude Code（仅在使用 Claude Code 时再装一份）
git clone <本仓库 URL> ~/.claude/skills/software-engineering-docs
```

Windows 示例：

```bash
git clone <本仓库 URL> "$HOME/.cursor/skills/software-engineering-docs"
```

若 Agent 未自动加载，在对话里明确说：`使用 software-engineering-docs 写【文档类型】`。

## 使用

直接下指令即可，例如：

- 「按本 skill 写一份《XX 系统需求规格说明书》」
- 「填写提测申请单，模块编号沿用 SRS」
- 「出本周项目周报，进度 62%，预期 70%」

Agent 应：锁定文档类型 → 读 `writing-guidelines.md` → 读对应 `references/*.md` → 按模板大纲成文 → 跑检查清单。

缺项目事实时写「待确认」，不应编造合同号、BUG 数、进度百分比。

## 仓库结构

```
SKILL.md                 # 触发、铁律、工作流、文档路由
writing-guidelines.md    # 封面、变更履历、文档介绍句式、图表与术语
references/              # 各阶段大纲、表格列名、检查清单
文档示例/                # 模板与示例（docx / xlsx / pptx）
README.md
LICENSE
```

### 文档示例目录

- `01 计划阶段`：可行性分析、项目信息表、实施方案、进度计划/简表
- `02 需求阶段`：需求规格说明书
- `03 设计阶段`：功能设计说明书、数据库设计说明书
- `04 开发阶段`：系统提测申请单
- `05 测试阶段`：测试用例、测试报告、测试计划
- `06 验收阶段`：竣工报告、安装维护手册、培训文档、使用手册
- `99 其他模板`：会议纪要、周报、月报、进度简报、工时、进度确认单

## 打包

```bash
python -c "import zipfile, pathlib; root=pathlib.Path('.');
files=['SKILL.md','writing-guidelines.md']+list(map(str, pathlib.Path('references').glob('*.md')));
out='software-engineering-docs.skill';
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for f in files:
        z.write(f, 'software-engineering-docs/'+f.replace('\\\\','/'))
print('wrote', out, 'files', len(files))"
```

`.skill` 只含指令，不含 `文档示例/`。完整使用请克隆仓库。

## License

MIT（见 `LICENSE`）
