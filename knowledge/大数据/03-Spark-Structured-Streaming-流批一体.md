# Spark Structured Streaming 流批一体

> **素材来源**：https://spark.apache.org/docs/latest/streaming/index.html + https://spark.apache.org/docs/latest/streaming/getting-started.html + https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html
> **抓取日期**：2026-08-28
> **整理方式**：技术深度型（八段卡片）。原始直链 `/structured-streaming-programming-guide.html` 自 4.0.0 起已被拆分为小页，本卡片按拆解后的 `streaming/index.html`（Overview）与 `streaming/getting-started.html`（Programming Model）综合整理。
> **适用文档类型**：方案设计报告、技术标书「流批一体」「微批次流处理」「近实时计算」章节
> **可支撑的技术点**：Structured Streaming, 流批一体, micro-batch, Continuous Processing, Dataset/DataFrame API, Spark SQL, Event Time, Watermark, Trigger, Output Mode, Exactly-Once, Checkpoint, Write-Ahead Log
> **写作约束**：术语沿用 Apache Spark 官方文档；不可编造具体延迟或吞吐数字。

## 1. 适用场景与触发词

需要「流批统一 API + 近实时（百毫秒~秒级）+ Spark 生态复用」时命中本卡片：

- 业务场景：近实时报表、行为日志聚合、ETL 实时化、增量数据处理
- 标书或设计报告关键词：「Structured Streaming」「流批一体」「微批次」「Spark SQL 流处理」「近实时」「事件时间窗口」「Watermark」「Trigger」

## 2. 技术内涵与边界

**做什么**：

- 基于 Spark SQL 引擎构建，提供与批处理一致的 Dataset/DataFrame API
- 默认采用微批次处理引擎，端到端延迟低至 100 ms，并保证 Exactly-Once
- 自 Spark 2.3 起引入「连续处理」（Continuous Processing）模式，端到端延迟低至 1 ms，但仅保证 At-Least-Once
- 通过 Checkpoint + Write-Ahead Logs（WAL）保证端到端 Exactly-Once 故障容错

**不做什么**：

- 不适合亚毫秒级硬实时（连续处理模式也无法保证 Exactly-Once）
- 不替代 Kafka / Pulsar——Structured Streaming 是计算引擎，需配 Source/Sink 中间件
- 对乱序数据的容忍度由 Watermark 配置决定，不当配置会丢数据或显著延迟
- 不适合复杂的 CEP 模式——多步骤流模式匹配用 Flink 更成熟

## 3. 典型架构与关键机制

### 3.1 核心抽象：流是无界的表

> 官方原文：「Structured Streaming is a scalable and fault-tolerant stream processing engine built on the Spark SQL engine. You can express your streaming computation the same way you would express a batch computation on static data. The Spark SQL engine will take care of running it incrementally and continuously and updating the final result as streaming data continues to arrive.」

- 「流」被建模为「无界表」（unbounded table）：每条新事件 = 新增一行
- 用户写 DataFrame/Dataset API 或 SQL，对无界表做关系查询
- 引擎负责把查询拆解为「增量执行计划」并持续运行

### 3.2 两种处理模式

| 模式 | 延迟 | 故障语义 | 适用 |
|---|---|---|---|
| Micro-batch（默认） | ~100 ms | Exactly-Once | 主流场景、近实时 ETL、报表 |
| Continuous Processing | ~1 ms | At-Least-Once | 监控告警等可容忍少量重复的场景 |

> 官方原文：「Internally, by default, Structured Streaming queries are processed using a micro-batch processing engine, which processes data streams as a series of small batch jobs thereby achieving end-to-end latencies as low as 100 milliseconds and exactly-once fault-tolerance guarantees. However, since Spark 2.3, we have introduced a new low-latency processing mode called Continuous Processing, which can achieve end-to-end latencies as low as 1 millisecond with at-least-once guarantees.」

### 3.3 编程模型三要素（Quick Example）

```python
lines = spark.readStream.format("socket").option("host", "localhost").option("port", 9999).load()
words = lines.select(explode(split(lines.value, " ")).alias("word"))
wordCounts = words.groupBy("word").count()

query = wordCounts.writeStream.outputMode("complete").format("console").start()
query.awaitTermination()
```

- **Source**：通过 `readStream` 定义输入源（socket / kafka / file 等）
- **Transformation**：DataFrame 操作（select / groupBy / join / window）
- **Sink**：通过 `writeStream` + `outputMode` + `format` 定义输出（console / kafka / file / foreach）

### 3.4 Output Mode

| 模式 | 含义 | 适用 |
|---|---|---|
| Append | 仅输出新增行（聚合不支持） | 行级追加场景 |
| Update | 输出被更新的行 | 状态化聚合（无界聚合） |
| Complete | 每次 Trigger 都输出完整结果 | 小结果集聚合（如 wordCount） |

### 3.5 Trigger

- 默认：尽快触发（As-Soon-As-Possible）
- `Trigger.ProcessingTime("N seconds")`：固定周期
- `Trigger.Once()`：单次触发（微批一次），常用于增量 ETL 准实时场景
- `Trigger.Continuous("N seconds")`：启用连续处理模式

### 3.6 容错机制

- **Checkpoint**：将 Streaming Query 的进度（已处理 offset 等）写入持久化存储（HDFS / S3 / OSS）
- **WAL（Write-Ahead Logs）**：Source 端把新事件先落日志后处理，保证故障时 replay 不丢
- **幂等 Sink**：Kafka sink（支持事务）保证 Exactly-Once；File sink 在分区级别幂等

## 4. 关键设计决策与权衡

### 决策 1：Micro-batch vs Continuous Processing

- **Micro-batch（本方案主流场景采用）**：延迟 ~100 ms；Exactly-Once；生态最完整
- **Continuous Processing**：延迟 ~1 ms；仅 At-Least-Once；仅少数 Source/Sink 支持
- **代价**：Continuous Processing 模式不支持某些聚合操作；状态管理 API 受限

### 决策 2：状态管理（RocksDB State Store）

- Spark 3.x 起 Structured Streaming 支持 RocksDB 状态后端（参考 KIP / SPARK-40217）；默认用堆内存
- 状态较大或聚合 key 数量多时建议切 RocksDB；调优成本与 Flink 类似

### 决策 3：Output Mode 选型

- **Append**：默认；适合无状态转换
- **Update / Complete**：聚合场景需考虑输出体量；Complete 在大结果集下开销大

### 决策 4：Watermark 策略

- 业务无乱序需求 → 可不设 Watermark（默认按处理时间）
- 业务有乱序 + 窗口聚合 → 必须设 Watermark + `withWatermark` + 容忍阈值
- **代价**：Watermark 过紧会丢数据；过松会显著拉大状态

## 5. 工程化要点

- **部署**：Spark Standalone / YARN / Kubernetes（Spark on K8s Operator 已是主流）
- **Checkpoint 存储**：可靠的分布式文件系统（HDFS / S3 / OSS）；建议使用对象存储 + 独立桶
- **资源配置**：Driver + Executor；Executor 内存与 Kafka Offsets 缓存、状态后端绑定
- **监控**：Spark Metrics（REST API）→ Prometheus Reporter；Structured Streaming 自带 UI（Streaming Query 页）展示输入速率、处理速率、批处理时长
- **运维**：Restart 任务时从 Checkpoint 恢复；状态 Schema 演进需谨慎；trigger intervals 与上游 Source 容量匹配
- **反压检测**：Spark UI 上的 Input Rate / Processing Rate 不平衡时考虑扩 Executor / 调 Trigger Interval

## 6. 指标映射

| 指标 | 口径示例 | 支撑手段 |
|---|---|---|
| 端到端延迟 | 事件入 Source → 输出 Sink ≤ X ms（Micro-batch ~100 ms；Continuous ~1 ms） | Trigger Interval + 微批处理时长 |
| 输入速率 | Records/s、KB/s | Spark UI Input Rate |
| 处理速率 | Records/s | Spark UI Process Rate |
| Checkpoint 时长 | 单次 Checkpoint ≤ M 秒 | Checkpoint 目录 + 异步化 |
| 状态大小 | 单 Executor 状态 ≤ N GB | RocksDB 后端 + TTL |
| Exactly-Once | Source + Sink 协同保证 | WAL + Kafka 事务 Sink |
| 失败恢复时间 | 重启 → Checkpoint 恢复 ≤ X 秒 | Checkpoint 周期 + State Store 体积 |

## 7. 标书化叙述示例

> 本方案的近实时数据通道采用 Apache Spark Structured Streaming。Source 端通过 Kafka Source 接入消息流，按事件时间构建无界表，触发方式选用 `Trigger.ProcessingTime("10 seconds")`，输出模式按业务选择（聚合指标场景使用 `Complete`、行级明细场景使用 `Append`）。流处理逻辑通过 DataFrame/SQL 表达，复用 Spark SQL 的 Catalyst 优化器与 Whole-Stage Code Generation。状态后端按数据量配置——中等状态使用默认堆内存，大状态切换为 RocksDB State Store；Checkpoint 周期与 Trigger interval 一致，状态快照持久化至 OSS 命名服务。Sink 端对 Kafka 启用 Kafka 事务 Sink，实现端到端 Exactly-Once；对对象存储启用分区幂等写入。通过 Spark REST API + Prometheus Reporter 上送 Input Rate、Process Rate、Batch Duration、Checkpoint Duration 四类指标；Spark UI 作为反压与倾斜定位入口。具体业务延迟 P99、状态规模上限、峰值 TPS 由用户在合同附件中按业务等级明确。

## 8. 风险与边界

- **不可编造项**：
  - Structured Streaming 各版本（3.x / 4.x）的 Continuous Processing 兼容性矩阵需回到官方文档核对
  - 具体延迟数字需实测或用户提供，不能引用未经验证的 benchmark
- **常见失败模式**：
  - Checkpoint 目录不可写 → 流任务立即失败；需独立部署对象存储
  - Watermark 过紧 → 窗口聚合丢数据
  - State Schema 演进不一致 → 任务启动失败
  - 聚合 Complete 模式输出过大 → 拖垮下游
- **与上游 Kafka 的耦合**：Kafka Source 的 Offset 管理依赖 `group.id` 与 `auto.offset.reset` 配置；与 Kafka Consumer 客户端语义不同
- **与 Flink 的边界**：Structured Streaming 偏「近实时 + SQL 复用」；极低延迟、复杂 CEP、严格 Exactly-Once 优先选 Flink