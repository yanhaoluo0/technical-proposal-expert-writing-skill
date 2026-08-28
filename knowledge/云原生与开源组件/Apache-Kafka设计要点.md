# Apache Kafka 设计要点

> **素材来源**：https://kafka.apache.org/documentation/（Design 章节）
> **抓取日期**：2026-08-28
> **整理方式**：精选转写（保留 Design 章节的 Motivation / Persistence / Efficiency / Producer / Consumer / Message Delivery Semantics / Transactions；删除 API、Config、Operations 等其它章节、版本号导航栏、目录页）
> **适用文档类型**：方案设计报告、技术标书「消息中间件」「高吞吐架构」章节
> **可支撑的技术点**：Kafka 设计动机, 分区, 副本, ISR, 持久化, 顺序磁盘, 零拷贝, sendfile, 端到端批压缩, 消息投递语义, at-most-once, at-least-once, exactly-once, 事务, 静态成员
> **写作约束**：定义性段落为 Kafka 官方文档原文引用，写作引用时建议标注「Apache Kafka 官方文档 Design 章节」

## 概述

Apache Kafka 设计为一个「统一平台」，处理大公司的所有实时数据流：高吞吐事件流（如实时日志聚合）、离线系统的周期性数据加载、传统低延迟消息场景、实时派生流处理。本素材精选 Design 章节中与方案论证相关的核心机制：**分区模型、副本与 ISR、文件系统持久化与零拷贝、端到端批压缩、生产者/消费者负载均衡与异步发送、三种消息投递语义、事务与静态成员**。

## 一、Design Motivation（设计动机）

Kafka 之所以成为「统一平台」，是因为它要同时支持多种用例：

- **高吞吐**：实时日志聚合等高容量事件流
- **优雅处理大数据积压**：支持离线系统的周期性数据加载
- **低延迟**：传统消息用例
- **分区、分布式、实时处理**：支持派生流的创建
- **容错**：在机器故障下保证可用性

> Supporting these uses led us to a design with a number of unique elements, more akin to a database log than a traditional messaging system.

## 二、持久化（Persistence）

### 2.1 不要害怕文件系统

**核心观点**：磁盘顺序读写在合适场景下可与网络性能相当，关键在访问模式。

- 7200rpm SATA RAID-5 阵列 6 盘的 JBOD 配置**顺序写约 600 MB/秒**，随机写仅 100 kB/秒——差距 6000 倍以上
- 现代 OS 用主内存做磁盘缓存（pagecache）；用文件系统 + pagecache 优于维护内存缓存
- 在 32 GB 机器上 pagecache 可达 28-30 GB，且无 GC 惩罚；服务重启后缓存仍热（in-process 缓存要 10+ 分钟重建）
- **设计原则**：数据立即写到持久日志（不强制刷盘）——本质是转入内核 pagecache

### 2.2 Constant Time Suffices

- 传统消息系统的 BTree 等结构 O(log N)，对磁盘不利——磁盘 seek 10ms 一次且并发受限
- Kafka 用简单读+追加文件结构：**所有操作 O(1)，读不阻塞写或不互相阻塞**
- 性能与数据量**完全解耦**——单服务器可利用多个 1+ TB SATA 盘（便宜、顺序读/写可接受）
- 「消息不立即删除」：**保留相对长时间（可一周）**，给消费方灵活回放

## 三、效率（Efficiency）

### 3.1 批处理与消息集抽象

- Kafka 协议围绕 **message set** 抽象构建——客户端/服务端/自身持久化都用同一格式
- 网络请求批量化摊薄 round-trip 开销
- 服务器一次追加整批到日志；消费者一次拉大块线性数据
- 把突发随机消息写入转化为线性写入流到消费者

### 3.2 字节拷贝与零拷贝（sendfile）

普通文件→Socket 数据路径 4 次拷贝 2 次系统调用：

1. OS 从磁盘读数据到内核 pagecache
2. 应用从内核空间读到用户空间 buffer
3. 应用写回内核空间 socket buffer
4. OS 从 socket buffer 拷贝到 NIC buffer

**Kafka 用 sendfile 系统调用**：只保留最后一次到 NIC buffer 的拷贝。

> 这让消息消费速率逼近网络连接极限。当消费者大致追上生产者时，集群的 Kafka 看到磁盘零读活动——所有数据从 cache 服务。

**注意**：TLS/SSL 在用户空间工作（Kafka 暂未支持内核 sendfile），开启 SSL 时不用 sendfile。

### 3.3 端到端批压缩

- 瓶颈可能是网络带宽（如跨数据中心数据管道）
- 单消息压缩压缩率低（同类消息之间有冗余，如 JSON 字段名、用户代理）
- Kafka **把多条消息合并压缩**：broker 验证后**保持压缩写入日志**与传输给消费者，消费者再解压
- 支持：**GZIP、Snappy、LZ4、ZStandard**

## 四、生产者（Producer）

### 4.1 负载均衡

- 生产者直接发到分区 leader 的 broker，**无中间路由层**
- 客户端控制发往哪个分区：
  - 随机实现简单负载均衡
  - 或按语义分区（按 key 哈希到分区）——如 user id 作 key 则同用户数据到同分区，消费者可做局部性处理

### 4.2 异步发送

- 生产者尝试在内存累积数据并以更大批次单请求发出
- 批处理可配置：不超过固定消息数 + 不超过固定延迟（如 64 kB 或 10 ms）
- 权衡少量额外延迟换取高吞吐

## 五、消费者（Consumer）

### 5.1 Push vs Pull

Kafka 选**传统 pull 模型**（生产者 push 到 broker，消费者 pull）：

- Push 系统难处理多样化消费者——broker 控制传输速率，consumer 跟不上时易遭 DoS
- Pull 系统的优雅降级：消费者落后就追赶，不落后就拉到所有可用消息
- Pull 还天然支持**激进的批处理**
- 朴素 pull 缺点：broker 无数据时消费者忙等；Kafka 用「long poll」请求参数解决——broker 阻塞直到数据到来（可等到给定字节数）

### 5.2 消费者位置（Consumer Position）

Kafka 与传统消息系统的关键区别：**消费偏移（offset）由消费者自己维护**，而非 broker 记录。

- 主题分为全有序分区，每分区由消费组内一个消费者消费
- 消费者位置只是「下一个要消费的消息的 offset」——一个整数
- 状态可周期性 checkpoint——「消息确认」很便宜
- **副作用**：消费者可**主动回退到旧 offset 重放数据**（违反传统队列契约，但对消费者是必要特性，如修复 bug 后重放）

### 5.3 静态成员（Static Membership，KIP-345）

目的：减少运维期间的 rebalance。

- 动态成员身份在重启/重新加入时变化，导致大量任务被重新分配
- 大状态应用恢复时间长，造成部分或全部不可用
- **静态成员**允许成员提供持久实体 ID，组成员保持稳定，不触发 rebalance
- 要求：broker 集群 + 客户端都升级到 2.3+；客户端设置 `ConsumerConfig.GROUP_INSTANCE_ID_CONFIG`
- 若客户端用静态成员但 broker < 2.3：抛 `UnsupportedException`
- 重复 ID 会触发 broker 端 fencing，通过 `FencedInstanceIdException` 强制重复客户端立即关闭

## 六、消息投递语义（Message Delivery Semantics）

三种可能保证：

- **At most once**——消息可能丢但不重投
- **At least once**——消息不丢但可能重投
- **Exactly once**——消息只被处理一次

**生产端**：

- 消息「committed」到日志仅当所有 in-sync replicas（ISR）都应用到日志
- 已 committed 的消息只要有一个复制该分区的 broker 仍「alive」就不会丢
- 0.11.0.0 之前：生产者收不到 committed 响应只能重发——at-least-once
- 0.11.0.0 起：生产者支持**幂等投递**（broker 用 producer ID + 序号去重）；并支持**事务**（原子写多分区）

**消费端**：

- 消费者控制日志位置
- 选项 1：读 → 保存位置 → 处理（at-most-once）
- 选项 2：读 → 处理 → 保存位置（at-least-once）

**Exactly-once**：

- Kafka Streams 用事务性 producer + read_committed 实现
- 写外部系统时经典做法是两阶段提交；更简单做法是让消费者把 offset 与输出写到同一处（如 Kafka Connect 写 HDFS 时同时写 offsets）
- 默认 at-least-once；禁用 producer 重试 + 消费前提交 offset 可实现 at-most-once

## 七、事务（Transactions）

要点：

- Kafka 事务与其它消息系统不同：**消费者与生产者分离，仅生产者是事务性的**
- 事务让生产者的所有记录与为消费者更新的 offset 原子完成
- 三要素：
  1. 消费者用 partition assignment 确保是消费组内当前处理该分区的唯一消费者
  2. 生产者用事务让所有生产记录与 offset 更新原子完成
  3. 一个消费者实例配一个生产者实例（rebalance 友好）
- 一般建议用 `read_committed` 隔离级别
- 配置：`isolation.level=read_committed`、`enable.auto.commit=false`（consumer）；`transactional.id`（producer）

## 八、写作引用建议

- 标书「消息中间件选型」引用 Motivation + 持久化 + 效率三段
- 「高吞吐设计」引用 pagecache + 零拷贝 + 端到端批压缩
- 「数据可靠性」引用 ISR + 三种投递语义 + 事务
- 「消费者重放」引用 Consumer Position 段（解决 bug 回放场景）
- 「运维稳定性」引用 Static Membership（解决大状态应用 rebalance）
