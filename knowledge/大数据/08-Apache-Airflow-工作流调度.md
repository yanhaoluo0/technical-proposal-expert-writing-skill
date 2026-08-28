# Apache Airflow 工作流调度

> **素材来源**：https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/overview.html
> **抓取日期**：2026-08-28
> **整理方式**：技术深度型（八段卡片）。原始抓取 41KB 含全站导航（已剥离）。核心机制围绕 Components / Architecture Diagrams / Executor / DAG / Task / Operator 展开。
> **适用文档类型**：方案设计报告、技术标书「工作流调度」「ETL 编排」「任务调度」章节
> **可支撑的技术点**：Airflow, DAG, Scheduler, Executor, CeleryExecutor, KubernetesExecutor, LocalExecutor, Task SDK, Metadata DB, DAG Processor, Triggerer, Resumable Tasks, DAG Bundle
> **写作约束**：术语沿用 Apache Airflow 官方文档（v3.x）；不可编造具体性能基准。

## 1. 适用场景与触发词

需要「Python 表达的工作流调度 + DAG 依赖 + 多执行器 + 可视化 UI + 丰富 Provider 生态」时命中本卡片：

- 业务场景：离线 ETL、批处理任务编排、跨系统数据同步、机器学习流水线、定时报表
- 标书或设计报告关键词：「Airflow」「DAG」「工作流调度」「ETL 调度」「TaskFlow」「Executor」「KubernetesExecutor」「CeleryExecutor」

## 2. 技术内涵与边界

**做什么**：

- Python 编写的平台，用 DAG（有向无环图）表达工作流
- 任务（Task）依赖关系显式定义；调度器按 DAG 解析触发
- 与执行的具体内容无关（agnostic）——可执行任何命令、Python 函数，或通过 Provider 集成
- 多种 Executor：LocalExecutor、CeleryExecutor、KubernetesExecutor 等
- 提供 Web UI 用于检查、触发、调试 DAG 与 Task

**不做什么**：

- 不擅长毫秒级实时调度（分钟级是典型粒度）
- 不擅长有状态长驻任务（这种场景用 Flink / Spark Streaming）
- 不等于消息流处理——Airflow 是「批量任务编排」而非「流处理」
- 不替代数据库——DAG 状态存储依赖元数据库（PostgreSQL / MySQL）

## 3. 典型架构与关键机制

### 3.1 必要组件

> 官方原文：「A minimal Airflow installation consists of the following components:」

- **Scheduler**：处理触发与提交任务；执行器是其内部属性
- **DAG Processor**：从 DAG Bundle 解析 DAG 文件并序列化到元数据库
- **DAG Bundle**：DAG 文件来源（默认本地文件系统；可配置为 Git / S3）
- **API Server**：提供 REST API 与 Web UI；Task 通过 Task SDK 与 API Server 通信（避免直接访问元数据库）
- **Metadata Database**：存储任务状态、DAG、变量（PostgreSQL / MySQL）

### 3.2 可选组件

- **Worker**：执行 Scheduler 派发的任务（CeleryExecutor 中作为长进程；KubernetesExecutor 中作为 POD）
- **Triggerer**：执行 deferrable task 的 asyncio 事件循环（Deferrable Operator & Trigger）
- **Plugins**：扩展 Airflow 功能；Scheduler、DAG Processor、Triggerer、API Server 均会加载

### 3.3 部署模式

> 官方原文：「While Airflow can be run in a single machine and with simple installation where only scheduler, Dag processor and API server are deployed, Airflow is designed to be scalable and secure, and is able to run in a distributed environment.」

| 模式 | 适用 |
|---|---|
| Basic | 单机部署；LocalExecutor；Scheduler 与 Worker 同进程；适用开发与小型场景 |
| Distributed | 各组件独立部署；不同安全边界；规模化生产 |
| Separate DAG Processing | Scheduler 与 DAG Processor 分离；Scheduler 不直接访问 DAG Bundle，增强安全 |

### 3.4 执行器（Executor）

| Executor | 特点 | 适用 |
|---|---|---|
| SequentialExecutor | 顺序执行；调试用 | 仅开发 |
| LocalExecutor | 单机多进程 | 中小规模 |
| CeleryExecutor | 依赖 Celery + 消息队列 | 中等规模 |
| KubernetesExecutor | 每个 Task 启动 K8s POD | 大规模 + 资源隔离 |

### 3.5 Task 执行架构（v3+）

- **Python Task SDK Execution**：Task 在独立进程中执行；通过 SDK 与 Airflow API Server 通信
- **Non-Python language SDKs（Go、Java）**：非 Python 语言 Task SDK 通信协议相同

### 3.6 角色（Airflow Security Model）

- Deployment Manager：安装、配置、管理部署
- DAG Author：编写 DAG 并提交
- Operations User：触发与监控

## 4. 关键设计决策与权衡

### 决策 1：Executor 选型

- **LocalExecutor（本方案中等规模生产采用）**：无需外部依赖；单机可启动多个 Task
- **CeleryExecutor**：需 Celery + Redis/RabbitMQ；任务队列化；适合分布式
- **KubernetesExecutor（本方案大规模弹性场景采用）**：每个 Task 一个 POD；资源彻底隔离；冷启动开销
- **代价**：K8s Executor 冷启动开销（数秒~十几秒）；不适合短任务

### 决策 2：DAG 表达（TaskFlow vs 传统）

- **TaskFlow（@task 装饰器）**：Pythonic；自动 XCom 处理；推荐现代写法
- **传统 Operator + set_upstream / set_downstream**：显式依赖；可读性高
- **代价**：TaskFlow 隐式 XCom 可能引入大对象在元数据库；需小心

### 决策 3：元数据库选型

- **PostgreSQL**：推荐；与 Airflow 兼容性最佳
- **MySQL**：支持；功能略受限
- **SQLite**：仅 SequentialExecutor；开发用

### 决策 4：DAG Bundle 与代码管理

- 本地文件系统、DAG Processor 持续监听
- Git 仓库（GitSync）；S3 / GCS 拉取
- **代价**：本地文件系统易产生「DAG 与部署耦合」；推荐 Git + GitSync

## 5. 工程化要点

- **部署**：K8s 上 Airflow 通过 Helm Chart / KubernetesExecutor 部署
- **DAG 编写**：
  - 文件按 `dags/` 目录组织；定时（schedule）使用 cron 表达式
  - 任务依赖：`>>` / `<<` / `set_upstream`
  - Catchup：默认禁用，避免历史 backfill
  - SLA：监控任务超时
- **Task 编写**：
  - Operator / Sensor（监听外部条件，如文件到达、API 可达）
  - Deferrable Operator（释放 Worker 资源，等外部触发）
  - TaskFlow（@task 装饰器）
- **监控**：
  - Web UI（Gantt、Tries、Logs）
  - Metrics Exporter（Prometheus）
  - Flower（Celery 场景）
- **运维**：
  - Scheduler HA（多 Scheduler 选举）
  - DAG 解析性能监控
  - 元数据库备份
  - Plugin / Provider 升级

## 6. 指标映射

| 指标 | 口径示例 | 支撑手段 |
|---|---|---|
| DAG 数量 | 单集群 ≤ N 个 | 拆分多集群 |
| Task 失败率 | ≤ X% | Alert + 重试 |
| DAG 运行延迟 | 触发 → 完成 ≤ Y 分钟 | SLA + Alert |
| Scheduler HA | 多 Scheduler 选举 | HA Scheduler 集群 |
| 资源利用率 | Worker CPU / Mem | K8s HPA（基于 Pending Task 数） |
| 元数据库 QPS | ≤ M QPS | PostgreSQL 性能调优 |

## 7. 标书化叙述示例

> 本方案离线数据通道与定时任务采用 Apache Airflow 作为工作流调度引擎。集群部署采用 KubernetesExecutor 模式，Scheduler / API Server / DAG Processor / Triggerer 独立部署；元数据库使用 PostgreSQL；DAG Bundle 通过 Git + DAG Processor 持续同步。任务按业务域拆分到独立 DAG 文件，使用 TaskFlow（@task）方式编写；定时策略使用 cron 表达式；关键任务启用 Catchup=False 避免历史 backfill；启用 SLA + Alert 监控超时。Task 类型按场景选择——Operator 执行命令；Sensor 监听外部条件；Deferrable Operator 处理长等待任务（如等待文件到达、API 回调）以减少 Worker 占用。监控通过 Airflow Web UI + Prometheus Exporter 上送 DAG 数量、Task 失败率、DAG 运行延迟、Scheduler HA 状态四类指标；Worker 资源按 Pending Task 数自动扩缩。具体业务的 DAG 数量、Task 并发、运行周期由用户在合同附件中按业务等级明确。

## 8. 风险与边界

- **不可编造项**：
  - Airflow 各版本（2.x / 3.x）的 Executor、Task SDK 兼容性矩阵需回到官方文档核对
  - 具体 DAG 数量、Task 并发等数字必须实测或用户提供
- **常见失败模式**：
  - DAG 解析慢 → 拆分 DAG 文件 + 优化 import
  - 元数据库瓶颈 → PostgreSQL 调优 + 拆分集群
  - Task 重试风暴 → 限制 max_tries / retry_delay
  - 时区错配 → 统一使用 UTC
  - 跨 DAG 依赖 → 用 Datasets / ExternalTaskSensor（避免耦合）
- **架构外延**：本卡片聚焦 Airflow 核心；不涵盖 Astronomer（托管）、DAG Factory、Task SDK 二次开发等周边