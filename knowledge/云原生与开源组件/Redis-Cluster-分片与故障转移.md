# Redis Cluster 分片、故障检测与复制迁移

> **素材来源**：https://redis.io/docs/latest/operate/oss_and_stack/reference/cluster-spec/
> **抓取日期**：2026-08-28
> **整理方式**：精选转写（剥掉开头 JSON 元数据；保留 Main Properties / Client & Server Roles / Key Distribution / Hash Tags / Cluster Topology / Heartbeat / Failure Detection / Replica Migration 核心机制；删除 Implementation Details / Protocol Details / 客户端库说明等细节段落）
> **适用文档类型**：方案设计报告、技术标书「缓存」「分布式数据」章节
> **可支撑的技术点**：Redis Cluster, 哈希槽, 16384 槽, CRC16, 哈希标签, gossip 协议, 故障检测, PFAIL, FAIL, 副本迁移, 写安全, 可用性
> **写作约束**：Redis 官方规范为唯一来源；配置项具体值（如 `cluster-port`、`NODE_TIMEOUT`、`FAIL_REPORT_VALIDITY_MULT`）回到官方文档核对

## 概述

Redis Cluster 是 Redis 的分布式实现，核心机制：**16384 个哈希槽分片**、**节点 TCP bus + gossip 协议**、**PFAIL/FAIL 两级故障检测**、**副本迁移（replica migration）**提升系统级可用性。本文精选自 Redis 官方 Cluster Specification，是写作中描述 Redis Cluster 高可用机制的权威出处。

## 一、设计目标与权衡

按重要性排序的三大目标：

1. **高性能与线性扩展到 1000 节点**
   - 无代理
   - 异步复制
   - 不在 value 上做合并操作
2. **可接受的写安全**（best-effort）：系统尽力保留连接至大多数 master 的客户端写入；少数派分区时丢失窗口更大
3. **可用性**：能在大多 master 可达、且每个不可达 master 至少有一个可达副本时存活；通过**副本迁移**让失去副本的 master 从多副本 master 处获得副本

> What is described in this document is implemented in Redis 3.0 or greater.

## 二、客户端/服务端角色

- 节点持有数据并维护集群状态（key → node 映射）
- 节点能力：**自动发现其它节点、检测不工作节点、必要时把 replica 提升为 master**
- 所有节点通过 **TCP bus + 二进制协议**（Redis Cluster Bus）相连
- 节点用 gossip 协议传播集群信息（发现新节点、ping 检测、集群消息）；cluster bus 也传播 Pub/Sub 与手动 failover 协调

## 三、Key Distribution（关键分布模型）

### 3.1 哈希槽切分

- 集群 key 空间切为 **16384 个 slot**——理论上限 16384 master（实际建议上限 ~1000）
- 每个 master 节点负责 16384 slot 的子集
- **集群稳定时**：一个 slot 由一个节点服务（但节点可有副本——用于故障替换与扩展读）
- 基础映射算法：
  ```
  HASH_SLOT = CRC16(key) mod 16384
  ```
- CRC16 规范：XMODEM（ZMODEM / CRC-16/ACORN）；宽 16 bit；Poly 1021；Output for "123456789" = 31C3
- 取高 14 位有效（16384 = 2^14）
- 测试中 CRC16 在不同 key 上分布均匀

### 3.2 哈希标签（Hash Tags）

- 用途：让多个 key 强制分配到**同一 slot**（用于多 key 操作）
- 算法：若 key 含 `{...}` 模式，**只对 `{` 与第一个 `}` 之间的子串**做 hash
  - 触发条件：含 `{`、其右侧有 `}`、中间有至少一个字符
  - 例：`{user1000}.following` 与 `{user1000}.followers` 同 slot（只 hash `user1000`）
  - 例：`foo{}{bar}` 整 key 做 hash（首 `{` 后紧跟 `}` 无字符）
  - 例：`foo{{bar}}zap` hash `{bar`
  - 例：`foo{bar}{zap}` hash `bar`（算法在首个匹配处停）
  - `{}` 开头保证整体 hash（二进制 key 名场景）

### 3.3 Glob 模式优化（Redis 8.0+）

`KEYS`/`SCAN`/`SORT` 在模式能识别到 hashtag 时只搜一个 slot，提升性能。优化生效条件：模式含 hashtag、hashtag 前无通配符/转义、hashtag 内无通配符/转义。

### 3.4 已实现子集

- 所有非分布式 Redis 单 key 命令
- 多 key 命令（如 set unions/intersections）仅在所有 key 同 slot 时支持
- **不支持多数据库**：只支持 db `0`，`SELECT` 命令不允许
- 手动 resharding 期间，多 key 命令可能临时不可用，单 key 命令始终可用

## 四、写安全

Redis Cluster 写安全 best-effort：连接至大多数 master 的客户端写入会被尽力保留。但有以下丢失窗口：

- 异步复制 → 写入 master 后未复制到 replica 前 master 宕机
- 网络分区下少数派 master 上的写入在分区恢复时被覆盖

## 五、可用性

- 在大多 master 可达 + 每个不可达 master 至少有一个可达副本时存活
- **副本迁移**：让失去副本覆盖的 master 从多副本 master 那里获得副本（详见第十节）

## 六、性能与合并操作（要点）

- 性能：无代理 + 异步复制 + 不合并 value
- 不做合并操作原因：合并类似 set union/intersection 涉及多 key；存储在多节点时要么低效要么难保持一致

## 七、Cluster Node 属性

- **节点名**：节点首次启动时由 160 bit 随机数生成的 16 进制字符串（通常用 /dev/urandom）
- 节点 ID 永久不变，除非配置文件被删或主动 `CLUSTER RESET` hard reset
- 节点 ID 全局唯一标识节点；可改 IP/端口而保留 ID
- 每个节点维护对其它节点的视图（ID、IP、port、flags、master、最后 ping/pong 时间、configuration epoch、link state、hash slot set）
- `CLUSTER NODES` 命令查看本地视图

## 八、Cluster Bus

- 节点除数据端口外，额外 TCP 端口接收其它节点连接
- 默认 port = data port + 10000（即 6379 → 16379）
- 可通过 `cluster-port` 配置显式指定
- 节点间通信只走 cluster bus + cluster bus 二进制协议（不公开）

## 九、Cluster Topology

- **全网状（full mesh）**：每个节点与其它所有节点有 TCP 连接
- N 节点集群：每个节点有 N-1 出向、N-1 入向连接；连接常驻、不按需创建
- 等不到 pong 时会重连一次再判定不可达
- gossip 协议 + 配置更新机制避免消息量指数增长

## 十、节点握手

- 节点启动时用 `CLUSTER MEET <ip> <port>` 把目标节点加入集群
- 通过 gossip 完成全网状发现
- 信任模型简单——管理员用 MEET 引入的就是可信节点

## 十一、故障检测（Failure Detection）

### 11.1 Heartbeat 和 Gossip

- 节点持续交换 ping/pong 包（结构相同，区别仅 message type 字段）
- 通常节点发 ping，接收方回 pong；也可主动发 pong 传播配置（如尽快广播新配置）
- **每个节点每秒向几个随机节点发 ping**，使每个节点的 ping/接收 pong 总数与集群节点数无关（常数级）
- 每节点保证：若某节点超过半个 `NODE_TIMEOUT` 没收到 ping/pong，会尝试重连
- 例：100 节点 + NODE_TIMEOUT=60s，每节点每 30s 向 99 节点发 ping = 3.3/s；100 节点 = 330 ping/s（每个节点接收约 3.3/s，可接受）

### 11.2 Heartbeat 包内容

公共头字段：

- Node ID（160 bit 伪随机）
- `currentEpoch` 与 `configEpoch`
- node flags（replica / master 等）
- 服务 slot 的 bitmap
- sender TCP base port
- cluster port
- 发送方视角的集群状态（down / ok）
- 若是 replica：master 的 node ID

Gossip section：含发送方对其它少量随机节点的视图（ID、IP、port、flags），用于发现与故障检测。

### 11.3 Failure Detection（PFAIL / FAIL）

**两个故障标志**：

- `PFAIL`（Possible Failure）：不可确认的故障类型
- `FAIL`：已被集群内多数 master 在固定时间内确认

**PFLAG 触发**：某节点对另一节点超过 `NODE_TIMEOUT` 仍**有 active ping 未收到回复**。master/replica 均可标 PFAIL。

**PFAIL → FAIL 升级条件**（同时满足）：

1. 节点 A 把节点 B 标 PFAIL
2. A 通过 gossip 段收集到集群**大多数 master** 对 B 状态的看法
3. 大多数 master 在 `NODE_TIMEOUT * FAIL_REPORT_VALIDITY_MULT` 时间窗内（当前实现 = 2 × NODE_TIMEOUT）报告 PFAIL/FAIL

满足后：A 把 B 标 FAIL，并向所有可达节点发 FAIL 消息强制标记。

**FAIL 是单向的**——只能 PFAIL → FAIL。清除条件：

- 节点已可达且是 replica（replica 不被 failover）
- 节点已可达且是 master 但无 slot（重新加入集群）
- 节点已可达且是 master 且长时间无 replica 提升（N × NODE_TIMEOUT）

最终一致：基于 gossip 的弱一致性；split brain 时少数派观点会在 rebalance 后被统一。

> The FAIL flag is only used as a trigger to run the safe part of the algorithm for the replica promotion.

## 十二、副本迁移（Replica Migration）

### 12.1 问题与思路

固定 master-replica 映射下，多次独立单节点故障累积会让某些 master 失去副本覆盖：

- Master A 故障 → A1 提升为 master
- 3 小时后 A1 独立故障 → 没有可提升的副本 → 集群不能正常服务

不增加副本数的解法：**让集群布局自动演化**——多副本 master（C 有 C1、C2）可以让一个副本迁移到无副本覆盖的 master。

### 12.2 Replica Migration 流程

- A 故障 → A1 提升
- C2 迁移为 A1 的副本
- 3 小时后 A1 故障 → C2 提升为新 master
- 集群可继续服务

### 12.3 Replica Migration 算法

- 不需要一致性协议（replica 布局不参与 config epoch 版本化）
- 算法避免 master 无副本时所有 replica 同时迁移
- 保证集群稳定后**每个 master 至少有一个副本**
- 算法在每个检测到「存在无好副本 master」的 replica 上触发，但只有一部分 replica 行动
- 「acting replica」定义：在多个有副本 master 中**副本数最多、非 FAIL、node ID 最小**的副本
- good replica 定义：从某节点视角看非 FAIL 状态的副本

## 十三、写作引用建议

- 标书「分布式缓存」章节用「16384 哈希槽 + CRC16」描述分片
- 「高可用」章节用「副本迁移」+「PFAIL/FAIL 两级故障检测」+「gossip 协议」描述自愈机制
- 「性能」章节用「无代理 + 异步复制 + 不合并 value」描述性能与一致性取舍
- 「多 key 操作」需限制 key 到同 slot（哈希标签），写标书时务必提及
- 与 `Redis-Sentinel-主从哨兵.md` 配合使用：Cluster 解决横向扩展，Sentinel 解决非集群版高可用
