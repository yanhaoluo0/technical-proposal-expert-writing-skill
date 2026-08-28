# Kubernetes 集群架构与组件

> **素材来源（合并两条）**：
> - Cluster Architecture：https://kubernetes.io/docs/concepts/architecture/
> - Components：https://kubernetes.io/docs/concepts/overview/components/
> **抓取日期**：2026-08-28
> **整理方式**：精选转写 + 合并（架构概览 + 组件职责列表，删除最新更新说明、相关链接导航、反馈区、第三方内容免责声明）
> **适用文档类型**：方案设计报告、技术标书「容器化平台」「基础设施」章节
> **可支撑的技术点**：Kubernetes 架构, 控制面, 数据面, 控制平面组件, 节点组件, kube-apiserver, etcd, kube-scheduler, kube-controller-manager, kubelet, kube-proxy, 容器运行时, 集群部署
> **写作约束**：Kubernetes 官方文档为本素材唯一来源；具体配置与版本特性应回到官网原文核对

## 概述

Kubernetes 集群由**控制面（Control Plane）**和**一组工作节点（Node）**组成。控制面管理全局决策（调度、响应集群事件）；节点承载运行的 Pod（应用工作负载）。生产环境的控制面通常跨多台机器部署，集群运行多个节点以提供容错与高可用。本素材合并了「Cluster Architecture」与「Components」两份官方文档，可作为标书「容器化平台」「云原生基础设施」章节的架构描述与配图依据。

## 一、整体架构

```
控制面（Control Plane）
├─ kube-apiserver        Kubernetes API 前端
├─ etcd                  集群数据 KV 存储
├─ kube-scheduler        Pod 调度
├─ kube-controller-manager 控制器集合（Node / Job / EndpointSlice / ServiceAccount / ...）
└─ cloud-controller-manager 云厂商集成（可选）

节点（Node）
├─ kubelet               节点 Agent，确保 Pod/容器运行
├─ kube-proxy（可选）    Service 网络规则维护
└─ Container runtime     容器运行时（containerd / CRI-O / 任意 CRI 实现）

插件（Addons，命名空间 kube-system）
├─ DNS                   集群 DNS
├─ Web UI (Dashboard)    集群管理界面
├─ Container Resource Monitoring  容器指标
├─ Cluster-level Logging 集中日志
└─ Network plugins       CNI 网络插件
```

> Figure source: kubernetes.io/docs/concepts/architecture/

## 二、控制面组件（Control Plane Components）

> 控制面组件对集群做全局决策（调度），并检测/响应集群事件（如 Deployment 的 replicas 不满足时启动新 Pod）。可运行于集群任意机器；生产环境通常跨多机器部署。

### 2.1 kube-apiserver

- Kubernetes 控制面的**API 前端**
- 设计为**水平扩展**——通过部署更多实例扩展
- 可运行多个实例并在实例间负载均衡

### 2.2 etcd

- **一致、高可用的 KV 存储**，作为 Kubernetes 所有集群数据的后备存储
- 必做 etcd 数据备份（详见 etcd 官方文档）

### 2.3 kube-scheduler

- 监视**未分配节点的新建 Pod**，并为其选择合适节点
- 调度考虑因素：单独与汇总资源需求、硬件/软件/策略约束、亲和性与反亲和性、数据局部性、工作负载间干扰、截止时间

### 2.4 kube-controller-manager

- 运行**控制器进程**
- 每个控制器是逻辑独立进程，但为减少复杂度都编译到同一二进制
- 控制器示例：
  - **Node controller**——节点下线时响应
  - **Job controller**——监控 Job 对象并创建 Pod 执行一次性任务
  - **EndpointSlice controller**——填充 EndpointSlice 对象（连接 Services 与 Pods）
  - **ServiceAccount controller**——为新 namespace 创建默认 ServiceAccount

### 2.5 cloud-controller-manager（可选）

- 嵌入云厂商特定控制逻辑
- 把与云平台交互的组件与仅与集群交互的组件分离
- 自建机房或学习环境无此组件
- 控制器示例：
  - **Node controller**——向云厂商查询节点是否已删除
  - **Route controller**——配置底层云网络路由
  - **Service controller**——创建、更新、删除云负载均衡

## 三、节点组件（Node Components）

> 节点组件运行于每个节点，维护运行中的 Pod 并提供 Kubernetes 运行时环境。

### 3.1 kubelet

- 运行于每个节点的 Agent
- 确保 PodSpec 中描述的容器运行且健康
- **不管理 Kubernetes 未创建的容器**

### 3.2 kube-proxy（可选）

- 节点上的网络代理，实现 Kubernetes Service 概念的一部分
- 在节点维护网络规则，使集群内/外网络会话能与 Pod 通信
- 使用 OS 包过滤层；若不可用则自行转发
- 若 CNI 插件自带等价包转发，可不部署 kube-proxy

### 3.3 Container runtime（容器运行时）

- 负责容器执行与生命周期管理的基础组件
- Kubernetes 支持：**containerd、CRI-O、任意 Kubernetes CRI 实现**

### 3.4 其它节点软件

集群可能在每个节点还需其他软件，例如 Linux 节点的 **systemd** 用以监管本地组件。

## 四、插件（Addons）

> 插件用 Kubernetes 资源（DaemonSet、Deployment 等）实现集群功能；命名空间资源通常位于 `kube-system`。

### 4.1 DNS

- 所有 Kubernetes 集群**应当**配置集群 DNS（很多示例依赖它）
- 集群 DNS 是 DNS 服务器，附加在环境中其它 DNS 之外，为 Kubernetes 服务提供 DNS 记录
- Kubernetes 启动的容器自动将 DNS 服务器加入搜索列表

### 4.2 Web UI (Dashboard)

- 集群通用 Web UI，可管理与排障集群中的应用与集群本身

### 4.3 Container Resource Monitoring

- 记录容器通用时序指标到中央数据库，提供浏览 UI

### 4.4 Cluster-level Logging

- 集中保存容器日志到中央日志存储，提供搜索/浏览界面

### 4.5 Network plugins

- 实现容器网络接口（CNI）规范
- 负责为 Pod 分配 IP 并实现 Pod 间通信

## 五、架构变体（Architecture Variations）

虽然 Kubernetes 核心组件不变，部署与管理方式可灵活调整。

### 5.1 控制面部署选项

| 选项 | 说明 |
|---|---|
| Traditional deployment | 控制面直接运行于专用机器/虚拟机，通常作为 systemd 服务 |
| Static Pods | 控制面以静态 Pod 部署，由 kubelet 在特定节点管理（kubeadm 常用） |
| Self-hosted | 控制面以 Pod 形式运行于集群内，由 Deployment / StatefulSet 管理 |
| Managed Kubernetes services | 云厂商抽象控制面，作为其服务一部分管理 |

### 5.2 工作负载放置考虑

- 小型/开发集群：控制面与用户工作负载可能同节点
- 大型生产集群：通常为控制面专设节点
- 部分组织在控制面节点运行关键 add-on / 监控工具

### 5.3 集群管理工具

- **kubeadm、kops、Kubespray** 提供不同部署与管理方法，每种方法组件布局与管理方式不同

### 5.4 自定义与扩展

- 自定义调度器可与默认调度器并存或替换
- API server 可通过 **CustomResourceDefinitions** 与 **API Aggregation** 扩展
- 云厂商可通过 **cloud-controller-manager** 与 Kubernetes 深度集成

## 六、写作引用建议

- 标书「容器化平台」「PaaS 平台」「云原生基础设施」章节可用本文作为架构描述、配图依据
- 「运维监控」章节可结合 DNS / Monitoring / Logging 插件段落
- 「高可用」章节可结合控制面跨机器部署、节点组件副本、etcd 备份等段落
- 与 `Istio服务网格.md`、`Apache-Kafka设计要点.md` 互为支撑
