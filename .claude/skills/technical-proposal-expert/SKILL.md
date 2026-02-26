---
name: technical-proposal-expert
description: Multi-scenario document writing for Chinese formal documents. Use when user wants to write documents (e.g. technical proposals, bidding docs, design reports, test reports, weekly reports) or has not specified document type and needs scene selection. This skill first asks what document to write, matches the best scenario (technical-proposal / design-report / test-report / weekly-report), or falls back to general; then confirms document usage scenario and user identity so output fits the reader and context, optionally builds a temporary txt glossary of industry terms for polish; loads the corresponding reference and applies shared writing rules (no AI-sounding phrases, narrative over bullets, logical flow).
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

### 3. 确认使用场景与用户身份（必做）

无论写哪类文档，在正式撰写前都须先明确两点，以便写出更符合其身份与定位的文档：

- **文档使用场景**：文档给谁看、在什么场合用（如内部汇报、对外投标、甲方验收、留档备查等）。
- **用户身份/角色**：撰写者或文档代表方的身份（如乙方技术负责人、项目经理、测试负责人、一线研发等）。

根据上述信息调整语气、详略、侧重点与称谓，使成品更贴合使用场景与身份定位。若用户未主动提供，可简短追问后再进入下一步。

### 4. 加载场景指引

匹配到场景后，**必须读取**本 skill 目录下对应的 reference 文件（`references/<场景标识>.md`），并按其中流程与约束执行。通用写作要求（见下）与场景指引**同时生效**。

### 5. 行业用语 / 专有名词（可选，润色用）

可与用户确认是否需要使用**行业黑话、专有名词、专业词汇**（如领域术语、公司/项目惯用语、行话等）。若用户确认需要：

- 在确认后生成一份**临时 txt**（如 `writing-glossary-temp.txt` 或用户指定名），将约定好的词条写入该文件，便于撰写时查阅。
- 在写作中**按场景适当融入**这些用语，作为润色的一部分；**不必处处使用**，仅在符合上下文与场景时自然带入，避免生硬堆砌。若当前文档场景偏通用或用户未提供词条，可不使用或仅少量使用。

### 6. 执行与输出

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
3. **使用场景与身份**：撰写前确认文档使用场景（给谁看、什么场合）和用户身份/角色，使文档更符合其定位。
4. **加载 reference**：匹配后必须读取 `references/<场景>.md` 并执行其中指引。
5. **行业用语（可选）**：可与用户确认行业用语/专有名词后生成临时 txt，在写作中**按场景适当**融入，仅作润色，不强行堆砌。
6. **通用要求**：全文遵守禁词表、去列表化原则、逻辑连接与输出控制；场景专属约束见各 reference。
