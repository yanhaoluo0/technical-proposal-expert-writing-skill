# Apache Flink 流计算核心机制

> **素材来源**：https://flink.apache.org/what-is-flink/flink-architecture/ + https://flink.apache.org/what-is-flink/flink-applications/ + https://nightlies.apache.org/flink/flink-statefun-docs-release-3.2/docs/concepts/distributed_architecture/
> **抓取日期**：2026-08-28
> **整理方式**：技术深度型（八段卡片）。原始抓取仅含功能条目与博客摘要，本卡片按官方架构文档中的 JobManager / TaskManager / Checkpoint / State Backend / Savepoint 概念体系展开。
> **适用文档类型**：方案设计报告、技术标书「实时计算引擎」「事件驱动」「流批一体」章节
> **可支撑的技术点**：Flink 架构, JobManager, TaskManager, Checkpoint, Chandy-Lamport, 两阶段提交, Savepoint, 状态后端, RocksDB, Exactly-Once, 事件时间, 水位线, 反压, 反压 credit-based, 分层 API, 流批一体
> **写作约束**：术语沿用 Apache Flink 官方文档；不可编造 Flink 版本号对应的具体可用性数字或业务基准。

## 1. 适用场景与触发词

方案中需要满足以下任一条件时命中本卡片：

- 业务对「实时事件驱动」「流批一体」「事件时间窗口 + 迟到数据处理」有强诉求（金融反欺诈、实时风控、实时特征、计费、监控告警等）
- 需要「Exactly-Once 端到端一致性」，并对延迟敏感（毫秒~秒级）
- 输入是持续事件流（Kafka、Pulsar、Kinesis、MQTT、数据库 CDC），输出要求低延迟聚合、维表关联、状态化计算
- 标书或设计报告出现关键词：「Flink」「流处理」「实时计算」「有状态计算」「检查点」「水位线」「Savepoint」「反压」「事件时间」

## 2. 技术内涵与边界

**做什么**：

- 对无界数据流（unbounded stream）执行有状态计算，支持事件时间（event time）与处理时间（processing time）两种时间模型
- 提供 Exactly-Once 状态一致性（基于分布式快照算法）
- 通过 Checkpoint（自动周期触发）与 Savepoint（手动触发的版本化快照）实现容错与状态迁移
- 支持状态后端（State Backend）：MemoryStateBackend / FsStateBackend / RocksDBStateBackend
- 提供四层编程接口：SQL、Table API、DataStream API、ProcessFunction（最低层，时间 + 状态最强控制力）

**不做什么**：

- 不等于「消息队列」——Flink 是计算引擎，需配合 Kafka/Pulsar 等作为输入输出
- 不内置 OLAP 能力（聚合查询、Ad-Hoc 分析）——非其设计目标；该类需求选 ClickHouse / Doris
- 不擅长小批量微批次（秒级以下延迟需求比 Spark Streaming 更合适）
- 不应被滥用为「ETL 调度器」——ETL 编排优先用 Airflow / DolphinScheduler；Flink 自身适合流式 ETL 而非定时跑批

## 3. 典型架构与关键机制

### 3.1 进程拓扑

一个 Flink 集群典型包含三类进程：

- **Client**：用户提交 Job 的入口，预编译 StreamGraph → JobGraph，提交给 JobManager
- **JobManager（JM）**：Master 节点，负责调度（Scheduler）、资源管理（ResourceManager）、分发 Task、协调 Checkpoint、协调 Failover
- **TaskManager（TM）**：Worker 节点，执行具体的 Task，提供一定数量的 Task Slot，每个 Slot 是独立执行线程 + 内存隔离单元

> 官方文档表述：「A Flink cluster consists typically of one master and multiple workers (TaskManagers).」

### 3.2 分层 API（自下而上）

| 层 | 接口 | 适用场景 | 抽象粒度 |
|---|---|---|---|
| 最低层 | ProcessFunction | 自定义窗口、Timer、状态、复杂业务逻辑 | 单事件 + 时间 + 状态 |
| 中低层 | DataStream API（map/filter/keyBy/window/aggregate） | 主流流处理 | 流 + 窗口 |
| 中高层 | Table API | 关系型表达，介于 SQL 与 DataStream 之间 | 表 |
| 最高层 | SQL on Stream & Batch Data | 类批 SQL 表达，简单业务首选 | 表 + SQL |

### 3.3 核心机制：分布式快照（Checkpoint）

Flink 的核心容错机制是 Asynchronous Barrier Snapshotting（ABS），借鉴 Chandy-Lamport 分布式快照算法思想，但为流处理优化：

- **Barriers**：JM 在数据流中周期性注入 checkpoint barrier（特殊标记），随数据流在算子之间流动
- **对齐（Alignment）**：收到 barrier 的算子会对输入通道做 barrier 对齐——先到的通道数据会缓冲；后续通道等 barrier 到位再放出；保证同一 checkpoint 内数据快照的全局一致性
- **异步快照**：算子状态异步写入持久化存储（一般是 DFS / S3 / OSS），不阻塞数据处理
- **Exactly-Once 语义**：Flink 保证算子状态 + 输入 offset 是 Exactly-Once；对外部 sink 的 Exactly-Once 需配合两阶段提交（2PC sink，如 Kafka 0.11+ 事务）

### 3.4 时间与水位线（Watermark）

- **事件时间（Event Time）**：事件实际发生的时间，嵌入数据本身
- **处理时间（Processing Time）**：算子处理事件的墙钟时间
- **水位线（Watermark）**：一种特殊记录，表示「时间戳 ≤ t 的事件已全部到达」；携带 `t` 推进事件时钟
- 迟到数据通过 `allowedLateness` 与 `side output` 处理

### 3.5 状态后端（State Backend）

| 后端 | 存储位置 | 适用 | 限制 |
|---|---|---|---|
| MemoryStateBackend | TM 堆内存 + JM heap | 本地开发、调试、小状态 | 状态受堆大小限制 |
| FsStateBackend | TM 堆内存（访问）+ DFS（持久化） | 中等状态、常规生产 | 大状态受堆限制 |
| RocksDBStateBackend | RocksDB（TM 本地磁盘）+ DFS | 大状态生产（GB~TB 级） | 访问延迟略高（本地磁盘读） |

### 3.6 反压（Backpressure）

Flink 通过 TCP-based / Credit-based 流控实现反压：当下游处理慢时，通过 buffer 队列的反馈信号让上游自动降速——无需人工干预。流批一体的数据交换靠 Netty + 缓冲池。

## 4. 关键设计决策与权衡

### 决策 1：流式 vs 微批次

- **流式（本方案采用）**：Flink 原生流式，每个事件触发一次处理，延迟毫秒级；Checkpoint 机制保证 Exactly-Once
- **微批次**：Spark Streaming 的早期模式（已不推荐）；Structured Streaming 仍保留微批次 + 连续处理双模式
- **代价**：流式引擎对状态管理、Checkpoint 的实现复杂度更高，运维门槛比 Spark 略高

### 决策 2：状态后端选型

- **RocksDB（本方案状态较大场景采用）**：支持 GB~TB 级状态；读写命中本地磁盘，延迟几十毫秒
- **Heap（FsStateBackend）**：读写快（毫秒内），但状态受 JVM 堆限制（建议 ≤ 几十 GB）
- **代价**：RocksDB 引入序列化成本（Cp kryo/avro/Protobuf），CPU 占用略高；需配置 `state.backend.incremental: true` 增量 Checkpoint 降低 HDFS 写入压力

### 决策 3：窗口与迟到数据

- **滚动 / 滑动 / 会话窗口**：业务最常用
- **迟到数据**：事件时间业务必备；Flink 通过 `watermark + allowedLateness + side output` 三件套处理
- **代价**：迟到数据策略过宽会显著放大状态占用；过窄会丢数据；具体阈值需业务侧提供

### 决策 4：外部 Sink 的 Exactly-Once

- **两阶段提交（2PC sink）**：Kafka 0.11+、MyJDBC XA 等支持；强一致
- **幂等写入**：UPSERT + 唯一键，业务侧补偿；实现简单但语义弱
- **At-Least-Once + 业务去重**：最低成本，但需要重试 + 去重表
- **代价**：2PC sink 写延迟最高（多一轮 preCommit）；业务级去重要维护额外的状态

## 5. 工程化要点

- **集群部署**：Kubernetes 上 Flink 官方提供 Native Kubernetes 集成（`kubernetes-session` / `kubernetes-application` 模式）；Standalone / YARN 仍可用
- **HA**：ZooKeeper 或 Kubernetes-based HA（推荐 K8s 模式）；JM 故障切换时间秒级
- **Checkpoint 存储**：DFS / S3 / OSS / HDFS；建议开启增量 Checkpoint
- **监控指标**：
  - 业务：Records Sent/Received、Watermark Lag、Checkpoint Duration、State Size
  - 系统：TaskManager CPU、JVM Heap、GC、Net Buffer 用量、GC Pause
  - 推荐 Reporter：Prometheus + Grafana + AlertManager
- **Savepoint 触发**：版本升级、扩缩容、修改并行度时使用；REST API 触发
- **反压定位**：Flink Web UI 的反压状态（OK/LOW/HIGH）逐算子下钻；常见瓶颈：自定义算子逻辑、外部 IO、同步调用
- **日志**：Log4j2 + 滚动策略；TM 上要单独配置 JVM 启动参数（`-Xmx`、`MetaspaceSize`、`UseG1GC`）

## 6. 指标映射

| 指标 | 口径示例 | 支撑手段 |
|---|---|---|
| 端到端延迟 | 事件产生 → 计算结果可见 ≤ X 秒 | Watermark 推进 + Source/Sink 缓冲监控 |
| 吞吐 | 峰值 TPS（如 100K events/s） | Records Sent/Received + Parallelism |
| Checkpoint 时长 | 周期 N 秒，单次完成 ≤ M 秒 | state.backend.incremental + RocksDB 调优 |
| 状态大小 | 单 TM 状态 ≤ N GB | RocksDB 配额 + 自定义 TTL 清理 |
| Exactly-Once | 故障恢复后无重复无丢失 | 2PC sink + Kafka 事务 |
| 可用性 | JM HA + TM 自动拉起，秒级切换 | ZK/K8s HA |
| 资源利用率 | TM CPU 60-80%，Heap 50-70% | 自定义 Reporter + 自动扩缩容 |

## 7. 标书化叙述示例

> 本方案实时计算引擎选用 Apache Flink，部署采用 Kubernetes Native 模式，作业拓扑由 1 个 JobManager + 多个 TaskManager 组成。任务按业务键（keyBy）分区，状态后端选用 RocksDBStateBackend（启用增量 Checkpoint），Checkpoint 周期 60s，状态快照持久化至 HDFS 命名服务。事件时间语义贯穿整条数据通路，Watermark 策略按业务允许的最大乱序时间窗配置（如 30s），迟到数据通过 `allowedLateness(10s)` + Side Output 双轨输出后写入独立的补偿通道，由离线任务兜底重算。对 Kafka 输出的链路启用 Kafka 事务 + 两阶段提交 Sink，实现端到端 Exactly-Once。运行时通过 Flink REST API + Prometheus Reporter 将 Records Sent/Received、Watermark Lag、Checkpoint Duration、State Size 四类指标上送监控；Web UI 反压视图作为反压定位入口；Savepoint 在版本升级与并行度变更时通过 API 触发并记录完成耗时。JobManager 主备由 Kubernetes 自带的 Controller Manager 提供；TaskManager 故障由 Kubernetes 自动拉起。具体的可用性指标值（如 RTO 上限、延迟 P99 数值）由用户根据业务等级在合同附件中提供。

## 8. 风险与边界

- **不可编造项**：
  - 具体 RTO / RPO 数值必须由用户业务侧提供，不能由本素材反推
  - 具体的峰值 TPS、状态规模上限必须结合业务规模给出，不应套用「百万 TPS」「TB 级状态」等通用数字
  - Flink 各版本（1.x / 2.x）的精确差异不应在本素材中描述，应回到官方 Release Notes 核对
- **常见失败模式**：
  - Checkpoint 超时 → 增量 Checkpoint、RocksDB 调优、减小状态
  - 反压扩散 → 检查自定义算子热点、外部系统慢调用、Key 不均
  - Savepoint 不可用 → 必须固定最大并行度（MaxParallelism）；变更需谨慎
  - 时间语义错配 → 业务侧明确说明使用 event time 还是 processing time；不要混用
  - 状态无限增长 → 必须配置 State TTL（`StateTtlConfig`）
- **架构外延**：本卡片聚焦 Flink 流计算引擎；不涵盖 Flink CDC（基于 Debezium 的数据捕获）、Flink ML、Flink Agents 等周边组件，这些应单独组织素材

---
