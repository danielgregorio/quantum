---
source: guide/getting-started.md
source_hash: e67760de8b10
---

# 入门

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/getting-started)为准。
:::

欢迎使用 Quantum！本指南帮助你在几分钟内上手 Quantum 框架。

## Quantum 是什么？ {#what-is-quantum}

Quantum 是一个用 XML 编写 Web 应用的**全栈声明式框架**。它的设计理念是"简单胜于配置"——让复杂的任务变得简单，同时保持语言干净、易读。

### 主要优点 {#key-benefits}

- **不需要 JavaScript** - 只用 XML 和 SQL 构建交互式应用
- **AI 即标签** - 模型调用、RAG 和带工具的智能体，不需要 Python 胶水代码
- **全栈** - 内置数据库查询、表单、会话和身份认证
- **经过校验的输入** - 声明的参数在你的代码运行之前就完成类型检查

## 前提条件 {#prerequisites}

- **Python 3.12+**
- **pip**

## 安装 {#installation}

```bash
pip install quantum-framework
quantum --version
```

可选依赖（PostgreSQL/MySQL、RAG、jobs、websockets）以及桌面目标所需的额外依赖，
列在[安装](/zh/guide/installation)中。

## 你的第一个组件 {#your-first-component}

创建一个名为 `hello.q` 的文件：

```xml
<q:component name="HelloWorld" xmlns:q="https://quantum.lang/ns">
  <q:return value="Hello World!" />
</q:component>
```

**Output:** `Hello World!`

运行它：

```bash
quantum run hello.q
```

## 添加动态内容 {#adding-dynamic-content}

用变量和循环让它更有意思一些：

```xml
<q:component name="Greetings" xmlns:q="https://quantum.lang/ns">
  <!-- Define a variable -->
  <q:set name="greeting" value="Hello" />

  <!-- Loop through a list -->
  <q:loop type="list" var="name" items="Alice,Bob,Charlie">
    <q:return value="{greeting} {name}!" />
  </q:loop>
</q:component>
```

**Output:**

```
["Hello Alice!", "Hello Bob!", "Hello Charlie!"]
```

## 使用条件 {#using-conditionals}

```xml
<q:component name="AgeCheck" xmlns:q="https://quantum.lang/ns">
  <q:set name="age" value="25" />

  <q:if condition="age >= 18">
    <q:return value="You are an adult" />
  </q:if>
  <q:else>
    <q:return value="You are a minor" />
  </q:else>
</q:component>
```

**Output:** `You are an adult`

## 创建函数 {#creating-functions}

```xml
<q:component name="Calculator" xmlns:q="https://quantum.lang/ns">
  <q:function name="add" returnType="number">
    <q:param name="a" type="number" required="true" />
    <q:param name="b" type="number" required="true" />
    <q:set name="result" value="{a + b}" />
    <q:return value="{result}" />
  </q:function>

  <q:set name="sum" value="{add(5, 3)}" />
  <q:return value="5 + 3 = {sum}" />
</q:component>
```

**Output:** `5 + 3 = 8`

## Web 应用 {#web-applications}

页面就是 `components/` 文件夹中的组件，文件名就是 URL。
创建 `components/index.q`：

```xml
<q:component name="index" xmlns:q="https://quantum.lang/ns">
  <html><body>
    <h1>Welcome to My App</h1>
    <p>Now: {dateFormat(now(), '%H:%M')}</p>
  </body></html>
</q:component>
```

**Shows:** `Welcome to My App`

在包含 `components/` 的文件夹中启动服务器：

```bash
quantum start
```

打开 `http://localhost:8080`。[快速开始](/zh/guide/quick-start)会接着介绍数据库和表单。

::: warning `q:application type="html"`
一些旧页面把 Web 应用描述为带有 `q:route` 块的 `q:application type="html"`。
这种形式从未运行过它的路由，已在 0.11 中移除——请像上面那样使用 `components/`。
参见 [q:application](/guide/applications)。
:::

## 调试模式 {#debug-mode}

获取详细的执行信息：

```bash
quantum run hello.q --debug
```

它会显示：
- 文件解析的细节
- AST 生成的信息
- 校验步骤
- 执行流程

## 下一步 {#next-steps}

- [安装详情](/zh/guide/installation) - 完整的安装指南
- [项目结构](/guide/project-structure) - 如何组织你的代码
- [组件](/zh/guide/components) - 深入了解组件
- [AI](/guide/ai) - 以标签形式调用 LLM、RAG 和智能体
- [实用示例](/zh/cookbook/) - 经过测试的示例，每个只做一件事
