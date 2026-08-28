# 实用测试金字塔（Ham Vocke / Martin Fowler 站）

> **素材来源**：https://martinfowler.com/articles/practical-test-pyramid.html
> **作者**：Ham Vocke（Thoughtworks）
> **首发日期**：2018-02-26
> **抓取日期**：2026-08-28
> **整理方式**：精选转写（保留 Test Pyramid 概念、术语混乱、部署流水线、避免测试重复核心段；删除 Tools and Libraries、Sample Application 代码示例、单元测试/集成测试/契约测试/UI 测试/E2E 测试的具体代码示例与各工具配置段）
> **适用文档类型**：方案设计报告、测试报告、技术标书「测试策略」章节
> **可支撑的技术点**：测试金字塔, 测试分层, 单元测试, 集成测试, 契约测试, E2E 测试, 验收测试, 探索式测试, 测试部署流水线, 测试反模式, 冰淇淋锥
> **写作约束**：保留 Vocke 原文表述；引用术语与策略建议时建议注明 Ham Vocke & Martin Fowler 站

## 概述

测试金字塔（Test Pyramid）由 Mike Cohn 在《Succeeding with Agile》中提出，按不同粒度组织测试并提示各层级数量配比。Ham Vocke 在 2018 年这篇文章中以现代视角**重述**金字塔：**底层大量单元测试**、**中间若干粗粒度测试**、**顶层极少量端到端测试**——并补充了部署流水线、测试重复、术语混乱等实践议题。本文可作为标书「测试策略」「质量保障」章节的核心理论引用。

## 一、自动化测试的重要性

- 自动化测试让团队**在秒级与分钟级**内知道软件是否坏掉，而非天或周
- 缩短反馈回路与敏捷、持续交付、DevOps 文化强相关
- 「有效的测试方法」让团队**快速且有信心地**前进

## 二、测试金字塔（The Test Pyramid）

> If you want to get serious about automated tests for your software there is one key concept you should know about: the **test pyramid**. Mike Cohn came up with this concept in his book _Succeeding with Agile_.

### 2.1 Mike Cohn 原版三层

从底到顶：

1. **Unit Tests**（单元测试）
2. **Service Tests**（服务测试）
3. **User Interface Tests**（UI 测试）

### 2.2 现代视角的修正

Vocke 认为原版命名/概念过于简单、有误导：

- 「service test」很难理解（很多开发者直接忽略这一层）
- SPA（React/Angular/Ember 等）出现后，UI 测试不一定在金字塔顶层——完全可以做 UI 单元测试
- **名称可重新定义**，但**形状不要变**

### 2.3 牢记两条原则

1. 写**不同粒度**的测试
2. **越高层次、测试数量越少**

### 2.4 健康测试套件的口诀

- **大量**小而快的单元测试
- **若干**粗粒度测试
- **极少**端到端测试

### 2.5 反模式：冰淇淋锥（Ice-Cream Cone）

> Watch out that you don't end up with a [test ice-cream cone](https://alisterscott.github.io/TestingPyramids.html) that will be a nightmare to maintain and takes way too long to run.

冰淇淋锥：E2E 最多、手工测试多、集成测试次之、单元测试最少——难维护、跑得慢。

## 三、测试层级的现代命名建议

原版层名易误导，可替换为更贴合本团队/代码库的命名，**只要团队内一致即可**。

## 四、术语混乱（The Confusion About Testing Terminology）

> 软件开发社区尚未就测试分类达成明确定义。

要点：

- 不同人对「integration tests」「component tests」「service test」的理解不同
- 没有「唯一正解」，**测试分类本身是光谱而非离散桶**
- Google 的 Simon Stewart 总结得好（**Test Sizes**），团队不必纠结命名，要**找团队内能用一致的术语**

## 五、部署流水线中的测试（Putting Tests Into Your Deployment Pipeline）

原则：**快速反馈（Fast Feedback）**——这是 CD/XP/敏捷的核心价值观。

- 好的流水线尽快告诉你做错了什么
- 跑得快的测试放在流水线早期阶段
- 跑得慢的测试放在后期阶段
- 阶段划分标准不是测试**类型**而是**速度与范围**

> 把一些很窄且跑得快的集成测试放在与单元测试同阶段是合理的——它们给出更快反馈，不是因为我们要按形式类型划界。

## 六、避免测试重复（Avoid Test Duplication）

> Every single test in your test suite is additional baggage and doesn't come for free.

**两条经验法则**：

1. **如果高层测试发现错误且没有对应低层测试失败，要补低层测试**
2. **把测试尽可能下推到金字塔底层**

理由：

- 低层测试能更好定位错误、隔离重现、跑得快、不臃肿
- 避免冗余测试保持测试套件快速

## 七、写作引用建议

- 标书「测试策略」章节直接引用**两条核心原则**（不同粒度、越高越少）
- 「测试类型配比建议」引用大量单元测试 / 若干粗粒度 / 极少 E2E
- 「测试反模式警示」引用冰淇淋锥
- 「部署流水线」引用「按速度与范围划分阶段，不按形式类型」
- 「测试治理」引用「避免测试重复两条经验法则」
- 与 `ISTQB术语表.md` 配合：金字塔给策略，术语表给统一词汇
