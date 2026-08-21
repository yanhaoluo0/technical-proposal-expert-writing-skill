---
name: technical-proposal-expert
description: MUST be used when writing, drafting, or polishing Chinese formal documents. Use when the user asks for 技术标书, 投标, 招标, 技术方案, 投标书, 方案设计报告, 系统设计说明, 测试报告, 测试总结, 工作周报, 周总结, or unspecified 公文/方案/文档. Also use when the document type is unclear and a writing scene must be chosen first.
---

# technical-proposal-expert

把本 skill 当作强制指令集。写中文正式文档时，先完成本文件流程，再动笔。

**违反条文等于违反精神。** 不能用「先写个草稿」「通用公文更快」「用户没点名 skill」跳过匹配和读 reference。

## 铁律

1. **先匹配场景，再写。** 未锁定场景、未读取对应 reference 之前，禁止输出正文。
2. **场景 reference 优先于通用知识。** 标书的零分点、设计报告的章节骨架，以 reference 为准。
3. **通用书写要求与场景指引同时生效。** 禁词表、去列表化、分段确认对所有场景有效。
4. **缺信息先问或写「待确认」，禁止编造** 指标、业绩、测试数据、招标条款编号。

## 工作流

复制并跟踪：

```
- [ ] 1. 确定文档类型（未明确则询问，已明确则直接匹配）
- [ ] 2. 匹配唯一场景；冲突则问 1 句；都不中则 general
- [ ] 3. 确认文档使用场景（给谁看、什么场合）和撰写身份
- [ ] 4. 读取对应 references/*.md（整份）
- [ ] 5. 按该 reference 撰写；遵守下方通用书写要求
- [ ] 6. 当前小节写完后自检禁词与列表；长文按约 1000 字暂停
```

行业用语为可选项：用户明确需要时，再生成临时词表（如 `writing-glossary-temp.txt`），只在上下文合适时自然带入，禁止堆砌。

## 场景路由

| 用户说法 | 场景 | 必须读取 |
|---|---|---|
| 技术标书、投标、招标、投标书、标书 | technical-proposal | [references/technical-proposal.md](references/technical-proposal.md) |
| 方案设计报告、设计报告、系统设计、研制方案 | design-report | [references/design-report.md](references/design-report.md) |
| 测试报告、测试总结、测试说明 | test-report | [references/test-report.md](references/test-report.md) |
| 周报、周总结、工作周报、周度汇报 | weekly-report | [references/weekly-report.md](references/weekly-report.md) |
| 其他、未明确、通用、一般文档 | general | [references/general.md](references/general.md) |

**歧义**：只说「技术方案」、未提投标/设计时，问一句是「投标技术标」还是「方案设计报告」，不要两套一起写。

同一对话锁定场景后不要中途更换，除非用户明确要求切换。

未说明类型时，用下面这段询问（不要先写正文）：

> 已加载 technical-proposal-expert。支持：技术标书、方案设计报告、测试报告、周报；其他按常规文档处理。本次要写哪类文档？

## 撰写前必确认

- **使用场景**：给谁看、什么场合（对外投标、内部汇报、甲方验收、留档等）
- **身份**：撰写者或代表方（乙方技术负责人、项目经理、测试负责人等）

据此调整语气、详略与称谓。用户没给就简短追问，不要默认成空泛「我司」。

## 通用文本书写要求

### 禁词

| 禁止 | 改为 |
|---|---|
| 总的来说 / 总之 | 综上所述 / 基于上述… / 鉴于此 |
| 首先/其次/最后 | 第一，…；在此基础上，…；最终，… |
| 我们致力于 | 本方案旨在 / 项目组将重点投入 |
| 这是一个… | 该模块被定义为… / 该子系统主要承担… |
| 可以/能够 | 具备…能力 / 实现…功能 / 支持…操作 |

### 去列表化

正文避免纯分点。优先叙述或「总—分—总」。表格、接口、参数、库表、清单可用列表或表。场景若规定「零分点」（标书），以该场景为准。

### 逻辑

段落用「基于上述分析」「在…前提下」「针对…场景」衔接。层级是否强制（`一、` / `1.1`）看场景 reference。

### 输出

- 每次输出完整小节或模块，不写半截
- 长文档约每 1000 个中文字符暂停，等用户确认再继续
- 写入文件时增量追加，不一次写完全文

## 找借口对照

| 借口 | 事实 |
|---|---|
| 用户只要一段正文 | 仍要先匹配场景并读 reference |
| 先按通用 SRS/方案写 | 场景骨架在 reference 里 |
| 禁词太严、先写后改 | 按禁词表直接写 |
| 标书用 bullet 更清晰 | 标书零分点；表结构除外 |
| 没说身份也能写 | 未提供则追问，不编造甲方/乙方口吻 |

## 红旗 — 停下重来

- 还没读对应 reference 就开始写
- 标书正文出现 `-` / `*` 分点
- 编造招标条款号、通过率、性能指标
- 长文一次倒出数千字且不暂停

## 最小示例

用户：「写一份政务监管平台的技术标书，模块有一张图和告警。」

1. 路由 → technical-proposal → 读 `references/technical-proposal.md`
2. 确认场合=对外投标、身份=乙方技术负责人（若未说则问）
3. 默认大文本模式：建 `plan.md`，先收架构与需求清单，再按模块叙述撰写
4. 正文零分点，每功能覆盖描述、实现流程、业务流程，并响应招标条款
