# Kafka Streams 客户端流处理

> **素材来源**：https://kafka.apache.org/43/streams/core-concepts/ + https://kafka.apache.org/43/streams/introduction/
> **抓取日期**：2026-08-28
> **整理方式**：技术深度型（八段卡片）。原始抓取 `/streams/` 仅含导航；补抓 `/streams/core-concepts/` 后展开。
> **适用文档类型**：方案设计报告、技术标书「Kafka 生态流处理」「客户端流处理」「流表二元性」章节
> **可支撑的技术点**：Kafka Streams, KStream, KTable, GlobalKTable, Stream-Table Duality, Exactly-Once v2, 状态存储, Interactive Queries, Topology, Processor API, DSL API, log compaction, stream time
> **写作约束**：术语沿用 Apache Kafka 官方文档；不可编造具体性能基准。

## 1. 适用场景与触发词

需要「嵌入 Java 应用的轻量级流处理 + Kafka 生态紧密集成 + 无独立集群运维」时命中本卡片：

- 业务场景：Kafka 消息的实时聚合、事件溯源、CDC 流处理、流表关联、Kafka 内置 ETL
- 标书或设计报告关键词：「Kafka Streams」「KStream」「KTable」「客户端流处理」「Exactly-Once」「流表二元性」「状态存储」「Interactive Queries」「Stream-Table Duality」

## 2. 技术内涵与边界

**做什么**：

- 客户端库（client library），嵌入 Java 应用进程；不部署独立集群
- 强依赖 Apache Kafka 作为消息层；利用 Kafka 分区模型水平扩展
- 支持 Exactly-Once 端到端语义（KIP-129 / KIP-447，v2 实现自 Kafka 2.5+ 起生效）
- 支持有状态本地存储 + Interactive Queries（外部查询状态）
- 提供 Streams DSL（高层 API）与 Processor API（底层 API）

**不做什么**：

- 不替代 Kafka Broker——流处理计算跑在客户端进程内，Broker 仅做消息存储与传输
- 不是独立集群模式（如 Flink / Spark 集群）——不适合需要集中运维的复杂部署
- 不适合非 Java 应用（官方仅 Java 客户端；其他语言需自实现协议或使用 Sarama 等）
- 不擅长跨数据中心的全局聚合（适合单集群内的流处理）

## 3. 典型架构与关键机制

### 3.1 处理拓扑（Stream Processing Topology）

> 官方原文：「A stream is the most important abstraction provided by Kafka Streams: it represents an unbounded, continuously updating data set. A stream is an ordered, replayable, and fault-tolerant sequence of immutable data records, where a data record is defined as a key-value pair.」

- **Stream**：最重要的抽象，无界、连续、可重放、容错的不可变数据记录序列
- **Processor Topology**：由 Stream Processor（节点）+ Stream（边）构成的有向图
- **两类特殊 Processor**：Source Processor（无上游，从 Kafka 主题消费）、Sink Processor（无下游，写入 Kafka 主题）

### 3.2 时间模型

Kafka Streams 区分三种时间：

| 时间 | 含义 | 决定方 |
|---|---|---|
| Event Time | 事件在源端实际发生时间 | 业务数据本身 |
| Processing Time | 流应用处理事件的时刻 | 引擎墙钟 |
| Ingestion Time | Broker 把事件追加到分区的时间 | Broker 配置 |

> 官方原文：「Kafka Streams assigns a timestamp to every data record via the TimestampExtractor interface. These per-record timestamps describe the progress of a stream with regards to time and are leveraged by time-dependent operations such as window operations.」

输出记录的 timestamp 决定规则（按官方原文）：

- 通过 `context.forward()` 处理输入记录产生 → 继承输入 timestamp
- 通过 `Punctuator#punctuate()` 周期函数产生 → 当前内部时间（`context.timestamp()`）
- 聚合结果 → 所有输入记录 timestamp 的最大值

### 3.3 流表二元性（Stream-Table Duality）

> 官方原文：「Essentially, this duality means that a stream can be viewed as a table, and a table can be viewed as a stream. Kafka's log compaction feature, for example, exploits this duality.」

- **Stream as Table**：流是表的 changelog；可从表头 replay 重建
- **Table as Stream**：表是流在某时刻的快照；可展开为键值对序列
- Kafka Streams 通过 KStream、KTable、GlobalKTable 接口显式建模二元性
- CDC（Change Data Capture）与 Kafka Streams 状态机复制都依赖该二元性

### 3.4 聚合（Aggregations）

> 官方原文：「In the Kafka Streams DSL, an input stream of an aggregation can be a KStream or a KTable, but the output stream will always be a KTable. This allows Kafka Streams to update an aggregate value upon the out-of-order arrival of further records after the value was produced and emitted.」

- 聚合输入可为 KStream 或 KTable，输出必为 KTable
- 输出 KTable 允许「乱序到达」触发更新（同一 key 的新值覆盖旧值）

### 3.5 窗口（Windowing）

> 官方原文：「Windowing lets you control how to group records that have the same key for stateful operations such as aggregations or joins into so-called windows. Windows are tracked per record key.」

- 窗口按 record key 跟踪
- **Grace Period**：允许乱序事件的最大延迟；超过 grace period 的事件被丢弃
- 处理时间语义下「乱序」不适用（按到达顺序处理）；事件时间下乱序可处理
- Kafka Streams 内置时间窗口、会话窗口、跳跃窗口、滑动窗口

### 3.6 状态（States）

> 官方原文：「Kafka Streams provides so-called state stores, which can be used by stream processing applications to store and query data.」

- 每个 Task 嵌入一个或多个 state store：persistent key-value store、in-memory hashmap、其他结构
- 状态自动持久化到 Kafka 内部 topic（`__state_store`）实现故障恢复
- **Interactive Queries**：外部通过 REST 直接查询本地 state store（只读）

### 3.7 处理保证（Exactly-Once v2）

> 官方原文：「Since the 0.11.0.0 release, Kafka has added support to allow its producers to send messages to different topic partitions in a transactional and idempotent manner, and Kafka Streams has hence added the end-to-end exactly-once processing semantics by leveraging these features.」

- Exactly-Once v2 要求 broker ≥ 2.5（KIP-447）；3.0 起旧实现 deprecated
- 设置 `processing.guarantee=StreamsConfig.EXACTLY_ONCE_V2`
- 保证对输入 topic offsets、状态存储更新、输出 topic 写入原子完成（与 Kafka 存储层紧密耦合）

### 3.8 乱序处理（Out-of-Order Handling）

- 同分区记录 timestamp 可能不随 offset 单调递增（造成乱序）
- 多分区任务可能存在跨分区乱序
- 状态算子（聚合 / Join）对乱序敏感；无状态算子不敏感
- 解决方案：窗口 grace period / Versioned State Stores（用于 stream-table join）

## 4. 关键设计决策与权衡

### 决策 1：Kafka Streams vs Flink vs Spark Streaming

- **Kafka Streams（本方案 Java 嵌入 + Kafka 密集型场景采用）**：零独立部署成本；与 Kafka 紧密协同 Exactly-Once；功能子集（无批处理）
- **Flink**：分布式独立集群；延迟更低（毫秒级）、状态更大、CEP 更强；运维复杂
- **Spark Structured Streaming**：流批一体；SQL 友好；微批次延迟 ~100 ms
- **代价**：Kafka Streams 缺乏独立调度、UI、跨语言支持；大规模状态场景下运维复杂

### 决策 2：DSL API vs Processor API

- **DSL（推荐）**：高层 map / filter / join / aggregate；可读性高
- **Processor API**：自定义 Processor、定时器（`Punctuator`）、状态访问；灵活度高
- **代价**：Processor API 调试与维护成本高，需对拓扑生命周期有深入理解

### 决策 3：状态存储选型

- **Persistent Key-Value Store（RocksDB）**：默认；状态可超内存容量
- **In-Memory Hashmap**：性能高；状态受 JVM 堆限制
- **代价**：Persistent 状态读写受磁盘 IO 影响；序列化成本（Cp kryo / Avro / Protobuf）

### 决策 4：状态规模与并行度

- 状态按 Kafka topic 分区划分；分区数决定并行度上限
- 增加分区 → 可水平扩展，但状态迁移需触发 rebalance
- 减少分区 → 状态合并，需要协调迁移

## 5. 工程化要点

- **依赖**：仅 Kafka；客户端库嵌入 Java 应用，无独立进程
- **部署**：与业务应用共进程；推荐容器化部署 + K8s HPA
- **配置**：`application.id`、`bootstrap.servers`、`processing.guarantee`、`num.stream.threads`
- **监控**：Kafka Streams 自带 Metrics（JMX + REST）；自定义 Metrics 接入 Micrometer / Prometheus
- **运维**：
  - 应用重启 → 自动从 `__consumer_offsets` 恢复
  - 状态查询 → 通过 Interactive Queries 暴露为微服务
  - 滚动升级 → 配合 K8s StatefulSet / Deployment 滚动策略，注意 rebalance 影响

## 6. 指标映射

| 指标 | 口径示例 | 支撑手段 |
|---|---|---|
| 处理延迟 | 事件入 → 输出 ≤ X ms | Streams Metrics process-latency |
| 吞吐 | Records/s | process-rate |
| 状态大小 | 单 Task 状态 ≤ N MB/GB | state-store-size-bytes |
| Exactly-Once | 故障恢复无重复无丢失 | processing.guarantee=EXACTLY_ONCE_V2 |
| Active Tasks | Active / Standby / Resting 数 | Kafka Streams 监控 |
| Rebalance 时长 | ≤ M 秒 | Kafka Streams rebalance-time |

## 7. 标书化叙述示例

> 本方案的 Kafka 消息流上轻量级流处理采用 Apache Kafka Streams。客户端库嵌入业务应用进程（Java），通过 KStream 处理订单事件流、KTable 维护用户最新状态视图，二者通过 stream-table join 实时关联。状态存储使用 RocksDB-backed persistent state store，关键聚合结果回写为 compacted topic；同时启用 Interactive Queries 对外暴露状态查询接口（如「查询某用户最新积分余额」）。处理语义启用 Exactly-Once v2（`processing.guarantee=StreamsConfig.EXACTLY_ONCE_V2`），要求 Kafka 集群 ≥ 2.5；输入 topic offset 提交、状态存储更新、输出 topic 写入三者原子完成。时间模型采用事件时间，事件嵌入 timestamp 字段；窗口聚合设置合理的 grace period 以适应业务乱序。Kafka Streams 自带 Metrics + 自定义业务指标通过 Micrometer 上送 Prometheus；K8s 滚动升级时配合 preStop hook 优雅退出避免 rebalance 中断。具体业务的处理延迟、状态规模、并发数等数值由用户在合同附件中按业务等级明确。

## 8. 风险与边界

- **不可编造项**：
  - 具体延迟、吞吐、状态大小数字必须实测或用户提供
  - Kafka Streams 各版本（3.x / 4.x）的特性差异需回到官方文档核对（如 Exactly-Once v2 兼容性）
- **常见失败模式**：
  - Rebalance 抖动 → 启用 Cooperative Sticky Assignor + 优化 key 分布
  - 状态无限增长 → 必须配置 State Store TTL / 主动删除
  - 乱序处理不当 → 设置合理的 grace period
  - 跨版本兼容 → broker 版本必须 ≥ 配置中 Exactly-Once v2 要求
- **架构外延**：本卡片聚焦 Kafka Streams 客户端库；不涵盖 Kafka Connect（Source/Sink 连接器生态）、Kafka Schema Registry、ksqlDB