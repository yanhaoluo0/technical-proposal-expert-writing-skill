# Redis Sentinel 主从哨兵高可用

> **素材来源**：https://redis.io/docs/latest/operate/oss_and_stack/management/sentinel/
> **抓取日期**：2026-08-28
> **整理方式**：精选转写（剥掉开头 JSON 元数据；保留 Capabilities / Distributed System / Deployment Requirements / Monitoring / Notification / Automatic Failover / Configuration Provider 核心机制；删除 Config Example / API Details / Client Library Setup 等细节段落）
> **适用文档类型**：方案设计报告、技术标书「缓存高可用」章节
> **可支撑的技术点**：Redis Sentinel, 主从复制, 哨兵监控, 自动故障切换, 哨兵分布式, 配置提供者, 主观下线, 客观下线
> **写作约束**：Redis 官方文档为唯一来源；具体配置值（如 quorum、down-after-milliseconds、failover-timeout）回到原文核对

## 概述

Redis Sentinel 为**非集群版 Redis** 提供高可用方案：监控主从实例、自动故障切换、通知、作为客户端服务发现的配置提供者。Sentinel 本身是分布式系统——多 Sentinel 协作完成故障检测（避免假阳性）+ 单点容错。本文精选自 Redis 官方 Sentinel 文档，是写作中描述 Redis 主从高可用方案的标准出处。

## 一、Sentinel 能力清单（Capabilities）

| 能力 | 说明 |
|---|---|
| **Monitoring（监控）** | 持续检查 master 与 replica 是否按预期工作 |
| **Notification（通知）** | 通过 API 通知系统管理员或其它程序，某 Redis 实例出问题 |
| **Automatic failover（自动故障切换）** | master 不工作时启动 failover：把 replica 提升为 master、其它 replica 重新配置指向新 master、用 Redis server 的应用被告知新连接地址 |
| **Configuration provider（配置提供者）** | 作为客户端服务发现的权威源——客户端连 Sentinel 询问当前 master 地址；failover 后 Sentinel 报告新地址 |

## 二、分布式系统视角

Sentinel 本身设计为多进程协作：

- 多 Sentinel 协作完成故障检测——降低假阳性概率
- 单个 Sentinel 不工作时仍可 failover——避免「failover 系统自身成为单点」

Sentinel + Redis + 客户端共同构成更大的分布式系统。

## 三、Sentinel 版本与运行

- 当前版本 **Sentinel 2**——Redis 2.8 起随稳定版发布，是对初版 Sentinel 的重写（更强更可预测的算法）
- Redis 2.6 随 Sentinel 1 已弃用
- 新功能先在 unstable 分支开发，稳定后 backport 到 stable
- 运行命令：
  - `redis-sentinel /path/to/sentinel.conf`
  - 或 `redis-server /path/to/sentinel.conf --sentinel`
- 必须指定配置文件——Sentinel 会保存当前状态用于重启；无配置文件或不可写则直接拒绝启动

## 四、部署前必知（Fundamental Things）

1. 健壮部署**至少需要 3 个 Sentinel 实例**
2. 3 个 Sentinel 应放在**独立失败**的物理机/虚拟机/可用区上
3. Sentinel + Redis 分布式系统**不保证**故障期间已确认写入不丢（因 Redis 异步复制）；可通过部署方式把写入丢失窗口限制在某些时刻
4. 客户端需支持 Sentinel（主流客户端库支持，但非全部）
5. **没有 HA 配置是绝对安全的**，需在开发/生产环境定期演练；凌晨 3 点 master 故障时才暴露配置错误将代价巨大
6. **Sentinel + Docker / NAT / 端口映射需谨慎**——Docker 端口重映射会破坏 Sentinel 的自动发现与副本列表

## 五、监听端口

Sentinel 默认监听 **TCP 26379**。Sentinel 间必须能互相连接，否则无法达成一致，failover 永不发生。

## 六、典型最小配置

```
sentinel monitor mymaster 127.0.0.1 6379 2
sentinel down-after-milliseconds mymaster 60000
sentinel failover-timeout mymaster 180000
```

> 注：以上为示例值；具体生产配置应回到官方文档与运维实践确定。

## 七、故障检测机制（与 Redis Cluster 的对照）

- 主观下线（SDOWN）：单个 Sentinel 判定实例下线（基于 down-after-milliseconds 等配置）
- 客观下线（ODOWN）：多数 Sentinel 同意某 master 不可达
- 配置中 `monitor` 末位的 quorum 即客观下线所需票数

> 与 Redis Cluster 的 PFAIL/FAIL 类似但术语不同：Sentinel 用 SDOWN/ODOWN。

## 八、自动故障切换流程

1. Sentinel 检测 master 客观下线
2. 选举一个 Sentinel Leader 执行 failover
3. Sentinel Leader 在 replica 中选一个晋升（按 replica-priority 与复制偏移）
4. 提升的 replica 切换为 master
5. 其它 replica 重新配置指向新 master
6. 客户端通过订阅 Sentinel 频道或查询 Sentinel 获得新 master 地址

## 九、配置提供者（Configuration Provider）

客户端不直连固定 master，而是：

- 启动时连接 Sentinel 询问 master 地址
- 订阅 `+switch-master` 频道
- 收到切换事件后查询 Sentinel 获得新 master

## 十、与 Redis Cluster 的关系

- **Sentinel** 解决**非集群版** Redis 的高可用（1 master + N replicas）
- **Redis Cluster** 解决横向扩展（多 master 分片），自带副本与故障切换
- 二选一或混用取决于扩展性需求

## 十一、写作引用建议

- 标书「缓存高可用」章节直接引用四大能力清单
- 「高可用架构」章节引用「至少 3 个 Sentinel + 独立失败域」
- 「可靠性风险」章节引用「异步复制不保证已确认写入不丢」
- 「运维约束」章节引用「Docker/NAT 注意事项 + 客户端支持要求」
- 与 `Redis-Cluster-分片与故障转移.md` 配套引用，对照两种高可用方案
