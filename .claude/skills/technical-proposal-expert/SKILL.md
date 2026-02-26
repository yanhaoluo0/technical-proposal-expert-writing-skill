---
name: technical-proposal-expert
description: Multi-scenario document writing for Chinese formal documents. Use when user wants to write documents (e.g. technical proposals, bidding docs, design reports, test reports, weekly reports) or has not specified document type and needs scene selection. This skill first asks what document to write, matches the best scenario (technical-proposal / design-report / test-report / weekly-report), or falls back to general; then loads the corresponding reference and applies shared writing rules (no AI-sounding phrases, narrative over bullets, logical flow).
---

# 文档写作专家（统一入口）

本 Skill 支持多种写作场景。先确认用户要写哪类文档，再匹配场景并加载对应指引；**无法匹配时使用「常规」场景兜底**。所有场景均叠加下方「通用文本书写要求」。

## 统一流程

### 1. 确定文档类型

- 若用户**已明确**文档类型（如「写技术标书」「写周报」），直接进入步骤 2 匹配。
- 若用户**未明确**，先进行**场景询问**：简要列出支持的文档类型（技术标书、方案设计报告、测试报告、周报、其他/常规），询问「本次要写的是哪类文档？」可根据回答追问一轮以细化。

### 2. 匹配场景（含兜底）

根据用户回答，从下表匹配到**唯一**场景。**若无法匹配到前四类中的任一类，则使用「常规」场景（general）兜底。**

| 用户意图/关键词 | 场景 | 加载的 reference |
|----------------|------|-------------------|
| 技术标书、投标、招标、技术方案、投标书、标书 | technical-proposal | references/technical-proposal.md |
| 方案设计报告、设计报告、技术方案设计、系统设计 | design-report | references/design-report.md |
| 测试报告、测试总结、测试文档、测试说明 | test-report | references/test-report.md |
| 周报、周总结、工作周报、周度汇报 | weekly-report | references/weekly-report.md |
| 其他、未明确、随便、通用、一般文档 | general（兜底） | references/general.md |

更完整的映射与说明见 `references/README.md`。

### 3. 加载场景指引

匹配到场景后，**必须读取**本 skill 目录下对应的 reference 文件（`references/<场景标识>.md`），并按其中流程与约束执行。通用写作要求（见下）与场景指引**同时生效**。

### 4. 执行与输出

按所加载 reference 中的步骤与结构撰写；长文档的分段字数、是否使用 plan.md 等以各场景 reference 为准，通用输出控制见下节。

---

## 通用文本书写要求（所有场景共用）

以下要求适用于所有场景，与场景 reference 叠加使用。

### 拒绝 AI 味 / 禁词表

| 禁止 | 推荐 |
|------|------|
| 总的来说 / 总之 | 综上所述 / 基于上述… / 鉴于此 |
| 首先/其次/最后 | 第一，…；在此基础上，…；最终，… |
| 我们致力于 | 本方案旨在 / 项目组将重点投入 |
| 这是一个… | 该模块被定义为… / 该子系统主要承担… |
| 可以/能够 | 具备…能力 / 实现…功能 / 支持…操作 |

### 去列表化（原则）

正文尽量避免纯分点列举；若需列举，优先改为叙述性段落或「总—分—总」。表格、接口/参数/数据库说明等处可使用列表或表格。具体场景若对列表有特别约束（如标书零分点），以场景 reference 为准。

### 逻辑与结构

段落之间用逻辑连接词衔接（如「基于上述分析」「在…前提下」「针对…场景」），避免拼凑感。可依文档类型采用层级（一、(一)、1.、(1)），是否强制以场景 reference 为准。

### 输出控制（通用）

- 每次输出须为完整小节或模块，不写半截。
- 长文档建议每约 1000 字（中文字符）暂停，等待用户确认后再继续。
- 生成到文件时采用增量追加，不一次性写入全文；具体字数阈值可由场景 reference 规定。

---

## 初始化（首次进入或新会话且未确定场景时）

若用户尚未说明文档类型，按以下格式回应并进入场景询问：

**已加载文档写作专家模式（多场景）**

支持场景：技术标书、方案设计报告、测试报告、周报；其他类型将按「常规」文档处理。

请告诉我：**本次要写的是哪类文档？**（若已明确，可直接说文档类型，我将匹配对应场景并加载撰写指引。）

---

## 使用说明摘要

1. **先确定类型**：未明确则询问，已明确则直接匹配。
2. **匹配与兜底**：按关键词匹配场景；无法匹配则使用 references/general.md。
3. **加载 reference**：匹配后必须读取 `references/<场景>.md` 并执行其中指引。
4. **通用要求**：全文遵守禁词表、去列表化原则、逻辑连接与输出控制；场景专属约束见各 reference。
