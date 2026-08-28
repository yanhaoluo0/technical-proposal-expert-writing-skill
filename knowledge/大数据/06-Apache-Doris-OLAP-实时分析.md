# Apache Doris OLAP 实时分析

> **素材来源**：https://doris.apache.org/docs/3.x/gettingStarted/what-is-apache-doris
> **抓取日期**：2026-08-28
> **整理方式**：技术深度型（八段卡片）。原始抓取末尾含 hCaptcha 等导航内容（已被剔除）。本卡片围绕 FE / BE 拓扑、存算一体 vs 存算分离、向量化执行引擎、Pipeline 执行引擎、三种数据模型展开。
> **适用文档类型**：方案设计报告、技术标书「实时数据仓库」「MySQL 兼容 OLAP」「湖仓一体」章节
> **可支撑的技术点**：Apache Doris, MPP, FE, BE, 存算一体, 存算分离, 向量化, Pipeline 执行引擎, CBO/RBO/HBO, 强一致物化视图, 数据模型, Duplicate Key, Unique Key, Aggregate Key, MySQL 协议, 湖仓加速
> **写作约束**：术语沿用 Apache Doris 官方文档；不可编造具体性能基准。

## 1. 适用场景与触发词

需要「MySQL 兼容 + 实时数据仓库 + 高并发点查 + 高吞吐复杂分析」时命中本卡片：

- 业务场景：实时报表、用户行为分析、用户画像、A/B 测试、日志分析、电商订单分析、湖仓查询加速
- 标书或设计报告关键词：「Apache Doris」「实时数据仓库」「MPP」「FE」「BE」「MySQL 兼容」「存算一体」「存算分离」「湖仓加速」

## 2. 技术内涵与边界

**做什么**：

- 基于 MPP（Massively Parallel Processing）架构的实时数据仓库；高查询速度、大数据集亚秒级返回
- 支持高并发点查询与高吞吐复杂分析
- MySQL 协议兼容，标准 SQL 语法；与 MySQL、Hive 函数高度兼容
- 自 3.0 起支持存算分离（compute-storage decoupled）架构
- 支持多种数据模型：Duplicate Key（明细）、Unique Key（主键）、Aggregate Key（聚合）

**不做什么**：

- 不替代 OLTP 数据库（MySQL / PostgreSQL）——非事务型业务首选
- 不擅长高频单行 UPSERT（Doris 主键模型在点查性能上优秀但批量导入吞吐仍是大优势场景）
- 不内置 ETL 调度——配 Airflow / DolphinScheduler 做编排

## 3. 典型架构与关键机制

### 3.1 存算一体架构（默认）

> 官方原文：「Apache Doris uses the MySQL protocol, is highly compatible with MySQL syntax, and supports standard SQL.」

仅两类进程：

- **Frontend (FE)**：用户请求处理、查询解析与规划、元数据管理、节点管理
- **Backend (BE)**：数据存储与查询执行；数据分片，多副本跨 BE 节点

FE 节点分三类角色：

| FE 角色 | 职责 |
|---|---|
| Master | 元数据读写；变更通过 BDB JE 协议同步到 Follower / Observer |
| Follower | 读取元数据；Master 故障时选举为新 Master |
| Observer | 读取元数据；增加查询并发；不参与选举 |

FE 与 BE 横向扩展；FE 与 BE 通过一致性协议确保高可用。整套集群可支持数百台机器与数十 PB 存储。

### 3.2 存算分离架构（3.0+）

> 官方原文：「Starting from version 3.0, a compute-storage decoupled deployment architecture can be chosen.」

三层结构：

- **Metadata Layer（元数据层）**：请求规划、查询解析与规划、元数据存储
- **Compute Layer（计算层）**：多计算组（compute group），每组独立租户；BE 无状态，可弹性扩缩
- **Storage Layer（存储层）**：S3 / HDFS / OSS / COS / OBS / Minio / Ceph 等共享存储

### 3.3 存储引擎

> 官方原文：「Apache Doris has a columnar storage engine, which encodes, compresses, and reads data by column.」

索引结构：

- **Sorted Compound Key Index**：最多三列复合排序键；高并发报表场景有效裁剪
- **Min/Max Index**：数值类型等值与范围过滤
- **BloomFilter Index**：高基数列等值过滤
- **Inverted Index**：任意字段的快速搜索

### 3.4 数据模型

| 模型 | 用途 |
|---|---|
| Duplicate Key Model（明细） | 事实表的明细存储 |
| Primary Key Model（Unique Key Model） | 同 key 覆盖；支持行级更新 |
| Aggregate Key Model | 同 key 合并值列；预聚合加速 |

### 3.5 查询引擎

- 全向量化执行（fully vectorized）；内存结构列式布局；SIMD 利用
- Pipeline 执行引擎：查询拆解为多子任务并行；解决线程爆炸；减少数据拷贝
- 自适应查询执行：运行时统计生成 Runtime Filter 下推到 Scan 节点
- 优化器：CBO + RBO + HBO（RBO 常量折叠、子查询重写、谓词下推；CBO Join 重排；HBO 基于历史推荐）

### 3.6 物化视图

- 强一致单表物化视图：系统自动维护
- 异步多表物化视图：集群内调度或外部调度工具周期性刷新

## 4. 关键设计决策与权衡

### 决策 1：存算一体 vs 存算分离

- **存算一体（本方案中小规模生产采用）**：运维简单；性能高；扩容需迁移数据
- **存算分离（大规模弹性需求采用）**：存储与计算独立扩缩；冷数据成本低；性能略低于存算一体
- **代价**：存算分离架构需 3.0+；冷热分层运维复杂

### 决策 2：数据模型选型

- **Duplicate Key**：明细查询首选
- **Unique Key**：需要行级更新场景（如维表 JOIN 后的覆盖写入）
- **Aggregate Key**：固定维度的预聚合报表
- **代价**：模型一旦选定，schema 演进受限；需事先规划

### 决策 3：导入方式

- **Stream Load（HTTP）**：实时导入；推荐用于 Kafka → Doris 通道
- **Broker Load**：从 HDFS / 对象存储批量导入
- **Routine Load**：Kafka 持续消费
- **Insert Into SELECT**：ETL 场景
- **代价**：不同导入方式吞吐与一致性保证不同

### 决策 4：MySQL 兼容性边界

- 兼容大多数 MySQL 语法；但部分 MySQL 特性（Doris 主键模型非事务）不支持
- Doris 客户端连接方式与 MySQL 一致（JDBC / 客户端 CLI）；BI 工具无缝对接

## 5. 工程化要点

- **部署**：物理机 / 虚拟机 / K8s；存算一体模式下 BE 建议 3 副本
- **数据建模**：宽表优先；避免跨分片 JOIN；ORDER BY 选择高频过滤列
- **写入**：Stream Load + Routine Load 满足实时需求；Batch 大小建议 1GB~10GB
- **查询**：利用 Runtime Filter 提升 JOIN 性能；监控慢查询日志
- **监控**：内置 web UI（端口 8030 / 8040）；Prometheus + Grafana 模板
- **运维**：
  - 副本修复：自动 + 手动
  - Compaction 策略：调整 `cumulative compaction` 间隔
  - Tablet 调度均衡
  - 备份：HDFS / 对象存储

## 6. 指标映射

| 指标 | 口径示例 | 支撑手段 |
|---|---|---|
| 写入吞吐 | Stream Load ≥ X MB/s；Routine Load 持续消费 | audit log + Compaction 状态 |
| 查询延迟 | P95 ≤ X 秒 | slow query log + Query Profile |
| 点查 QPS | 高并发 v1 主键模型 ≥ QPS | Runtime Filter + 短路径 |
| 高可用 | 副本丢失自动修复 | Tablet 副本修复机制 |
| 湖仓加速 | Hive / Iceberg / Hudi 查询延迟 | 外部表 + CBO |
| 资源利用率 | BE CPU 60-80% | Pipeline 线程数调优 |

## 7. 标书化叙述示例

> 本方案实时数据仓库采用 Apache Doris，承担业务实时报表、用户行为分析、湖仓查询加速三类业务负载。集群采用存算一体架构，FE 部署 Master + Follower + Observer 三类节点保证元数据高可用；BE 部署三副本，数据通过 Stream Load 与 Routine Load 双通道接入——日志流走 Routine Load 持续消费 Kafka，业务宽表走 Stream Load 批量写入。表引擎按业务选型——明细事实表使用 Duplicate Key 模型；维表与需要行级更新的指标表使用 Unique Key 模型；高频聚合报表使用 Aggregate Key 模型。查询引擎全向量化 + Pipeline 执行引擎 + CBO/RBO/HBO 综合优化器支撑复杂查询；Runtime Filter 在大表 JOIN 时显著降低扫描量。BI 工具通过标准 MySQL 协议接入。运行时通过 Doris Web UI + Prometheus Exporter 上送写入吞吐、查询延迟、副本状态、Compaction 时长四类指标。具体业务的写入吞吐、查询延迟、存储容量由用户在合同附件中按业务等级明确。

## 8. 风险与边界

- **不可编造项**：
  - 具体 QPS、延迟、压缩比必须实测或用户提供
  - Doris 各版本（1.x / 2.x / 3.x）的特性差异（如存算分离、行级更新等）需回到官方 Release Notes 核对
- **常见失败模式**：
  - 跨分片 JOIN → 性能差；预先打宽表
  - 不设分桶键 → 数据倾斜；选择高基数列作为分桶键
  - 主键模型误用 → 频繁 Upsert 拖垮写入
  - Compaction 积压 → 调整策略或扩容
- **架构外延**：本卡片聚焦 Doris 内核；不涵盖 Doris Manager（运维平台）、Doris Kubernetes Operator 等周边产品