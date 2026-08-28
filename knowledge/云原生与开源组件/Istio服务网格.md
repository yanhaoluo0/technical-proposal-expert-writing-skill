# Istio 服务网格

> **素材来源**：https://istio.io/latest/about/service-mesh/
> **抓取日期**：2026-08-28
> **整理方式**：整篇转写（原文篇幅较短，删除版本号公告、反馈按钮、链接脚注列表；保留 What is Istio / Features / Why Istio 核心段）
> **适用文档类型**：方案设计报告、技术标书「服务网格」「微服务治理」章节
> **可支撑的技术点**：Istio, 服务网格, mTLS, 零信任, 流量管理, 金丝雀, A/B 测试, 可观测性, Envoy, Ambient 模式, Sidecar 模式
> **写作约束**：Istio 官方为唯一来源；具体组件与配置应回到官网原文核对

## 概述

Istio 通过在应用旁挂代理（应用级代理），为网络加入**应用感知的流量管理、强可观测性、强安全能力**，无需修改应用代码。Istio 由 Google、IBM、Lyft 于 2016 年创立，是 CNCF 毕业项目，与 Kubernetes、Prometheus 并列。本文整篇转写自 Istio 官方「About / Service Mesh」页，是写作中描述服务网格能力边界的标准出处。

## 一、What is Istio

> A **service mesh** is an infrastructure layer that gives applications capabilities like zero-trust security, observability, and advanced traffic management, without code changes. **Istio** is the most popular, powerful, and trusted service mesh.

Istio 解决开发者与运维在分布式/微服务架构中遇到的挑战：无论是从零构建、云原生迁移、还是加固现有系统。

### 1.1 三大能力

- **安全与治理**：mTLS 加密、策略管理、访问控制
- **网络功能**：金丝雀发布、A/B 测试、负载均衡、故障恢复
- **可观测性**：跨服务的流量可观测

### 1.2 跨环境

- 不限于单一集群、网络、运行时——Kubernetes、VM、多云、混合、本地都可纳入同一网格

### 1.3 扩展生态

- 可独立安装；可选 Istio 商业发行版
- 生态提供多种场景的打包集成

## 二、Features（核心特性）

### 2.1 Secure by default（默认安全）

- 基于**工作负载身份 + 双向 TLS + 强策略控制**的零信任方案
- 落地 Google BeyondProd 思想的开源实现
- 避免厂商锁定与单点故障

### 2.2 Increase observability（强可观测性）

- 在服务网格内生成遥测数据
- 与 APM 集成（Grafana、Prometheus）输出洞察指标

### 2.3 Manage traffic（流量管理）

- 简化流量路由与服务级配置
- 支持 A/B 测试、金丝雀发布、按比例分流的灰度发布

## 三、Why Istio

### 3.1 多种部署模式（Multiple Deployment Modes）

- 数据面两种模式可选：
  - **Ambient 模式**——简化的应用运维生命周期
  - **传统 Sidecar 模式**——复杂配置场景

### 3.2 由 Envoy 驱动（Powered by Envoy）

- Envoy 是云原生事实标准网关代理
- 通过 WebAssembly 扩展自定义流量功能
- 可集成第三方策略系统

### 3.3 真正的社区项目（A True Community Project）

- 由云原生领域大量创新者共同设计
- 现代化工作负载导向

### 3.4 稳定的二进制发布（Stable Binary Releases）

- 跨生产工作负载稳定部署
- 所有发布免费可访问

## 四、写作引用建议

- 标书「服务网格选型」章节引用「mTLS / 流量管理 / 可观测性」三大能力
- 「零信任安全」章节引用「工作负载身份 + 双向 TLS + 强策略控制」
- 「灰度发布」章节引用「A/B 测试 / 金丝雀发布 / 百分比分流」
- 「部署模式选型」章节引用「Ambient vs Sidecar」
- 与 `微服务-定义与九大特征-Fowler.md`、`Kubernetes架构与组件.md` 配合引用
