# OpenYurt 边缘计算平台

> **素材来源**：https://openyurt.io/
> **抓取日期**：2026-08-28
> **整理方式**：技术深度型（八段卡片）。原始 B6 为 OpenYurt 官方主页（含图片链接）。本卡片围绕边缘自治、跨地域网络（YurtHub / Raven / pool-coordinator）、多地域资源管理（NodePool / UnitedDeployment / YurtAppDaemon / YurtIngress）、云原生设备管理四大特性展开。
> **适用文档类型**：方案设计报告、技术标书「边缘自治」「OpenYurt」「云边协同」「边缘容器编排」章节
> **可支撑的技术点**：OpenYurt, YurtHub, Raven, pool-coordinator, NodePool, UnitedDeployment, YurtAppDaemon, YurtIngress, OTA, Auto Upgrade, 边缘自治, 跨地域网络
> **写作约束**：术语沿用 OpenYurt 官方文档；不可编造具体性能基准。

## 1. 适用场景与触发词

需要「边缘自治 + 跨地域云边网络 + 多 NodePool 资源管理 + 云原生设备模型」时命中本卡片：

- 业务场景：IoT、分布式云、物流、交通、制造、CDN、零售边缘
- 标书或设计报告关键词：「OpenYurt」「边缘自治」「NodePool」「YurtHub」「Raven」「跨地域网络」「UnitedDeployment」「OTA 升级」「边缘 Ingress」

## 2. 技术内涵与边界

**做什么**：

- CNCF Sandbox 项目；面向边缘计算与 IoT 场景
- 在 Kubernetes 上做非侵入式增强（Non-intrusive enhancement）
- 支持跨架构（ARM / X86）边缘工作负载管理
- 通过 NodePool 抽象管理边缘资源池
- 支持边缘自治、跨地域网络、多地域应用管理

**不做什么**：

- 不替代 Kubernetes——是 K8s 之上的扩展
- 不擅长超大量节点（OpenYurt 在数万个节点规模验证）
- 不替代消息中间件——设备消息通过 EMQX / Kafka 等桥接

## 3. 典型架构与关键机制

### 3.1 边缘自治能力

> 官方原文：「In edge computing scenario, the network connections between edge and cloud are diversified (e.g. 5G, WIFI, etc.). Network jitter or node offline will lead to node heartbeat cannot be reported to the cloud in real time, which triggers the eviction and reconstruction of edge services.」

**问题**：边云网络抖动 / 节点离线 → 心跳上报失败 → 触发 Pod 驱逐重建 → 业务中断。

**OpenYurt 解决**：
- 云端：增强 Pod 驱逐控制能力
- 边缘：本地缓存 + 心跳代理上报机制
- 边云网络恢复：边缘服务状态与云端同步，数据一致性保证

### 3.2 跨地域网络通信

> 官方原文：「In the cloud edge scenario, the cloud to edge / edge to edge are in different physical network planes. Generally only the cloud side exposes public network service addresses, and the native CNI container network can only address data-plane communication in a single region (layer 2 or layer 3 connectivity scenario).」

**问题**：云 → 边、边 → 边跨地域网络；原生 CNI 只能单地域通信。

**OpenYurt 组件**：
- **Raven**：跨地域数据面通信组件；与原生 CNI 完全兼容
- **pool-coordinator**：云边流量复用组件；减少云边控制面通信数据量

### 3.3 多地域资源与应用管理（Unitization）

> 官方原文：「For edge scenarios, OpenYurt pioneers the concept of Unitization, which can close the loop of resources, applications, and service traffic in the unit.」

**NodePool 抽象**：
- 资源层：抽象节点池；边缘站点资源按地理位置分类划分
- 应用层：UnitedDeployment（单元化部署）、YurtAppDaemon（单元化 DaemonSet）、YurtIngress（边缘 Ingress）
- 流量层：流量在 NodePool 内闭环访问
- 升级层：OTA / Auto Upgrade；解决原生滚动升级在 NodeNotReady 时阻塞的问题

### 3.4 云原生设备管理

> 官方原文：「OpenYurt abstracts and defines a cloud native model of leaf devices in edge computing scenario from the following perspectives: basic properties, main capabilities and what information can be transmitted.」

- 从基础属性、主要能力、可传输信息三方面抽象叶子设备模型
- 兼容主流 IoT 设备管理方案（通过 Plugin）
- 通过云原生声明式 API 提供设备数据采集、处理、控制能力

### 3.5 核心组件

| 组件 | 职责 |
|---|---|
| YurtHub | 边缘节点上的代理；缓存云端 API；离线时本地服务 |
| YurtAppManager | NodePool / UnitedDeployment / YurtAppDaemon / YurtIngress CRD 管理 |
| Raven | 跨地域数据面 |
| pool-coordinator | 云边流量复用 |
| NodePools | 节点池抽象 |
| OTA | 边缘节点操作系统与应用升级 |

## 4. 关键设计决策与权衡

### 决策 1：OpenYurt vs KubeEdge vs K3s

- **OpenYurt（本方案边缘自治 + 多地域场景采用）**：NodePool / Unitization 抽象；CNCF Sandbox
- **KubeEdge**：MQTT 设备孪生；边云同步；离线自治
- **K3s**：轻量级 K8s；ARM 友好
- **代价**：OpenYurt 学习曲线陡；CRD 较多；与上游 K8s 版本对齐窗口

### 决策 2：YurtHub 缓存策略

- **全量缓存**：本地完整 K8s API 数据；适合资源量小
- **按需缓存**：只缓存相关资源；适合大量边缘节点
- **代价**：缓存策略影响内存与一致性

### 决策 3：跨地域网络方案

- **Raven（本方案采用）**：跨地域 L3 通信；与原生 CNI 兼容
- **VPN（IPSec / Wireguard）**：通用但配置复杂
- **云厂商专线**：成本高；适合大型企业

### 决策 4：升级策略

- **OTA 升级（操作系统 / 边缘节点级）：**
- **Auto Upgrade（应用级）**：自动化滚动升级
- **手动升级**：完全可控；适合关键业务

## 5. 工程化要点

- **部署**：
  - 云端 K8s 集群（≥ 1.24）
  - YurtHub 部署到边缘节点
  - CRD 注册到 K8s
- **网络**：
  - 云边：WebSocket / HTTPS 长连接
  - 跨地域：Raven
  - 节点间：原生 CNI（与 Raven 兼容）
- **监控**：
  - YurtHub Metrics
  - Raven Metrics
  - NodePool 状态
- **运维**：
  - 节点注册（NodePool Label）
  - 滚动升级（UnitedDeployment / YurtAppDaemon）
  - OTA 升级
  - 离线恢复演练

## 6. 指标映射

| 指标 | 口径示例 | 支撑手段 |
|---|---|---|
| NodePool 数 | 单集群 ≤ N 个 | 资源池规划 |
| 边缘节点数 | 单 NodePool ≤ X 节点 | NodePool 拆分 |
| 边云连接健康 | 在线率 ≥ Y% | YurtHub 心跳 |
| 跨地域延迟 | 跨地域 Pod 通信 ≤ Z ms | Raven 监控 |
| 应用分发时延 | 创建 Pod → 边缘运行 ≤ T 秒 | 镜像缓存 + P2P |
| 升级成功率 | OTA ≥ V% | OTA 平台监控 |

## 7. 标书化叙述示例

> 本方案边缘计算平台采用 OpenYurt。云端 Kubernetes 集群（≥ 1.24）部署 YurtAppManager（含 NodePool / UnitedDeployment / YurtAppDaemon / YurtIngress CRD）；边缘节点通过 YurtHub 代理接入；按地理位置划分 NodePool（如「华东-站点 A」「华北-站点 B」）。边缘自治能力由 YurtHub 本地缓存 + 心跳代理上报实现——边云网络抖动或断连时，边缘 Pod 不被驱逐；网络恢复后增量同步。跨地域网络由 Raven 实现，云边、边边通信基于 L3，与原生 CNI 完全兼容。设备消息通过 EMQX 桥接后由 OpenYurt 设备模型抽象处理。应用部署采用 UnitedDeployment 按 NodePool 单元化分发；升级采用 OTA + Auto Upgrade 策略应对节点 NotReady 场景。监控通过 YurtHub / Raven Metrics Exporter + Prometheus 上送 NodePool 数、边云连接健康率、跨地域延迟、应用分发时延四类指标。具体业务的 NodePool 数、边缘节点规模、网络条件由用户在合同附件中按业务等级明确。

## 8. 风险与边界

- **不可编造项**：
  - 具体 NodePool 数、边缘节点规模、跨地域延迟必须实测或用户提供
  - OpenYurt 各版本（1.x）的组件差异需回到官方 Release Notes 核对
- **常见失败模式**：
  - YurtHub 缓存膨胀 → 调整缓存策略；只缓存相关资源
  - 跨地域延迟高 → 启用 pool-coordinator 减少控制面流量
  - NodePool 拆分过细 → 管理复杂度上升；按业务 + 地理位置合并
  - OTA 升级失败 → 灰度升级 + 自动回滚
- **架构外延**：本卡片聚焦 OpenYurt 主干；不涵盖 OpenYurt-IoT、OpenYurt Operator、跨 K8s 集群联邦等周边