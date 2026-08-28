# EMQX Broker 集群架构

> **素材来源**：https://docs.emqx.com/en/ + https://docs.emqx.com/en/emqx/latest/deploy/cluster/introduction.html
> **抓取日期**：2026-08-28
> **整理方式**：技术深度型（八段卡片）。原始 B2 为 EMQX 产品介绍页（内容多为产品链接）；本卡片围绕 EMQX 集群架构、节点发现、消息路由、数据集成（Data Bridge）、钩子扩展展开。
> **适用文档类型**：方案设计报告、技术标书「EMQX 部署」「MQTT Broker 集群」「物联网消息中间件」章节
> **可支撑的技术点**：EMQX, EMQX Cluster, ekka, Erlang, Mnesia, MQTT, Multi-protocol Gateway, Data Integration, Data Bridge, Rule Engine, Hook, REST API, Dashboard, Auth, ACL, Session, Retain, Shared Subscription
> **写作约束**：术语沿用 EMQX 官方文档；不可编造具体性能基准。

## 1. 适用场景与触发词

需要「百万级设备连接 + MQTT Broker 集群 + 数据集成到 Kafka / 数据库 + 内置 SQL 规则引擎」时命中本卡片：

- 业务场景：IoT 平台、车联网、智慧能源、工业互联网、智能家居
- 标书或设计报告关键词：「EMQX」「MQTT Broker」「物联网平台」「集群」「多协议网关」「数据集成」「规则引擎」

## 2. 技术内涵与边界

**做什么**：

- 高性能开源 MQTT Broker；Erlang/OTP 编写；单实例支持百万级连接
- 集群化水平扩展（基于 Erlang 集群协议 ekka）
- 多协议网关：MQTT、MQTT over WebSocket、LwM2M、CoAP、Stomp
- 内置 SQL 规则引擎（Rule Engine）+ Data Bridge（数据桥接到 Kafka / Pulsar / 数据库）
- 提供 Dashboard、REST API、Prometheus 集成

**不做什么**：

- 不替代消息中间件（如 Kafka）——EMQX 是 IoT 协议 Broker；数据汇集后通常桥接至 Kafka
- 不擅长 OLAP 分析——数据落到 ClickHouse / Doris 等分析引擎
- 不擅长实时流计算——桥接给 Flink / Spark Streaming
- EMQX Edge（Neuron）面向边缘侧，不是中心侧 Broker

## 3. 典型架构与关键机制

### 3.1 产品矩阵

- **EMQX Cloud**：全托管云服务
- **EMQX Enterprise**：自管云原生 MQTT 平台 + SQL 规则引擎 + 多协议网关
- **EMQX Neuron**：工业边缘数据中枢（边缘侧）
- **EMQX Edge**：轻量级边缘 Broker
- **Device Agent**：MQTT 驱动的 AI 助手（生成设备 SDK 等）

### 3.2 集群架构

- 基于 Erlang/OTP 内置的集群能力（ekka）
- 节点间通过 Erlang 分布协议通信（TCP）
- 自动节点发现（基于 `cluster.discovery_strategy`：static / mcast / dns / etcd / k8s）
- Mnesia 分布式数据库保存集群状态、会话、Retain 消息、路由表
- 集群模式：Core + Replicant（读副本）

### 3.3 消息路由

- 主题路由表在所有节点同步
- 客户端连接到任意节点；消息发布时由本地节点判断目标节点并转发
- 共享订阅（MQTT 5 `$share/`）在集群内按 Group 分发

### 3.4 数据集成（Data Bridge）

- 内置 SQL 规则引擎（Rule Engine）实时过滤 / 转换消息
- Data Bridge 把处理后消息写入外部系统：Kafka、Pulsar、RabbitMQ、PostgreSQL、MySQL、Redis、MongoDB、ClickHouse、InfluxDB、TDengine、Cassandra、Doris、TimescaleDB、S3、Cassandra、HTTP / HTTPS Webhook
- 支持 Exactly-Once（Kafka 0.11+ 事务）/ At-Least-Once

### 3.5 多协议网关

- MQTT 5 / MQTT 3.1.1
- MQTT over WebSocket（WS / WSS）
- LwM2M（轻量级 M2M）
- CoAP（受限应用协议）
- Stomp
- TCP 私有协议（私有网关）

### 3.6 认证与授权

- 认证：Username / Password、Client Certificate、HTTP Backend、PSK、Enhanced Authentication（MQTT 5）
- 授权（ACL）：内置 / 文件 / HTTP Backend / MySQL / PostgreSQL / Redis
- ClientId / Username / Topic 多维度授权

### 3.7 钩子（Hook）扩展

- 客户端连接 / 断开
- 消息发布 / 投递
- 订阅 / 取消订阅
- 用于审计、风控、二次处理

### 3.8 Dashboard / REST API / Metrics

- Web Dashboard：连接数、消息速率、客户端列表、主题树
- REST API：管理客户端、订阅、规则、桥接、用户、ACL
- Prometheus Exporter：`/api/v5/metrics`
- 日志：JSON 结构化日志

## 4. 关键设计决策与权衡

### 决策 1：自管 EMQX vs EMQX Cloud

- **自管 EMQX（本方案私有化部署采用）**：可控性强；合规要求高的政企首选
- **EMQX Cloud（多租户 SaaS 场景采用）**：免运维；订阅模式成本可控
- **代价**：自管需 K8s Operator + DBA + SRE 投入

### 决策 2：单节点 vs 集群

- **单节点（设备数 ≤ 10 万连接）**：开发测试、小规模生产
- **集群（百万级连接 / 跨地域 HA）**：ekka + 节点自动发现 + 数据副本
- **代价**：集群引入节点间同步开销；规模与节点数非线性（建议 3~7 节点）

### 决策 3：数据集成方式

- **Rule Engine + Data Bridge（本方案 Kafka / 数据仓库桥接采用）**：零代码；高吞吐；Exactly-Once
- **客户端订阅 + 外部订阅者**：业务方自取；灵活但重复实现订阅
- **WebHook 桥接**：简单场景；吞吐低
- **代价**：Rule Engine 调试与运维需 Dashboard 支持；规则过复杂时维护成本上升

### 决策 4：持久化策略

- **Mnesia**：内置；集群共享会话与 Retain 消息
- **外部数据库**：会话外置（PostgreSQL / MySQL）
- **代价**：Mnesia 写入高频，外部数据库压力大；混合模式常见

## 5. 工程化要点

- **部署**：
  - K8s 部署：EMQX Operator（官方）
  - 节点数：3 起步；5/7 节点更稳；建议奇数
  - 反亲和性：节点尽量分散到不同物理机 / 可用区
- **HA**：
  - 节点间 Erlang 集群自动 Failover
  - 客户端使用多 Broker 地址（推荐 DNS 域名）
- **配置**：
  - `cluster.discovery_strategy`：k8s 场景用 k8s；静态环境用 static
  - `zone`：机房 / 可用区感知路由
  - `listeners`：TCP / SSL / WS / WSS
- **监控**：
  - Dashboard：连接数、订阅数、消息速率
  - Prometheus：Exporter → Grafana
  - 日志：结构化 JSON；ELK / Loki
- **运维**：
  - 滚动升级：通过 K8s 滚动策略
  - 配置热加载：Dashboard / API
  - 客户端强制下线：`/api/v5/clients/{clientid}`

## 6. 指标映射

| 指标 | 口径示例 | 支撑手段 |
|---|---|---|
| 并发连接数 | 单节点 ≥ N 万连接；集群 ≥ M 百万 | Dashboard + Metrics |
| 消息吞吐 | 单节点 ≥ X 万 msg/s | QoS 0/1 + Rule Engine |
| 集群同步延迟 | ≤ N 秒 | ekka 监控 + Mnesia 状态 |
| 规则命中率 | 100% / 失败率 | Rule Engine 监控 |
| 数据桥接延迟 | ≤ Y 秒 | Kafka / 数据库侧监控 |
| 客户端断线率 | ≤ X% | Dashboard 客户端状态 |

## 7. 标书化叙述示例

> 本方案 IoT 平台中心 Broker 采用 EMQX 集群。集群采用 5 节点（奇数）部署，跨两个可用区；节点发现通过 Kubernetes API 适配器；客户端通过 DNS 域名连接（自动 Failover）。MQTT 5 与 MQTT 3.1.1 双协议支持；关键设备启用 TLS 加密（端口 8883）。数据集成通过内置 SQL 规则引擎过滤 + Data Bridge 桥接到 Kafka / ClickHouse / MySQL；规则按业务域拆分到不同 Rule Engine 路径，关键业务规则启用 Exactly-Once（Kafka 事务）。认证采用 Username/Password + Client Certificate 双模式；ACL 按 ClientId + Topic 粒度按最小权限原则配置。运行时通过 EMQX Dashboard + Prometheus Exporter 上送连接数、消息吞吐、规则命中率、数据桥接延迟四类指标；K8s Operator 负责集群滚动升级与节点拉起。具体业务的设备规模、消息频率、合规要求由用户在合同附件中按业务等级明确。

## 8. 风险与边界

- **不可编造项**：
  - 单集群连接数、消息吞吐数字必须实测或 EMQX 官方 benchmark 提供
  - EMQX 各版本（5.x）的具体特性差异需回到官方 Release Notes 核对
- **常见失败模式**：
  - 节点时间不同步 → Erlang 集群通信异常；启用 NTP
  - Mnesia 表过大 → 启动慢；拆分或外置
  - 数据桥接积压 → 提高 Kafka 消费者并发 / 扩容
  - 规则引擎 SQL 性能差 → 简化规则 + 增加索引
  - 客户端重连风暴 → 启用指数退避 + 最大重试次数
- **架构外延**：本卡片聚焦 EMQX 中心 Broker；不涵盖 EMQX Edge（边缘 Broker）、Neuron（边缘数据中枢）、Device Agent（AI 助手）