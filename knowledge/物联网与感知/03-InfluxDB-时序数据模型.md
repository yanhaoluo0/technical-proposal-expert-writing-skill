# InfluxDB 时序数据模型

> **素材来源**：https://www.influxdata.com/time-series-database/ + InfluxDB v3 官方文档（关于 TSI 索引引擎）
> **抓取日期**：2026-08-28
> **整理方式**：技术深度型（八段卡片）。原始 B3 为「Why Time Series Matters」白皮书导论（40KB）。本卡片精选数据模型（Measurement / Tags / Fields / Timestamp）、三类工作负载模式、TSI 索引引擎核心机制。
> **适用文档类型**：方案设计报告、技术标书「时序数据库」「监控指标」「IoT 数据存储」章节
> **可支撑的技术点**：InfluxDB, Line Protocol, Measurement, Tagset, Field, Timestamp, TSI, TSM, 工作负载模式, 运维, 分析, 数字孪生, Flux, SQL, Telegraf
> **写作约束**：术语沿用 InfluxData 官方文档；不可编造具体性能基准。

## 1. 适用场景与触发词

需要「时间序列数据的高频写入 + 多维度标签查询 + 长期保留 + 实时分析」时命中本卡片：

- 业务场景：DevOps 监控、APM、IoT 遥测、网络设备遥测、电池储能（BESS）、卫星遥测、金融行情
- 标书或设计报告关键词：「InfluxDB」「时序数据库」「TSDB」「Line Protocol」「Telegraf」「时间序列」「TSI」「TSM」「降采样」

## 2. 技术内涵与边界

**做什么**：

- 时序数据库（Time Series Database）；高频写入、多维度标签、低延迟查询
- 数据模型：Measurement（度量）+ Tagset（标签键值对）+ Field（字段值）+ Timestamp
- 内置 Telegraf 采集器生态；200+ 集成
- v2.x 提供 Flux 查询；v3.x 转向 SQL 查询 + Apache Arrow 引擎
- 支持三类工作负载：Operational（实时监控）、Analytical（历史分析）、Digital Engineering（闭环控制）

**不做什么**：

- 不擅长事务（OLTP）——单行更新性能非首要目标
- 不擅长跨实体 JOIN——时序查询为主
- 不替代 OLAP（ClickHouse / Doris）——大规模历史分析选型不同
- 不擅长跨数据中心复制（InfluxDB v3 Cloud 提供，OSS 能力有限）

## 3. 典型架构与关键机制

### 3.1 数据模型

> 官方原文：「The InfluxDB platform organizes time series in a structured format. At the top level is a measurement name, followed by a set of key/value pairs called tags that describe the metadata, followed by key/value pairs of the actual values called fields. Field values in InfluxDB can be boolean, int64, float64, or strings. Finally, there is a timestamp for the set of values. All data is queried by measurement, tags, field and time.」

- **Measurement**：度量名（如 `cpu_usage`、`temperature`）
- **Tagset**：标签键值对，索引化（如 `host=server01, region=us-west`）
- **Field**：字段值，未索引（如 `usage_idle=98.5, usage_user=1.5`）
- **Timestamp**：纳秒精度

### 3.2 Line Protocol（写入格式）

```
measurement,tag1=value1,tag2=value2 field1=v1,field2=v2 timestamp
```

例：`temperature,location=room1,sensor=s01 value=23.5 1620000000000000000`

### 3.3 三类工作负载模式

> 官方原文：「Time series workloads fall into three overlapping patterns: Operational / Analytical / Digital Engineering.」

| 工作负载 | 特征 | 需求 |
|---|---|---|
| Operational（运维） | 实时监控、低延迟告警 | 高吞吐写入、低延迟查询、高分辨率、短保留 |
| Analytical（分析） | 历史分析、容量规划 | 聚合、长期保留、大范围扫描 |

### 3.4 存储引擎（v2.x）

- **TSM（Time-Structured Merge Tree）**：类似 LSM Tree；数据按时间分片压缩
- **TSI（Time Series Index）**：倒排索引；按 measurement + tagset 索引，加速标签查询
- 数据写入：先写 WAL → 内存中 → 定期刷盘 → Compaction

### 3.5 查询引擎

- **v2.x**：Flux（函数式查询语言）
- **v3.x**：SQL（标准 SQL）+ Apache Arrow 列式执行
- 内置连续查询（Continuous Query）实现自动降采样（v2.x）；v3.x 改用 Tasks + Scheduled Queries

### 3.6 典型业务场景

> 官方文档表述：

- **Digital Infrastructure（DevOps、APM、Kubernetes、Networks）**：容器、虚拟机、应用、网络设备的高基数遥测
- **Real-Time Analytics Applications**：业务事件流分析、实时仪表板
- **Battery Energy Storage Systems（BESS）**：电池储能遥测——电压、电流、温度、SOC、SOH
- **Satellite Telemetry and Control（TTC）**：卫星遥测——功率、热控、姿态、推进、子系统状态
- **Industrial Internet of Things（IIoT）**：制造、油气、运输、基础设施的过程变量（压力、流量、振动、温度）

### 3.7 时序管理挑战

- **Operational Workload Challenges**：高采样率（每秒到毫秒）+ 高基数（独立时序数量大）+ 无背压
- **Analytical Workload Challenges**：跨长时间范围扫描 + 多独立时序聚合 + 序列不对齐

## 4. 关键设计决策与权衡

### 决策 1：InfluxDB vs TDengine vs TimescaleDB

- **InfluxDB（本方案通用场景采用）**：生态成熟；Telegraf + 200+ 集成
- **TDengine**：国内时序数据库；一设备一表；订阅功能
- **TimescaleDB**：PostgreSQL 扩展；SQL 友好
- **代价**：InfluxDB v2 → v3 不兼容（数据需要迁移）

### 决策 2：v2.x vs v3.x

- **v2.x（Flux + TSM）**：成熟生态；UI + CLI + API 完善
- **v3.x（SQL + Apache Arrow）**：标准 SQL；性能更强；新平台
- **代价**：v2 → v3 迁移成本高；新项目建议直接 v3

### 决策 3：保留策略

- **无限保留**：存储成本不可控
- **固定保留 + 降采样**：高频数据保留 N 天，自动降采样后长期保留
- **分桶策略**：不同业务不同桶；优化压缩与查询
- **代价**：降采样数据丢失原始精度

### 决策 4：高基数优化

- 高基数标签（device_id、user_id）会显著放大 TSI 索引
- 限制标签基数（≤ 100K）；高基数标签转为 Field

## 5. 工程化要点

- **部署**：
  - OSS 单实例 / OSS 集群（InfluxDB v2 OSS 不支持水平扩展；v3 OSS 仍受限）
  - Cloud（多副本 + 跨可用区）
  - K8s 上 InfluxDB Operator（社区）
- **写入**：
  - Telegraf 采集（推荐；200+ 集成）
  - Line Protocol（HTTP API）
  - 客户端库：Go / Java / Python / JavaScript
  - 批量写入（5000 点/批）
- **查询**：
  - v2.x：Flux；v3.x：SQL
  - Grafana 集成
- **降采样**：
  - v2.x：Continuous Query
  - v3.x：Tasks + Scheduled Queries
- **监控**：
  - `/metrics` 端点（InfluxDB v2 OSS 提供 Prometheus Exporter）
  - 自监控数据库（`_internal`）
- **运维**：
  - Compaction 监控
  - TSI 索引重建（高基数场景）
  - 备份与恢复（v2 Enterprise；v3 OSS 不完整）

## 6. 指标映射

| 指标 | 口径示例 | 支撑手段 |
|---|---|---|
| 写入吞吐 | 单实例 ≥ N 万点/秒 | 批量写入 + Line Protocol |
| 查询延迟 | P95 ≤ X ms | TSI 索引 + 降采样 |
| 存储压缩比 | ≥ 10:1（vs 原始） | TSM 引擎 + 编码 |
| 高基数标签数 | 单 measurement ≤ M 个 | 标签基数治理 |
| 降采样周期 | 高频数据 → 1 分钟聚合 → 30 天保留 | Continuous Query / Tasks |
| 监控覆盖率 | 业务系统 ≥ X% 接入 | Telegraf 集成 |

## 7. 标书化叙述示例

> 本方案时序数据存储采用 InfluxDB。设备遥测通过 Telegraf 采集（200+ 集成覆盖容器、数据库、网络设备、MQTT 等数据源），Line Protocol 批量写入（5000 点/批）。数据模型按业务域拆分 measurement——`device_telemetry`、`app_metrics`、`network_metrics` 等；标签设计按业务过滤维度（如 `site_id`、`device_type`、`region`），高基数维度（device_id、user_id）严格控制并转为 Field。查询层分两条路径——实时监控使用 v2 Flux / v3 SQL 通过 Grafana 可视化；历史分析通过降采样（Continuous Query / Tasks）保留长期聚合。运行时通过 `/metrics` 端点 + Prometheus Exporter 上送写入吞吐、查询延迟、TSI 索引大小、降采样覆盖范围四类指标；监控采集与告警联动 Grafana AlertManager。具体业务的写入峰值、查询延迟、保留周期由用户在合同附件中按业务等级明确。

## 8. 风险与边界

- **不可编造项**：
  - 具体写入吞吐、查询延迟、压缩比必须实测或 InfluxData 官方 benchmark 提供
  - InfluxDB v2 / v3 的兼容性、迁移成本需回到官方 Migration Guide 核对
- **常见失败模式**：
  - 高基数标签 → TSI 索引爆炸；治理标签基数
  - 连续查询未设置 → 长期数据未降采样；存储膨胀
  - 标签误用 Field → 查询性能差；重新设计数据模型
  - v2 → v3 升级 → 数据迁移；新项目直接 v3
- **架构外延**：本卡片聚焦 InfluxDB 内核；不涵盖 InfluxDB Cloud（托管服务）、InfluxDB Enterprise（商业版高级特性）、Kapacitor（流处理）