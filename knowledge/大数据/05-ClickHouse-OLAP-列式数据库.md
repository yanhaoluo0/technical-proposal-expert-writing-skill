# ClickHouse OLAP 列式数据库

> **素材来源**：https://clickhouse.com/docs/get-started/about/intro
> **抓取日期**：2026-08-28
> **整理方式**：技术深度型（八段卡片）。原始抓取为 ClickHouse 官方「What is ClickHouse」介绍页；本卡片围绕列式存储、向量化、MergeTree、复制等关键概念展开。
> **适用文档类型**：方案设计报告、技术标书「OLAP」「实时分析」「Ad-Hoc 查询」「日志分析」章节
> **可支撑的技术点**：ClickHouse, 列式存储, OLAP, MergeTree, 向量化执行, 多主复制, 角色访问控制, 自适应 JOIN, 近似计算, 分片, 高吞吐写入
> **写作约束**：术语沿用 ClickHouse 官方文档；不可编造具体性能基准。

## 1. 适用场景与触发词

需要「亿级~万亿行级数据的实时分析 + 列式存储 + 高并发查询」时命中本卡片：

- 业务场景：用户行为分析、Ad-Hoc 查询、BI 报表、日志分析、监控指标查询、A/B 测试平台
- 标书或设计报告关键词：「ClickHouse」「OLAP」「列式数据库」「实时分析」「日志分析」「Ad-Hoc」「高吞吐写入」「列存」

## 2. 技术内涵与边界

**做什么**：

- 列式（column-oriented）OLAP SQL 数据库，提供 ANSI SQL 兼容的声明式查询语言
- 针对分析查询（聚合、字符串处理、算术运算）在大规模数据集上达到毫秒级响应
- 支持异步多主复制（asynchronous multi-master replication）实现多副本数据冗余
- 提供 RBAC、近似计算、自适应 JOIN 算法

**不做什么**：

- 不擅长 OLTP 事务（高频单行写入 / 读取 / 更新）——不替代 MySQL / PostgreSQL
- 不擅长强一致事务（无跨表事务、无分布式事务）
- 不擅长实时高并发单点查询（毫秒级以下）——主键查询性能不如专用 KV
- 不等于 ETL 引擎——需配合 Kafka / Flink 做实时数据通道

## 3. 典型架构与关键机制

### 3.1 列式存储 vs 行式存储

> 官方原文：「ClickHouse is a column-oriented database. In such systems, tables are stored as a collection of columns, i.e. the values of each column are stored sequentially one after the other. This layout makes it harder to restore single rows (as there are now gaps between the row values) but column operations such as filters or aggregation become much faster than in a row-oriented database.」

- 行式：连续行依次存储；适合行级读取
- 列式：每列单独存储；适合聚合（只读相关列）

**官方示例**：1 亿行 web analytics 数据，查询 MobilePhoneModel + RegionID + EventDate 三列，ClickHouse 在 92 毫秒内完成，吞吐约 10 亿行/秒。

> 官方原文：「the query processed 100 million rows in 92 milliseconds, a throughput of approximately over 1 billion rows per second or just under 7 GB of data transferred per second.」

### 3.2 MergeTree 引擎族

- ClickHouse 的核心表引擎：MergeTree
- 数据写入生成多个 part，后台异步合并（merge）以提升查询效率
- 变体：ReplacingMergeTree（去重）、SummingMergeTree（聚合）、AggregatingMergeTree（自定义聚合）、CollapsingMergeTree（折叠）
- 主键不是唯一的（与 MySQL 不同），仅用于索引排序与裁剪

### 3.3 向量化执行

- 所有内存结构按列布局；减少虚函数调用；提升 CPU Cache 命中率；使用 SIMD 指令
- 官方文档表述：「memory structures laid out in a columnar format. This can largely reduce virtual function calls, increase cache hit rates, and make efficient use of SIMD instructions.」

### 3.4 异步多主复制

> 官方原文：「ClickHouse uses an asynchronous multi-master replication scheme to ensure that data is stored redundantly on multiple nodes. After being written to any available replica, all the remaining replicas retrieve their copy in the background. The system maintains identical data on different replicas. Recovery after most failures is performed automatically, or semi-automatically in complex cases.」

- 数据写入任意副本；其他副本后台拉取
- 多数故障场景下自动恢复；复杂场景需手动干预

### 3.5 SQL 兼容性

- 兼容 ANSI SQL 多数子集
- 支持 GROUP BY、ORDER BY、JOIN、IN、窗口函数、子查询
- 自有方言：Lambda 函数、AggregateFunction 状态类型、Arrays / Nested 数据结构、采样查询（`SAMPLE`）

### 3.6 近似计算

> 官方原文：「ClickHouse provides ways to trade accuracy for performance. For example, some of its aggregate functions calculate the distinct value count, the median, and quantiles approximately. Also, queries can be run on a sample of the data to compute an approximate result quickly.」

- `uniqHLL12`、`quantile`、`quantiles` 提供近似结果换取性能
- `SAMPLE k` 子句在数据子集上计算

### 3.7 自适应 JOIN

> 官方原文：「ClickHouse chooses the join algorithm adaptively: it starts with fast hash joins and falls back to merge joins if there's more than one large table.」

- 自动选择 hash join → merge join 降级

## 4. 关键设计决策与权衡

### 决策 1：ClickHouse vs Doris vs StarRocks

- **ClickHouse（本方案高吞吐写入 + 多副本生态采用）**：写入性能强；MergeTree 生态成熟；社区活跃
- **Doris**：MySQL 协议 + FE/BE 分离；强一致单表物化视图；运维友好
- **StarRocks**：CBO 优化器；向量化执行；实时数仓主流
- **代价**：ClickHouse 的事务、Update/Delete 弱；不擅长高 QPS 单行查询

### 决策 2：MergeTree 表引擎选型

- **MergeTree**：基础引擎
- **ReplacingMergeTree**：去重（按 ORDER BY 列）
- **SummingMergeTree**：数值列聚合
- **AggregatingMergeTree**：自定义状态聚合
- **代价**：变体引擎对查询语义有影响（如 ReplacingMergeTree 的「最终一致性」需靠 optimize final 强制合并）

### 决策 3：复制策略

- **ReplicatedMergeTree + ZooKeeper / ClickHouse Keeper**：多副本；通过 ZK 协调
- 单分片多副本：写入主副本，副本拉取
- **代价**：ZK 运维成本；副本延迟可能影响查询一致性

### 决策 4：分片（Sharding）

- 分布式表（Distributed table）+ 本地表（local table）
- 分片键选择影响数据分布与查询路由
- 跨分片 JOIN 性能差，优先考虑预先打宽表

## 5. 工程化要点

- **部署**：单实例 / 集群；ZK / ClickHouse Keeper 协调；推荐 K8s Operator（Altinity / ClickHouse Inc. 官方）
- **写入**：Batch Insert（推荐 10K~100K 行/批）；Kafka Engine 表对接 Kafka 流；MaterializedView 异步物化
- **查询**：高 QPS 业务加 `max_threads` / `max_memory_usage`；大结果集使用 `PREWHERE`
- **监控**：内置 system.metrics、system.events、system.query_log；Prometheus 集成 via clickhouse-exporter
- **运维**：
  - 定期 `OPTIMIZE TABLE ... FINAL`（慎用，IO 重）
  - 冷热分层：S3 冷存储 + 本地热盘
  - 备份：`BACKUP/RESTORE` 命令（v21+）
- **数据建模**：
  - 优先宽表（避免 JOIN）
  - ORDER BY 列选高频过滤列
  - LowCardinality 字典编码
  - 使用 `PREWHERE` 提前过滤

## 6. 指标映射

| 指标 | 口径示例 | 支撑手段 |
|---|---|---|
| 写入吞吐 | 单节点 ≥ X 万行/秒 | Batch Insert + Kafka Engine |
| 查询延迟 | P95 ≤ X ms | system.query_log + 索引优化 |
| 副本同步延迟 | ≤ N 秒 | system.replicas |
| 磁盘占用 | 压缩后 ≥ 10:1（与原始日志比） | Compression Ratio 监控 |
| 高可用 | 单副本失败自动恢复 | ReplicatedMergeTree + Keeper |
| 查询 QPS | 峰值 QPS ≤ M | max_threads + 资源池 |

## 7. 标书化叙述示例

> 本方案实时分析平台采用 ClickHouse 作为核心 OLAP 引擎，承担日志分析、用户行为查询、Ad-Hoc 报表三类业务负载。集群采用 ReplicatedMergeTree 多副本模式，副本数 2 起步，关键数据副本数 ≥ 3，通过 ClickHouse Keeper 替代 ZooKeeper 降低组件依赖。表引擎按业务选型——明细表使用 MergeTree，去重需求使用 ReplacingMergeTree，聚合指标使用 AggregatingMergeTree。写入路径采用 Kafka Engine 表对接 Kafka 流，配合 MaterializedView 实现近实时物化（延迟秒级）。查询路径对高频过滤列设置 LowCardinality 与 ORDER BY，配合 PREWHERE 提前裁剪。查询路由通过 Distributed 表实现跨分片查询；跨分片 JOIN 通过预先打宽表避免。运行时通过 system.metrics、system.query_log、system.replicas 三类系统表 + Prometheus Exporter 上送写入吞吐、查询延迟、磁盘占用、副本延迟四类指标；K8s Operator 负责集群扩缩。具体业务的写入吞吐、查询延迟、存储容量由用户在合同附件中按业务等级明确。

## 8. 风险与边界

- **不可编造项**：
  - 具体 QPS、延迟、压缩比必须实测或用户提供
  - ClickHouse 各版本（22.x / 23.x / 24.x）的特性差异（如 BACKUP/RESTORE、Lightweight Delete）需回到官方 Release Notes 核对
- **常见失败模式**：
  - 高频单行写入 → 拖垮集群；必须 Batch Insert
  - 跨分片 JOIN → 性能崩溃；预先打宽表
  - 不设 ORDER BY → 全表扫描；性能崩塌
  - ZK / Keeper 故障 → 副本协调失效；需高可用 Keeper 集群
- **架构外延**：本卡片聚焦 ClickHouse 内核；不涵盖 ClickHouse Cloud（托管服务）、chDB（嵌入式）等周边产品