# 微服务架构：定义与九大共同特征（Martin Fowler & James Lewis）

> **素材来源**：https://martinfowler.com/articles/microservices.html
> **作者**：James Lewis、Martin Fowler
> **首发日期**：2014-03-25
> **抓取日期**：2026-08-28
> **整理方式**：精选转写（删除站点导航、订阅栏、图示说明、脚注营销内容；保留九大特征的定义段与原文表述）
> **适用文档类型**：方案设计报告、技术标书、架构评审文档
> **可支撑的技术点**：微服务, 微服务架构, 九大特征, 组件化, 业务能力, 智能端点, 去中心化, 基础设施自动化, 设计容错, 演进式设计
> **写作约束**：定义与表述为 Fowler/Lewis 原文引用，不要重写为新表述；引用时建议注明作者与日期

## 概述

「微服务」（Microservices）一词由 James Lewis 与 Martin Fowler 在 2014 年这篇文章中确立行业地位。它没有精确定义，但有九大共同特征：组件化与服务、按业务能力组织、产品而非项目、智能端点与哑管道、去中心化治理、去中心化数据管理、基础设施自动化、设计容错、演进式设计。本素材保留了九大特征的定义性段落，可直接转写入中文标书作为「微服务架构理论出处」。

## 一、整体定义（原文转写）

> In short, the microservice architectural style is an approach to developing a single application as a suite of small services, each running in its own process and communicating with lightweight mechanisms, often an HTTP resource API. These services are built around business capabilities and independently deployable by fully automated deployment machinery. There is a bare minimum of centralized management of these services, which may be written in different programming languages and use different data storage technologies.

要点：

- 单一应用拆分为**一组小型服务**
- 每个服务**独立进程**，通过轻量级机制通信（通常 HTTP 资源 API）
- 服务围绕**业务能力**构建
- **全自动部署机制**使其能独立部署
- **集中管理**降到最低限度
- 可使用不同编程语言、不同数据存储技术（多语种、多存储）

术语出处：2011 年 5 月威尼斯近邻软件架构师研讨会提出；2012 年 5 月确定「Microservices」命名。

---

## 二、九大共同特征

### 1. Componentization via Services（组件化与服务）

- **库（Library）**：与程序链接，通过内存函数调用
- **服务（Service）**：进程外组件，通过 Web Service 请求或远程过程调用等方式通信
- 服务作为组件的最大优势：**可独立部署**——单体应用修改任一组件都要整体重部署；微服务架构下多数修改只需重部署该服务本身
- 副作用：远程调用比进程内调用昂贵，需要更粗粒度 API；如果要改变组件职责，跨进程迁移行为更难

### 2. Organized around Business Capabilities（按业务能力组织）

- 传统按技术层（UI / 服务端 / 数据库）划分团队导致跨团队协作昂贵（Conway's Law）
- 微服务拆分按**业务能力**而非技术层；服务承担该业务领域从前端到持久化的整栈实现
- 团队是**跨职能的**：用户体验、数据库、项目管理技能同在一队
- 单体应用也能按业务能力模块化，但实际少见；微服务的进程边界让模块边界更明确

### 3. Products not Projects（产品而非项目）

- 项目模式：交付即解散，由运维接手
- 微服务支持者倾向**产品模式**：团队对产品终身负责——Amazon 的「you build, you run it」
- 开发者日常接触生产行为与用户，强化产品质量意识

### 4. Smart endpoints and dumb pipes（智能端点与哑管道）

- 反例：Enterprise Service Bus（ESB）——在通信机制中塞入大量智能化（路由、编排、转换、业务规则）
- 微服务主张：**端点智能、管道简单**。服务持有自己的领域逻辑（类似 Unix filter）；协议倾向简单的 REST 或轻量消息总线
- 通信机制本身保持 dumb（只做消息路由）：如 RabbitMQ、ZeroMQ
- 单体内组件通过方法/函数调用通信；改为微服务要把细粒度调用改为**粗粒度协作**，否则会出现性能问题

### 5. Decentralized Governance（去中心化治理）

- 中心化治理倾向标准化到单一技术平台
- 微服务拆分后每个服务可选型：Node.js 报表页面、C++ 实时组件、不同数据库
- 标准方面：不靠纸面规范，而靠把内部工具沉淀为共享库让其他人复用（内部开源）
- 服务契约管理：使用 **Tolerant Reader** 与 **Consumer-Driven Contracts** 模式降低耦合
- 极端：Amazon 的「构建即运行」、Netflix 的「开发者自服务」——团队对软件 24/7 全面负责

### 6. Decentralized Data Management（去中心化数据管理）

- 概念层面：不同系统的「客户」概念可能不同——销售视图 vs 售后视图；这正是 DDD 中的 Bounded Context（限界上下文）
- 存储层面：每服务管自己的库，可采用不同 DBMS——Polyglot Persistence（多语种持久化）
- 影响：跨服务更新不能依赖分布式事务；微服务强调**无事务协调**，承认**最终一致性**，通过补偿操作处理不一致

### 7. Infrastructure Automation（基础设施自动化）

- 与 Continuous Delivery / Continuous Integration 强相关
- 构建流水线：跑大量自动化测试 → 自动化部署到新环境
- 单体应用能同等享受流水线；微服务的运维图景与单体显著不同
- 投资基础设施自动化是微服务能落地的必要前提

### 8. Design for failure（设计容错）

- 服务随时可能失败；客户端必须优雅响应
- 这是相对单体的劣势：需要额外处理失败
- 反过来促进韧性：Netflix 的 Simian Army 在工作日人为制造服务/数据中心故障测试
- 监控：架构性指标（数据库 QPS）+ 业务相关指标（每分钟订单数）
- 强调实时监控、语义监控、熔断器状态、当前吞吐与延迟的可视化

### 9. Evolutionary Design（演进式设计）

- 微服务从业者多来自演进式设计背景，将服务分解视为控制变更速率的工具
- 目标不是减少变更，而是**让变更更频繁、更快、更可控**

---

## 三、关于「微服务未来」的判断（原文转写）

> Microservice practitioners, usually have come from an evolutionary design background and see service decomposition as a further tool to enable application developers to control changes in their application without slowing down change.

写作时可引用：微服务不追求一次性最优拆分，而是允许通过持续拆分/合并调整。

---

## 四、写作引用建议

- 标书「架构设计原则」章节可引用原文定义段落（注意标注作者与日期）
- 「微服务适用性判断」可结合 `微服务架构权衡.md` 一并引用
- 「业务能力划分」可引用 Conway's Law 与 Bounded Context（DDD）
- 「基础设施自动化」与 `Kubernetes架构与组件.md`、`Istio服务网格.md` 互为支撑
