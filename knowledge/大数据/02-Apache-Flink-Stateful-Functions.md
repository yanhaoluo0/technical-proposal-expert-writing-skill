# Apache Flink Stateful Functions 状态化函数

> **素材来源**：https://nightlies.apache.org/flink/flink-statefun-docs-release-3.2/docs/concepts/distributed_architecture/
> **抓取日期**：2026-08-28
> **整理方式**：技术深度型（八段卡片）。基于 Flink Stateful Functions 3.2 文档 Distributed Architecture 章节。
> **适用文档类型**：方案设计报告、技术标书「Serverless 流处理」「状态化函数」「跨语言事件驱动」章节
> **可支撑的技术点**：Stateful Functions, Serverless, 状态化函数, 物理分离逻辑共置, Remote Function, Embedded Function, HTTP/gRPC 协议, Function as a Service, Lambda 风格, Function persistence
> **写作约束**：术语沿用 Apache Flink Stateful Functions 官方文档；不可编造具体性能基准。

## 1. 适用场景与触发词

需要「事件驱动的有状态计算 + 多语言实现 + 独立弹性扩缩」时命中本卡片：

- 业务场景：复杂事件处理（CEP）、事件溯源（ES）、有状态微服务、工作流编排、跨语言（Java / Python）状态计算
- 标书或设计报告关键词：「Stateful Functions」「Serverless 流处理」「函数即服务」「Function as a Service」「状态化函数」「逻辑共置物理分离」

## 2. 技术内涵与边界

**做什么**：

- 提供「状态化函数」（Stateful Functions）抽象：业务逻辑封装为 Function，运行在 FaaS / K8s / JVM 中；状态由 Flink 端托管
- 实现「逻辑共置（Logical Co-location）+ 物理分离（Physical Separation）」：消息路由、状态访问、Timer 调度由 Flink 统一处理，但函数进程可独立部署、独立扩缩
- 支持三种部署风格：Embedded（同 JVM）、Co-located（sidecar）、Remote（独立进程，HTTP/gRPC）

**不做什么**：

- 不是通用函数计算平台——其 Function 状态绑定到 Flink 持久化层
- 不替代 Flink DataStream API 主线方案——Stateful Functions 是「事件驱动 + 多语言」的特殊抽象
- 不适用于纯批处理、超低延迟（亚毫秒）硬实时场景

## 3. 典型架构与关键机制

### 3.1 高层视图

Stateful Functions 部署包含：

- **Apache Flink Worker 进程（TaskManager）**：接收来自 Kafka / Kinesis 等入口的事件，按 key 路由到目标 Function，调用 Function，将结果消息路由到下游
- **Function 进程**（可选远程部署）：在 HTTP/gRPC 端点接收 Flink 端发来的调用请求（携带消息 + 状态访问 + Timer），执行 Function 逻辑后返回结果

> 官方文档原句：「The Flink worker processes (TaskManagers) receive the events from the ingress systems (Kafka, Kinesis, etc.) and route them to the target functions. They invoke the functions and route the resulting messages to the next respective target functions.」

### 3.2 组件

- Flink 集群：一个 Master + 多个 Worker（TaskManager）
- 辅助依赖：ZooKeeper 或 Kubernetes（master failover）+ 持久化存储（S3 / HDFS / NAS）存放 Checkpoint
- 不需要数据库；Flink 进程无需持久卷

### 3.3 核心设计：逻辑共置 + 物理分离

> 官方原文：「A core principle of many Stream Processors is that application logic, and the application state must be co-located. That approach is the basis for their out-of-the box consistency. Stateful Functions takes a unique approach to that by logically co-location state and compute, but allowing to physically separate them.」

- **逻辑共置（Logical Co-location）**：消息路由、状态访问、函数调用紧耦合——状态按 key 分片、消息按 key 路由到持有该 key 状态的算子，每个 key 同时只有一个 writer 调度函数调用
- **物理分离（Physical Separation）**：Function 可独立进程部署，消息 + 状态访问 + Timer 作为调用请求的一部分传入

### 3.4 三种部署风格（Function 端）

| 风格 | 部署位置 | 调用协议 | 优点 | 代价 |
|---|---|---|---|---|
| Embedded | Flink JVM 进程内 | 直接方法调用 | 性能最高 | 仅 JVM 语言；与 Flink 耦合 |
| Co-located | K8s Pod 内 sidecar（与 TM 同 Pod） | Pod 内网络 | 跨语言；无 Service 路由 | 不能独立扩缩 Function 与 State |
| Remote | 独立进程 / Lambda / K8s 服务 | HTTP / gRPC 经 Service / LB 路由 | Function 与 State 完全独立扩缩 | 网络一跳；Function 必须无状态 |

> 官方文档原句：「Remote Functions use the above-mentioned principle of physical separation while maintaining logical co-location. The state/messaging tier (i.e., the Flink processes), and the function tier are deployed, managed, and scaled independently.」

## 4. 关键设计决策与权衡

### 决策 1：Remote vs Co-located vs Embedded

- **Remote（本方案多语言 / Serverless 场景采用）**：Function 可运行任意语言、任意运行时；Function 端可水平扩缩到 N 实例；Flink 端按 key 路由
- **Co-located（多语言 + 中等性能）**：通过 sidecar 与 TM 共 Pod；绕开 Service LB 网络一跳
- **Embedded（极致性能）**：函数与 Flink 同 JVM；最高吞吐；只支持 JVM 语言
- **代价**：Remote 模式引入网络一跳延迟（ms 级）；Co-located 不能独立扩缩 state 与 function

### 决策 2：Function 数量与 Function 状态粒度

- 一个 Function 类型 = 一类业务（如 `UserFunction`、`OrderFunction`）；状态按 Function 类型 + key 命名空间分片
- Function 数量过多会导致 Function Registry 过大、调度开销升高
- 单一 Function 类型承担过多职责会破坏业务边界

### 决策 3：Function 端状态 vs Flink 端状态

- Stateful Functions 设计意图：Function 端尽量无状态（视为可丢弃进程），持久状态全在 Flink 端
- 反模式：在 Function 端维护本地缓存或外部 DB 存储——会破坏 Exactly-Once 与一致性

## 5. 工程化要点

- **依赖**：除 Flink 外，还需 ZooKeeper / K8s（HA）+ 对象存储（Checkpoint）
- **SDK**：Stateful Functions 提供 Python SDK / Java SDK；Go SDK 通过 gRPC 自行实现
- **部署**：Remote Function 通常以 K8s Deployment 部署；端点由 Service / Ingress 暴露
- **弹性扩缩**：Function 端独立扩缩，由 K8s HPA 触发；Flink 端通过 adaptive scheduler / Reactive Mode 自适应
- **监控**：Flink Metrics + Function 端自定义指标；Function 调用延迟、失败率是核心 SLI
- **运维**：Flink Checkpoint 周期与 Function 调用超时配合；Function 端超时过长会拖垮 Checkpoint

## 6. 指标映射

| 指标 | 口径示例 | 支撑手段 |
|---|---|---|
| 端到端延迟 | 事件产生 → Function 结果 ≤ X ms | 链路埋点（Ingress→Flink→Function） |
| Function 吞吐 | 每 Function 实例 QPS | Function 自定义 Metrics |
| Flink 状态大小 | 单 Function 类型状态 ≤ N GB | RocksDB 后端 + TTL |
| Function 扩缩容 | HPA 在 CPU > 70% 时扩容 | K8s HPA / 自定义指标 |
| Checkpoint 时长 | 周期 60s，单次 ≤ M 秒 | 增量 Checkpoint + 状态分片 |
| Exactly-Once | Function 调用与状态写入原子 | Flink 2PC + Remote Function 幂等 |

## 7. 标书化叙述示例

> 本方案的「事件驱动 + 多语言」型业务流（如订单编排、设备影子同步、复杂事件处理）选用 Apache Flink Stateful Functions 架构。Stateful 层由 Flink TaskManager 集群承担，使用 RocksDBStateBackend 持久化状态；Function 层独立部署在 Kubernetes 上，按业务类型拆分为多个独立 Deployment（如 `UserFunction`、`OrderFunction`），按 key 经 HTTP/gRPC 经 Service 路由被 Flink 端调用。该方案实现「逻辑共置（按 key 路由到目标 Function）+ 物理分离（Function 与 State 独立扩缩）」，Function 端视为无状态进程，可由 Kubernetes HPA 按 CPU 与请求延迟弹性伸缩；Flink 端通过 Reactive Mode 自适应反压。Checkpoint 周期配置为 60 秒，状态快照持久化至 OSS 命名服务；Function 端超时上限与 Checkpoint 超时联动配置，避免 Checkpoint 被长 Function 调用阻塞。具体业务峰值 TPS 与 Function 端目标延迟由用户在合同附件中按业务等级明确。

## 8. 风险与边界

- **不可编造项**：
  - Function 调用延迟、吞吐数字必须由实测或用户提供
  - Flink Stateful Functions 各版本（3.x）的特性差异（如 Persistence、Remote Module）需回到官方文档核对
- **常见失败模式**：
  - Function 端有状态 → 违反 Stateful Functions 设计意图；失败时状态丢失
  - Function 端超时过长 → Checkpoint 长时间无法完成
  - Function 数量过多 → Registry 膨胀，调度开销升高
  - HTTP/gRPC 端点未限流 → Flink 端反压失效
- **与上游 Kafka 等消息中间件的耦合**：Stateful Functions 默认通过 Flink Connector 接入 Kafka；不替代消息中间件本身
- **与 FaaS（Lambda）的边界**：Function 端可以运行 AWS Lambda；本卡片不涵盖 Lambda 自身的冷启动 / 并发配额等约束