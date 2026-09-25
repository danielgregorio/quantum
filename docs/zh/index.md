---
layout: home
title: Quantum
hero:
  name: Quantum
  text: 用声明式页面构建 Web 应用
  tagline: 数据库、表单、会话和 AI 都在语言之中。无需构建工具链，无需 JavaScript，无需前端框架。
  actions:
    - theme: brand
      text: 开始使用
      link: /zh/guide/quick-start
    - theme: alt
      text: 为什么选择 Quantum
      link: /zh/guide/why-quantum
    - theme: alt
      text: 在 GitHub 上查看
      link: https://github.com/danielgregorio/quantum

features:
  - icon: "🎯"
    title: 一个页面，从上到下
    details: 守卫、动作、查询和界面，按运行的顺序写在一起。无需编写 JavaScript。
  - icon: "🖥️"
    title: 浏览器、终端、桌面
    details: 同一个页面可以在浏览器（quantum start）、终端（quantum console）和桌面窗口（quantum desktop）中运行。
  - icon: "🧾"
    title: 知道自身规则的表单
    details: 表单从其动作的 q:param 中获取必填、长度、类型和可选值——在浏览器和服务器上都会检查。
  - icon: "🗃️"
    title: 值得信赖的 SQL
    details: 参数化查询、声明式的数据表结构计划、变更历史，以及针对你的数据库运行的 quantum check。
  - icon: "🤖"
    title: 语言内置 AI
    details: q:llm 根据你的文档回答，引用来源并支持流式输出；q:agent 调用你用 Quantum 编写的工具。
  - icon: "✅"
    title: 有规范，有测试
    details: 规范（SPEC）的每条规则都有测试；示例应用在 CI 中端到端运行。
source: index.md
source_hash: 15bee710f3f5
---

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/)为准。目前大部分文档仍为英文。
:::

# 欢迎使用 Quantum

Quantum 用**声明式的 XML 页面构建 Web 应用**——同一个页面也能在终端和桌面窗口中运行。它受 ColdFusion 和 Adobe Flex 启发，让你无需编写 JavaScript 就能构建内部工具、仪表盘和 AI 应用。[为什么选择 Quantum？](/zh/guide/why-quantum)

## 快速示例

一个页面：从数据库列出笔记，并通过表单添加一条——字段的规则、插入操作以及之后的提示消息都包含在内：

<<< @/../examples/cookbook/testing/first-test/components/index.q{xml}

这个页面及其测试在每次变更时都会运行——参见示例
[A first test with quantum test](/cookbook/testing/first-test)（英文）。

## 主要特性

### 语言核心
- **组件**：可复用的 `.q` 文件，带参数和返回值
- **状态管理**：用 `q:set` 定义变量，支持校验和类型检查
- **循环**：用 `q:loop` 遍历范围、数组、列表和查询结果
- **条件**：完整的 `q:if`/`q:elseif`/`q:else`
- **函数**：用 `q:function` 定义可复用的逻辑

### 界面（`ui:*`）
- **一组核心组件**：窗口、盒子、面板、表格、列表、表单和字段（[UI](/guide/ui)）
- **三种渲染器**：浏览器、终端和桌面窗口，来自同一个页面
- **来自动作的表单**：字段、规则和错误都来自动作的 `q:param`
- **来自查询的表格**：分页、边输入边搜索、可排序和可编辑的单元格

### 后端功能
- **数据库查询**：带参数的 SQL、数据表结构计划、变更历史、`quantum check`
- **认证**：会话管理和基于角色的访问控制
- **数据导入**：JSON、CSV 和 XML 数据源
- **文件和邮件**：上传、受保护的下载和 `q:mail`（[指南](/guide/files-and-mail)）
- **AI**：带来源和流式输出的 `q:llm`、`q:knowledge`、`q:agent`（[指南](/guide/ai)）

## 理念

> **简单胜于配置**

Quantum 优先考虑可读性和易用性。如果你会 XML 和 SQL，就能构建完整的应用。

## 开始使用

```bash
pip install quantum-framework
quantum start          # in an application folder; the guide builds one step by step
```

[阅读快速入门指南](/zh/guide/quick-start)
