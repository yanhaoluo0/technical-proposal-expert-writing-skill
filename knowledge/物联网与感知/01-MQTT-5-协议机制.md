# MQTT 5 协议机制

> **素材来源**：https://www.hivemq.com/mqtt/mqtt-5/ + https://kafka.apache.org/43/streams/core-concepts/（用于 KStream 对照概念）
> **抓取日期**：2026-08-28
> **整理方式**：技术深度型（八段卡片）。原始 B1 为 HiveMQ「MQTT 5 Essentials」专题页，主体是功能特性列表；本卡片围绕 MQTT 5 协议核心机制（发布订阅模型、QoS、主题、遗嘱、共享订阅、Reason Code、User Properties、Session Expiry、Message Expiry、Topic Alias、Request-Response）展开。
> **适用文档类型**：方案设计报告、技术标书「物联网通信」「MQTT」「设备接入」「消息协议」章节
> **可支撑的技术点**：MQTT 5, MQTT 3.1.1, Publish/Subscribe, QoS 0/1/2, Last Will and Testament, Shared Subscription, Topic, User Properties, Reason Code, Negative Acknowledgement, Session Expiry, Message Expiry, Topic Alias, Request-Response, Flow Control
> **写作约束**：术语沿用 HiveMQ MQTT 5 文档与 OASIS MQTT 5 规范；不可编造具体带宽 / 延迟数字。

## 1. 适用场景与触发词

需要「低带宽、不稳定网络下 IoT 设备与云端双向通信 + 多种 QoS + 主题路由」时命中本卡片：

- 业务场景：设备接入（智能制造、智慧城市、车联网、能源监控）、实时指令下发、状态上报、设备影子同步
- 标书或设计报告关键词：「MQTT」「MQTT 5」「MQTT 3.1.1」「发布订阅」「QoS」「Last Will」「遗嘱」「共享订阅」「主题别名」「消息过期」

## 2. 技术内涵与边界

**做什么**：

- 轻量级发布订阅（Pub/Sub）消息协议；TCP 长连接；适合低带宽、不稳定网络
- 三种 QoS 等级：At most once（0）、At least once（1）、Exactly once（2）
- 基于主题（Topic）的路由：`/` 分层 + `+`（单层通配）+ `#`（多层通配）
- 遗嘱消息（Last Will and Testament，LWT）：设备非正常断开时由 Broker 代发
- 持久会话（Persistent Session）：断线期间消息可被 Broker 保留

**不做什么**：

- 不替代消息中间件——MQTT 5 是协议，需配合 Broker（EMQX / HiveMQ / Mosquitto）
- 不擅长高吞吐消息流（Kafka、Pulsar 在百万 TPS 场景更合适）
- 不擅长请求-响应的同步调用——需要 Request-Response 模式（MQTT 5 新增能力）
- 不擅长点对点（p2p）通信——本质上是一对多 / 多对一

## 3. 典型架构与关键机制

### 3.1 协议基础

- TCP 长连接（默认 1883；TLS 加密为 8883；WebSocket 为 8083/8084）
- 三种角色：Publisher（发布者）、Subscriber（订阅者）、Broker（代理）
- Broker 负责：连接管理、主题路由、消息分发、QoS 保证、Session 持久化

### 3.2 QoS 三级

| QoS | 语义 | 流程 | 适用 |
|---|---|---|---|
| 0 | At most once | PUBLISH → 丢弃 | 不重要状态（环境数据采样） |
| 1 | At least once | PUBLISH → PUBACK；重传直到收到 | 状态上报（允许偶尔重复） |
| 2 | Exactly once | PUBLISH → PUBREC → PUBREL → PUBCOMP 四次握手 | 严格计费、扣款 |

### 3.3 MQTT 5 vs MQTT 3.1.1 主要增强

HiveMQ 官方专题总结 MQTT 5 新特性：

- **User Properties**：消息可携带自定义键值对元数据
- **Reason Codes + Negative Acknowledgements**：所有响应（PUBACK / PUBREC / PUBREL / PUBCOMP / SUBACK / UNSUBACK / DISCONNECT / AUTH / CONNACK）携带 Reason Code；失败响应附带具体原因
- **Payload Format Description + Content Type**：声明 payload 编码格式（如 UTF-8、JSON Schema）
- **Server Disconnect**：Broker 可发 DISCONNECT 强制客户端下线（带 Reason Code）
- **Session Expiry Interval**：会话在断开后保留多久（含断线期间投递）
- **Message Expiry Interval**：消息有有效期，过期即丢弃
- **Shared Subscriptions**：多客户端分组共享订阅（`$share/{ShareName}/{filter}`）实现负载均衡
- **Subscription Identifier**：每条订阅携带整数 ID，匹配消息携带该 ID，便于客户端识别订阅源
- **Topic Alias**：客户端与服务端约定短别名替换长主题，节省带宽
- **Request / Response Pattern**：Response Topic + Correlation Data 实现 RPC 风格调用
- **Flow Control**：CONNECT / CONNACK 中约定 Receive Maximum，控制并发未确认消息数
- **Enhanced Authentication**：AUTH 数据包支持自定义认证流程（如 SASL、OAuth）
- **Server Keep-Alive**：服务端可单独发心跳（无需客户端）
- **Maximum Packet Size**：限制单包大小（避免大消息阻塞）
- **Assigned Client Identifiers**：服务端可为空 ClientId 分配唯一 ID

### 3.4 主题（Topic）

- 分层主题：`factory/area1/line2/machine3/temperature`
- 单层通配符 `+`：`factory/+/+/+/temperature` 匹配三段任意
- 多层通配符 `#`：`factory/area1/#` 匹配 `area1` 下所有子主题
- 系统主题：`$SYS/`（Broker 状态与监控）
- 共享订阅：`$share/{ShareName}/{filter}`（MQTT 5）

### 3.5 消息生命周期

- Persistent Session（持久会话）：断开时保留订阅 + 未投递 QoS > 0 消息
- 非持久会话：断开即清理
- QoS 1/2 消息在 Session Expiry 期间可投递
- Message Expiry 超过则丢弃

## 4. 关键设计决策与权衡

### 决策 1：MQTT vs CoAP vs AMQP

- **MQTT（本方案 IoT 设备接入采用）**：TCP 之上的发布订阅；成熟生态；客户端库全平台
- **CoAP**：UDP 之上；受限设备首选（电池供电、低带宽）
- **AMQP**：金融级消息；更复杂；适合企业内部系统集成
- **代价**：MQTT 不适合纯 UDP 受限设备；CoAP 不适合大量长消息

### 决策 2：QoS 等级选择

- **QoS 0**：高吞吐、不重要数据（环境采样）
- **QoS 1**：通用上报（设备状态、指标）——**最常用**
- **QoS 2**：严格语义（计费、扣款、控制指令）
- **代价**：QoS 2 四次握手开销大；为提升吞吐优先选 QoS 1 + 业务去重

### 决策 3：Broker 选型

- **EMQX**：开源 MQTT Broker；高并发（百万级连接）；集群化
- **HiveMQ**：商业 Broker；企业级特性丰富
- **Mosquitto**：轻量级；低资源；适合嵌入式
- **代价**：EMQX 资源占用高于 Mosquitto；HiveMQ 商业许可

### 决策 4：会话模式

- **Clean Session（默认 MQTT 3.1.1）**：断开即清理；简单
- **Persistent Session（MQTT 3.1.1 + 优化于 MQTT 5）**：断线期间消息暂存
- **代价**：Persistent Session 增加 Broker 存储压力；Session Expiry 必须配置合理

## 5. 工程化要点

- **Broker 部署**：单实例 / 集群（EMQX 支持 Erlang/OTP 内置集群协议 ekka）
- **TLS 加密**：必须启用（数据安全 / 合规）
- **认证**：账号密码、Client Certificate、OAuth 2.0、Enhanced Authentication
- **ACL**：按 ClientId / Topic 粒度授权
- **监控**：
  - Broker 内置 Metrics（EMQX Dashboard / REST API）
  - 连接数、消息速率、主题数、订阅数
  - Prometheus Exporter
- **运维**：
  - Session 清理策略
  - Retain 消息管理
  - Will 消息保留期
- **客户端库**：
  - Java：Eclipse Paho、HiveMQ MQTT Client
  - Python：paho-mqtt
  - C：Eclipse Paho C
  - Embedded：C++（适用于资源受限设备）

## 6. 指标映射

| 指标 | 口径示例 | 支撑手段 |
|---|---|---|
| 设备连接数 | 单 Broker ≥ N 万连接 | 集群 + 水平扩展 |
| 消息吞吐 | 单 Broker ≥ X 万 msg/s | QoS 0/1 优化 |
| 端到端延迟 | 发布 → 订阅 ≤ X ms | Broker 监控 + QoS 等级选择 |
| TLS 握手开销 | 启用 TLS 后吞吐下降 | TLS Session Resumption |
| 会话保持 | Persistent Session 消息暂存 | Session Expiry Interval |
| 共享订阅负载均衡 | 多 Subscriber 均衡接收 | `$share/` 前缀 |

## 7. 标书化叙述示例

> 本方案设备接入层采用 MQTT 5 协议。设备端使用 Eclipse Paho 客户端库，通过 TLS 加密通道（端口 8883）连接云端 Broker（EMQX 集群）。QoS 等级按业务选择——状态上报类消息使用 QoS 1（保证至少一次投递，由业务层去重）；计费与扣款类指令使用 QoS 2（保证恰好一次）。主题按业务域分层命名（如 `site/{siteId}/device/{deviceId}/telemetry`），订阅端使用通配符订阅全量遥测。关键设备启用 Last Will and Testament（LWT），非正常断开时由 Broker 代发离线事件到 `device/{deviceId}/status` 主题，运维侧订阅该主题更新设备状态。MQTT 5 新特性按需使用——User Properties 携带消息路由元数据；Topic Alias 节省长主题带宽；Message Expiry 防止过期消息堆积；Shared Subscriptions 在高吞吐场景下多消费端负载均衡。Broker 集群通过 Prometheus Exporter 上送连接数、消息速率、QoS 命中率、Session 数四类指标；ACL 按 ClientId + Topic 粒度配置。具体业务的设备规模、消息频率、延迟要求由用户在合同附件中按业务等级明确。

## 8. 风险与边界

- **不可编造项**：
  - 具体连接数、消息吞吐、延迟数字必须实测或用户提供
  - 不同 Broker 版本（EMQX 5.x / HiveMQ 4.x）的功能支持差异需回到官方文档核对
- **常见失败模式**：
  - QoS 2 滥用 → Broker 资源紧张；按需启用
  - Session 不清理 → Broker 内存增长；配置 Session Expiry
  - 通配符订阅过广 → 客户端过载；拆分订阅
  - Will 消息未配置 → 设备离线检测延迟
  - ACL 配置过宽 → 安全风险；按最小权限原则
- **架构外延**：本卡片聚焦 MQTT 协议；不涵盖 EMQX 集群架构（独立卡片）、HiveMQ 商业功能、AWS IoT Core / Azure IoT Hub 平台层