# Apache Iceberg 数据湖表格式

> **素材来源**：https://iceberg.apache.org/spec/
> **抓取日期**：2026-08-28
> **整理方式**：技术深度型（八段卡片）。原始抓取为完整 Table Spec（191KB），本卡片精选 Goals / Overview / Spec 中 Snapshot、Manifest、Manifest List、Optimistic Concurrency、Sequence Numbers、Row-level Deletes 等核心概念。
> **适用文档类型**：方案设计报告、技术标书「数据湖表格式」「ACID 表」「湖仓一体」「隐藏分区」章节
> **可支撑的技术点**：Iceberg, Snapshot, Manifest, Manifest List, Optimistic Concurrency, Sequence Number, Row-level Delete, Hidden Partition, Schema Evolution, Partition Evolution, Parquet, Avro, ORC, v1/v2/v3, V4
> **写作约束**：术语沿用 Apache Iceberg 官方规范；不可编造具体性能基准。

## 1. 适用场景与触发词

需要「数据湖之上的 ACID 表 + 模式与分区演进 + 隐藏分区 + 多引擎（Spark/Flink/Trino）兼容」时命中本卡片：

- 业务场景：湖仓一体（Lakehouse）、跨引擎数据共享、海量数据集增量更新、合规审计归档
- 标书或设计报告关键词：「Apache Iceberg」「数据湖表格式」「ACID 表」「Snapshot」「隐藏分区」「Schema Evolution」「Partition Evolution」「Row-Level Delete」

## 2. 技术内涵与边界

**做什么**：

- 为分布式文件系统（S3 / HDFS / OSS / GCS）上的大数据集合（Parquet / Avro / ORC）提供「表」抽象
- 提供 Serializable 隔离（读不被写阻塞，写不被读阻塞）
- 支持 Schema Evolution、Partition Evolution、Row-level Delete
- 支持 Hidden Partition（隐藏分区）
- 与 Spark、Flink、Trino、Hive、Presto、DuckDB、ClickHouse、Doris 等多引擎兼容

**不做什么**：

- 不替代数据库——Iceberg 是表格式，不是数据库引擎
- 不替代 Parquet / ORC 等文件格式——它「管理」这些文件
- 不替代数据湖存储（S3 / HDFS）——它是存储之上的元数据层
- 单表事务 / 跨表事务不直接提供（依赖执行引擎）

## 3. 典型架构与关键机制

### 3.1 设计目标（Goals）

> 官方原文：

- **Serializable isolation**：读与并发写隔离；写操作增加或删除文件是原子的；读者不获取锁
- **Speed**：scan 规划使用 O(1) 远程调用（非 O(n) 随表大小增长）
- **Scale**：规划主要由客户端执行，不瓶颈于中心化元数据存储
- **Evolution**：完整支持 Schema 与 Partition Spec 演进；Schema 演进支持嵌套结构的列 add / drop / reorder / rename
- **Dependable types**：核心类型有良好定义
- **Storage separation**：分区是表配置；读规划使用数据值谓词而非分区值；支持分区方案演进
- **Formats**：底层文件格式支持一致的 schema 演进规则与类型；读写优化格式并存

### 3.2 总体结构

> 官方原文：「This table format tracks individual data files in a table instead of directories. This allows writers to create data files in-place and only adds files to the table in an explicit commit.」

- 表的状态维护在元数据文件（metadata files）中
- 任何变更生成新元数据文件 + 原子 swap 旧文件
- 表元数据记录：schema、partitioning config、custom properties、snapshots
- Snapshot 表示表在某个时刻的状态

### 3.3 Snapshot / Manifest / Manifest List

- **Data file**：实际数据文件（Parquet / Avro / ORC）
- **Manifest**：记录数据文件的列表（每行 = 一个数据文件的元信息 + 分区数据 + 指标）
- **Manifest List**：一个 snapshot 对应一个 manifest list，列出该 snapshot 的所有 manifest；含分区统计与数据文件数
- Manifest 可被多个 snapshot 复用（slow-changing 元数据不重写）
- 一个 snapshot 的数据是其所有 manifest 中 live files 的并集（每个 live file 最多一次）

### 3.4 Optimistic Concurrency

> 官方原文：「An atomic swap of one table metadata file for another provides the basis for serializable isolation. Readers use the snapshot that was current when they load the table metadata and are not affected by changes until they refresh and pick up a new metadata location.」

- 写者基于当前 metadata 乐观创建新 metadata，提交时通过元数据指针原子 swap
- 失败重试：若基于的 snapshot 不再 current，重试基于新 current 重做
- 满足条件：例如「重写文件」操作可应用于新 snapshot，只要重写文件仍在表中

### 3.5 Sequence Numbers

> 官方原文：「The relative age of data and delete files relies on a sequence number that is assigned to every successful commit.」

- 每次成功 commit 分配 sequence number
- 数据 / 删除文件、manifest、snapshot 携带 sequence number
- 新文件以 `null` 写入，读取时用 manifest 的 sequence number 替换
- 「existing」文件继承 manifest 的 sequence number，确保不可变

### 3.6 Row-level Deletes（V2+）

> 官方原文：「The primary change in version 2 adds delete files to encode rows that are deleted in existing data files.」

两种类型：

- **Position deletes**：通过 data file path + 行位置标记删除（V2 存 position delete file；V3+ 用 deletion vector）
- **Equality deletes**：通过一列或多列值标记删除（如 `id = 5`）

### 3.7 Format Versioning

- **V1**：管理 Parquet / Avro / ORC 大型分析表（不可变文件 + 增删文件）
- **V2**：在 V1 基础上加 Row-level Updates / Deletes
- **V3**：扩展数据类型与能力（nanosecond timestamp(tz)、unknown、variant、geometry、geography）；列默认值；多参数 transform；Row Lineage；二进制删除向量；表表加密
- **V4**：元数据结构重组（开发中，未正式采用）；支持 metadata 中的相对路径（relative locations）

### 3.8 Schema / Partition Evolution

- Schema Evolution：安全 add / drop / reorder / rename 列，包括嵌套结构
- Partition Evolution：分区方案可演进；读规划使用数据值谓词而非分区值（避免「重写历史分区」）

### 3.9 文件系统要求

- In-place write（文件不可变）
- Seekable reads
- Deletes（表可以删除不再使用的文件）
- 无需随机写；无需 rename（除非用 atomic rename 提交 metadata）

## 4. 关键设计决策与权衡

### 决策 1：Iceberg vs Delta Lake vs Apache Hudi

- **Iceberg（本方案多引擎兼容 + 隐藏分区采用）**：规范驱动；多引擎支持最广；Spec 演进路径清晰
- **Delta Lake**：与 Spark 生态深度绑定；湖仓一体首选
- **Hudi**：Copy-on-Write / Merge-on-Read 双模式；擅长增量 ETL
- **代价**：Iceberg 在 Spark 生态中部分功能（Row-level Delete）依赖执行引擎实现质量

### 决策 2：Format Version 选型

- **V1**：仅追加 + 不可变；轻量；适合纯流式日志
- **V2（本方案主流采用）**：Row-level Delete + 严格写者要求；典型湖仓
- **V3**：高级类型 + Row Lineage；执行引擎支持度逐步增加
- **代价**：V2 / V3 写者要求更严；老引擎需升级

### 决策 3：Catalog 选型

- **REST Catalog**：跨引擎共享；当前推荐
- **Hive Catalog**：与 Hive Metastore 集成
- **Glue / Nessie Catalog**：云厂商或专用元数据服务
- **代价**：不同 Catalog 的并发控制、审计、跨区域能力差异大

### 决策 4：删除策略

- **Position Deletes**：定位精确；写入开销小；读时合并
- **Equality Deletes**：依赖 Join 谓词；写者开销大；读时合并代价高

## 5. 工程化要点

- **存储**：S3 / HDFS / OSS / GCS / Azure Blob
- **Catalog**：REST Catalog / Hive Metastore / AWS Glue / Project Nessie
- **写入**：
  - Spark：`df.writeTo("db.tbl").append()` / `.overwritePartitions()` / `.create()`
  - Flink：`FlinkSink.forRowData().append()`
  - Trino：`INSERT INTO ...`
- **读取**：
  - 支持 Time Travel（`AS OF` 语法 + snapshot id / timestamp）
  - 支持 Hidden Partition（用户写查询时无需写分区列，自动按分区裁剪）
- **运维**：
  - `expire_snapshots` 清理过期 snapshot
  - `remove_orphan_files` 清理孤立文件
  - `rewrite_manifests` 合并 manifest 提升规划效率
  - `rewrite_data_files`（Compaction）压缩小文件
- **监控**：表 metadata 大小、snapshot 数量、文件数、Compaction 状态

## 6. 指标映射

| 指标 | 口径示例 | 支撑手段 |
|---|---|---|
| 元数据大小 | 单表 metadata.json ≤ M MB | 定期 `rewrite_manifests` |
| Snapshot 数量 | 单表 ≤ N 个 | `expire_snapshots` |
| 文件数量 | 单分区 ≤ N 个 | `rewrite_data_files` |
| 查询规划时间 | Plan ≤ M 秒（O(1) 远程调用） | 监控 manifest 数量 |
| 写入吞吐 | Spark Append ≥ Y MB/s | 批量写入调优 |
| 删除准确率 | 99.99%（Row-level Delete 后） | Position/Equality Delete 合并 |

## 7. 标书化叙述示例

> 本方案湖仓一体采用 Apache Iceberg 表格式作为数据湖之上的表格式层。原始 Parquet / Avro 文件由 Spark、Flink、Trino 多引擎写入 Iceberg 表；元数据通过 REST Catalog 统一管理，跨引擎共享。表设计采用 V2 格式版本，支持 Row-level Delete（Position Deletes + Equality Deletes）；分区采用 Hidden Partition（用户查询不需显式写分区列，按数据值谓词自动裁剪）。Schema Evolution 与 Partition Evolution 在演进过程中无需重写历史数据。时间旅行（Time Travel）通过 snapshot id 或 timestamp 查询历史版本。写入路径按场景选择——Spark 批处理走 DataFrameWriter，Flink 实时增量走 FlinkSink，Trino 即席查询走 INSERT INTO。运维自动化包括：`expire_snapshots` 周期性清理过期 snapshot；`rewrite_manifests` 合并 manifest；`rewrite_data_files` Compaction 合并小文件。监控通过 Iceberg REST Catalog 提供的审计日志 + Prometheus 上送元数据大小、Snapshot 数量、文件数量、Compaction 时长四类指标。具体业务的元数据规模、Compaction 周期、查询性能等数值由用户在合同附件中按业务等级明确。

## 8. 风险与边界

- **不可编造项**：
  - 各引擎对 V2 / V3 的支持度差异需回到官方兼容性矩阵（如 `https://iceberg.apache.org/multi-engine/`）
  - 具体性能基准（写入吞吐、查询延迟、Compaction 时长）必须实测或用户提供
- **常见失败模式**：
  - Snapshot 无限累积 → 必须 `expire_snapshots`
  - 小文件过多 → 必须 `rewrite_data_files`
  - 跨引擎 Schema 不一致 → 统一类型映射表
  - Catalog 高可用失效 → 选择多可用区 / 多副本 Catalog
- **架构外延**：本卡片聚焦 Iceberg 表格式；不涵盖 Puffin（统计文件）、Z-order（多维排序）、Bloom Filter 等高级特性

---

