

# technical-proposal-expert

项目名称与 skill 名称均为 **`technical-proposal-expert`**。

中文正式文档写作 skill：技术标书、方案设计报告、测试报告、周报；其余走常规兜底。根目录 `SKILL.md` 是唯一入口。

## 安装

把整个仓库克隆到 skills 目录：

```bash
git clone https://github.com/yanhaoluo0/technical-proposal-expert-writing-skill.git ~/.cursor/skills/technical-proposal-expert
```

Claude Code：

```bash
git clone https://github.com/yanhaoluo0/technical-proposal-expert-writing-skill.git ~/.claude/skills/technical-proposal-expert
```

每种工具只装一份。Cursor 不要同时保留 `~/.cursor/skills` 与 `~/.claude/skills` 下的同名 skill。

未自动加载时，在对话里说：`使用 technical-proposal-expert 写【文档类型】`。

## 使用

直接说要写的文档即可，例如「写技术标书」「出方案设计报告」「写测试报告」「写周报」。类型不明时会先问场景，再读对应 `references/`。

## 结构

```
SKILL.md                          # 发现、铁律、路由、通用书写要求
references/technical-proposal.md  # 标书：零分点、plan.md、需求响应
references/design-report.md       # 设计报告 1–11 章
references/test-report.md
references/weekly-report.md
references/general.md             # 兜底
```
