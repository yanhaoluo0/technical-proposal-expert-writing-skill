# CQRS：命令查询职责分离（Martin Fowler）

> **素材来源**：https://martinfowler.com/bliki/CQRS.html
> **作者**：Martin Fowler
> **首发日期**：2011-07-14
> **抓取日期**：2026-08-28
> **整理方式**：整篇转写（删除评论/订阅/相关链接列表；正文较短，全文保留）
> **适用文档类型**：方案设计报告、技术标书、读写分离方案
> **可支撑的技术点**：CQRS, 命令查询分离, 读写分离, 事件驱动, 事件溯源, 领域驱动设计, DDD Bounded Context, 报表数据库
> **写作约束**：保留 Fowler 原文表述；引用时注明作者与日期；CQRS 适用边界严格遵循 Fowler 「When to use it」

## 概述

CQRS（Command Query Responsibility Segregation，命令查询职责分离）由 Greg Young 首次提出，Martin Fowler 在 2011 年撰写本文推广。核心思想：**用于更新与读取的信息模型可以不同**。Fowler 同时强调：**CQRS 给大多数系统带来风险性复杂度，慎用**——仅在「复杂领域」或「高性能应用」两类场景有明确收益。

## 一、问题背景：CRUD 思维模型的局限

主流方法把信息系统当作 CRUD 数据存储：

- Create / Read / Update / Delete 记录
- 概念模型以单点表示（多条记录聚合、虚拟记录、按规则验证/推断存储）

随着需求复杂化：

- 多重信息表示（用户接触不同展示；开发者有自己的概念模型；持久存储尽量贴近概念模型）
- 当所有表示都「下沉到同一概念模型」时该模型就会变得复杂

## 二、CQRS 的核心改变

把单一概念模型**拆分为更新模型（Command）与读取模型（Query）**：

- **Command 模型**：处理写操作
- **Query 模型**：处理读操作
- 不同对象模型，可能在不同逻辑进程、不同硬件
- 典型流程：用户看网页（Query 模型渲染） → 发起变更（路由到 Command 模型处理） → 变更同步到 Query 模型

> By separate models we most commonly mean different object models, probably running in different logical processes, perhaps on separate hardware.

变体：

- 共用同一数据库（数据库作为两模型通信媒介）
- 各自独立数据库（Query 模型实质上是实时报表数据库 ReportingDatabase）
- 也可以是同一对象但命令/查询接口分离（类似关系数据库的视图）

## 三、CQRS 自然契合的架构模式

- 任务型 UI（基于任务的交互界面）
- 事件驱动编程模型（常见拆分服务的 CQRS 系统通过事件协作 EventCollaboration 通信）
- **事件溯源（Event Sourcing）**（与 CQRS 高度协同）
- **最终一致性（Eventual Consistency）**（双模型一致性问题的常用解）
- **EagerReadDerivation**（预计算读模型，简化查询侧）
- **EventPoster** + **MemoryImage**（写模型产生事件，读模型作为内存镜像避免大量数据库交互）
- **领域驱动设计（DDD）** 复杂领域天然适合 CQRS

## 四、When to use it（适用边界）

> Like any pattern, CQRS is useful in some places, but not in others. Many systems do fit a CRUD mental model, and so should be done in that style. CQRS is a significant mental leap for all concerned, so shouldn't be tackled unless the benefit is worth the jump.

**两大适用方向**：

1. **复杂领域少数情况**：让少数复杂领域用 CQRS 处理——Fowler 强调「这种适用性是少数情况」，通常 Command 与 Query 重叠多，共享模型更省事
2. **高性能应用**：读写负载可分离、独立扩展；可对读写应用不同优化策略（如读用不同 DB 访问技术）

**严格约束**：

- CQRS **应只用于系统的特定部分**（DDD 术语：单个 Bounded Context 内决策），不应作用于整个系统
- **不适用时不要用**：在不适合的领域用 CQRS 会增加复杂度、降低生产力、增加风险

**替代方案**：

- 如果领域不适合 CQRS 但查询有性能问题，仍可只用 **ReportingDatabase**（用主系统处理多数查询，把重查询 offload 到报表库）

## 五、慎用警告

> Despite these benefits, you should be very cautious about using CQRS. Many information systems fit well with the notion of an information base that is updated in the same way that it's read, adding CQRS to such a system can add significant complexity. I've certainly seen cases where it's made a significant drag on productivity, adding an unwarranted amount of risk to the project, even in the hands of a capable team.

## 六、Further Reading

- Greg Young 在 CodeBetter 的总结（被 Fowler 推荐为首要阅读材料）
- Udi Dahan 的详细 CQRS 技术描述
- dddcqrs Google Group 邮件列表

## 七、写作引用建议

- 在标书「读写分离方案」「报表性能优化」「事件驱动架构」章节可引用本素材
- **必须同时引用 Fowler 的「慎用警告」**，避免方案设计中被评审质疑「为什么用 CQRS」
- 配合 `微服务模式-模式库索引.md` 2.1 节「服务协作模式」一起引用
- 配合 DDD Bounded Context、Event Sourcing、最终一致性等术语写作
