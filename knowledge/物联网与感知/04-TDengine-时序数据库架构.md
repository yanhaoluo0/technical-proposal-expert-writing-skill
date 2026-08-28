# TDengine 时序数据库架构

> **素材来源**：https://tdengine.com/tsdb-architecture-core-technology-explained/
> **抓取日期**：2026-08-28
> **整理方式**：技术深度型（八段卡片）。原始 B4 前段含欧盟 cookie consent 导航（已剥离）。本卡片围绕 TDengine 分布式集群架构（mnode/vnode/qnode/snode）、一设备一表、超级表、LSM 列存、流处理等核心机制展开。
> **适用文档类型**：方案设计报告、技术标书「时序数据库」「工业物联网」「设备遥测」章节
> **可支撑的技术点**：TDengine, dnode, mnode, vnode, vgroup, qnode, snode, 一设备一表, Supertable, Tag, LSM, 列存, 分层存储, 流处理, 订阅, 存算分离
> **写作约束**：术语沿用 TDengine 官方文档（2026-07）；不可编造具体性能基准。

## 1. 适用场景与触发词

需要「海量设备遥测写入 + 一设备一表数据建模 + 内置流处理 + 国产时序数据库」时命中本卡片：

- 业务场景：工业物联网（IIoT）、能源监控、智能制造、车联网、智慧城市、设备预测性维护
- 标书或设计报告关键词：「TDengine」「时序数据库」「一设备一表」「超级表」「Supertable」「订阅」「流处理」「存算分离」

## 2. 技术内涵与边界

**做什么**：

- 高性能、分布式时序数据库；专为 IoT / 工业 / 能源场景设计
- 数据建模核心：「一设备一表」
- 超级表（Supertable）作为模板 + Tag 标签管理
- 存储引擎：LSM Tree + 列存；支持分层存储（热 SSD / 冷 S3）
- 内置流处理（snode）；订阅（Subscription）；缓存（Cache）
- 存算分离架构

**不做什么**：

- 不擅长 OLTP——单行 UPSERT 非首选
- 不擅长大规模 JOIN（IoT 时序查询场景不常见）
- 不擅长跨数据中心复制——主主复制有边界
- 不替代 InfluxDB / TimescaleDB 等——特定场景对比

## 3. 典型架构与关键机制

### 3.1 分布式集群拓扑

> 官方原文：「A TDengine cluster is built from dnodes (Data Nodes). Each dnode is a running instance of the taosd process and can host multiple logical node types:」

dnode（Data Node）是物理进程 `taosd`；一个 dnode 上可承载多种逻辑节点：

- **mnode（Management Node）**：管理集群元数据、用户、协调；多个 mnode 组成 HA 组（基于 Raft）
- **vnode（Virtual Node）**：核心数据存储与查询执行单元；管理时序数据子集；独立处理写入、查询、压缩
- **vgroup（Virtual Group）**：一个或多个 vnode 复制同一数据分片；提供 HA
- **qnode（Query Node）**：跨 vnode 查询；将 Supertable 查询分解为子查询并合并
- **snode（Stream Node）**：执行流处理任务；至少一个 snode；多个可负载均衡 + HA

### 3.2 存算分离

> 官方原文：「TDengine supports Storage-Compute Separation. vnodes handle storage; qnodes and snodes handle compute. The two layers scale independently.」

- vnode 负责存储；qnode / snode 负责计算
- 查询负载增加 → 增加 qnode
- 写入或存储瓶颈 → 增加 vnode / dnode
- 独立扩缩避免「一维过配」

### 3.3 数据模型：一设备一表

> 官方原文：「The core data modeling principle in TDengine is 'One Table per Device.' Each sensor, machine, or data collection point receives its own table. This is not a workaround. It is the fundamental design.」

```
CREATE TABLE t_001 (ts TIMESTAMP, current FLOAT, voltage INT, phase FLOAT);
```

- 每设备一张表，写入无锁、append-only
- 不同设备不争夺同一写入路径
- 物理世界天然映射（风电场 500 风机 → 500 张表）

### 3.4 超级表（Supertable）+ Tag 系统

```
CREATE STABLE meters (ts TIMESTAMP, current FLOAT, voltage INT, phase FLOAT)
TAGS (location BINARY(64), group_id INT);

CREATE TABLE t_001 USING meters TAGS ("Building_A", 1);
```

- 超级表定义共享 schema + tag 结构
- 子表继承 schema 并提供自己的 tag 值
- tag 与时序数据分离存储并索引 → 按 tag 过滤快速

### 3.5 与其他数据模型对比

| 维度 | TDengine（一设备一表） | 传统 RDBMS | 其它 TSDB（measurement + tags） |
|---|---|---|---|
| 数据组织 | 每设备表 | 共享宽表 / 分区表 | 以度量为中心的 measurement |
| 写入冲突 | 每设备无锁 | 行级 / 表级锁 | 视实现而定 |
| 单设备查询 | 单表扫描，快 | WHERE 过滤 | tag 过滤 |
| 跨设备聚合 | Supertable 查询 via qnode | 复杂 JOIN / UNION | measurement + GROUP BY tags |
| 高基数 | 原生支持 | 索引压力大 | tag 索引压力大 |

### 3.6 存储引擎：LSM 列存

> 官方原文：「TDengine uses an LSM Storage Engine design, adapted for time-series data. Writes land in a MemTable (in-memory buffer) and are flushed to persistent SSTable files on disk.」

- 写入：MemTable → SSTable（持久化）
- 时序数据 append-only + 时间顺序 → SSTable 在时间维度自然不重叠 → compaction 比通用 LSM 更简单

### 3.7 列存与压缩

> 官方原文：「Data within each SSTable is stored in columnar format.」

- 同类型相邻存储 → 压缩比远高于行存
- 类型特定编码：delta-of-delta（时间戳）、ZigZag（整数）、XOR（浮点）
- 通用压缩器：LZ4 / ZLIB / ZSTD / XZ
- 典型压缩比 10:1；有损压缩可达 20:1

### 3.8 分层存储

> 官方原文：「TDengine supports tiered storage. Hot data stays on local SSD for fast access. Warm and cold data can migrate to low-cost object storage (S3 or compatible).」

- 热数据：本地 SSD
- 温 / 冷数据：S3 / OSS / HDFS
- 按数据库级保留策略自动迁移

### 3.9 查询引擎：虚拟表聚合

- Supertable 查询（如 `SELECT AVG(current) FROM meters WHERE group_id=1 INTERVAL(1h)`）通过 qnode 拆解
- Tag 过滤 → 子查询分解 → 各 vnode 并行执行 → 结果合并
- 可分解聚合（SUM、COUNT、MIN、MAX）直接合并
- 不可分解聚合（AVG、STDDEV）从组件值重建

### 3.10 流处理

- snode 执行流处理任务
- 至少一个 snode；多个可负载均衡 + HA

### 3.11 订阅（Subscription）

- 应用可订阅「超级表 / 子表」变更
- 类 Kafka 消费语义

## 4. 关键设计决策与权衡

### 决策 1：TDengine vs InfluxDB vs TimescaleDB

- **TDengine（本方案海量设备 + 一设备一表建模场景采用）**：写吞吐强；压缩比高；国产化场景
- **InfluxDB**：生态成熟；Telegraf 集成多
- **TimescaleDB**：SQL 友好；PostgreSQL 兼容
- **代价**：TDengine 客户端库不如 InfluxDB 丰富；学习曲线较陡

### 决策 2：存算一体 vs 存算分离

- **存算一体（中小规模采用）**：性能高；运维简单
- **存算分离（大规模 / 弹性需求采用）**：独立扩缩；冷数据成本低
- **代价**：存算分离架构下数据访问延迟略高（拉网络）

### 决策 3：数据模型

- **一设备一表（TDengine 原生）**：写入无锁；天然映射
- **宽表（InfluxDB / Prometheus）**：schema 简单；高基数压力大
- **代价**：一设备一表下 SQL / BI 工具需通过 Supertable 抽象；初次接触者可能不适应

### 决策 4：流处理内置 vs 外置

- **TDengine 内置 snode（本方案简单流处理采用）**：无外部依赖；运维简单
- **Flink / Spark Streaming（复杂 CEP / 跨源采用）**：能力强；运维复杂
- **代价**：内置 snode 流处理能力有限；复杂流逻辑用 Flink

## 5. 工程化要点

- **部署**：
  - 物理机 / 虚拟机 / K8s
  - 集群至少 3 节点；mnode 至少 3 副本
- **客户端**：
  - C / Java / Python / Go / Rust / Node.js
  - REST API
- **数据接入**：
  - 设备直连（MQTT / TCP / 自定义）
  - Telegraf 集成（TDengine 输出插件）
  - Kafka Connect
- **查询**：
  - SQL 接口
  - Grafana / BI 工具集成
- **监控**：
  - 内置监控数据库
  - Prometheus Exporter
- **运维**：
  - 滚动升级
  - 数据迁移（存算分离）
  - 备份与恢复

## 6. 指标映射

| 指标 | 口径示例 | 支撑手段 |
|---|---|---|
| 设备表数量 | 单数据库 ≤ N 万张 | 设备建模规划 |
| 写入吞吐 | 单 dnode ≥ X 万点/秒 | 批量写入 + 调优 |
| 压缩比 | ≥ 10:1（vs 原始） | 类型编码 + ZSTD/LZ4 |
| 查询延迟 | 单设备查询 ≤ N ms | 子表扫描 + 索引 |
| 跨设备聚合延迟 | Supertable 查询 ≤ M 秒 | qnode 并行 + 索引 |
| 流处理延迟 | 事件触发 → 输出 ≤ Y 秒 | snode 监控 |

## 7. 标书化叙述示例

> 本方案工业物联网数据存储采用 TDengine。数据建模按业务域划分数据库——`factory_data`、`energy_data`、`device_telemetry`；每设备一张表（命名 `t_{device_id}`），通过 Supertable `meters` 提供 schema 模板与 Tag（location、group_id）索引。集群采用 5 节点部署（dnode），每个 dnode 承载 mnode（HA 组 3 副本）、vnode、qnode、snode 四类逻辑节点，按存算分离架构运行（vnode 负责存储，qnode/snode 负责计算与流处理）。写入采用设备端 SDK 批量写入（每批 5000~10000 点），写入路径经 Kafka 削峰后落 TDengine。查询层分两条路径——单设备查询直接命中子表；跨设备聚合经 Supertable 查询由 qnode 拆解并行执行。内置流处理（snode）实现简单实时统计（如设备超阈值告警）。运行时通过监控数据库 + Prometheus Exporter 上送写入吞吐、压缩比、查询延迟、流处理延迟四类指标。具体业务的设备规模、写入峰值、查询延迟、保留周期由用户在合同附件中按业务等级明确。

## 8. 风险与边界

- **不可编造项**：
  - 具体写入吞吐、查询延迟、压缩比必须实测或 TDengine 官方 benchmark 提供
  - TDengine 各版本（3.x）的特性差异（存算分离、Subscription、Stream）需回到官方 Release Notes 核对
- **常见失败模式**：
  - 高基数标签 → 索引膨胀；治理标签设计
  - 跨 vgroup JOIN → 性能差；避免跨设备 JOIN
  - snode 单点 → 至少 2 副本
  - 集群脑裂 → mnode 至少 3 节点 + Raft
- **架构外延**：本卡片聚焦 TDengine 内核；不涵盖 taosX（边缘）、TDengine Cloud、TDengine IDMP 等周边产品