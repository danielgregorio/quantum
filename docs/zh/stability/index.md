---
source: stability/index.md
source_hash: b2f88ba7b500
---

# 稳定性

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。英文页面由 `SUPPORT_TIERS.md` 自动生成，本译文可能滞后于它；内容如有出入，以[英文原文](/stability/)为准。
:::

Quantum 逐个标签地说明它承诺什么。从 1.0 起，**核心层（Core）和 AI 层遵循语义化版本（semver）**：
1.x 版本不会破坏只使用这两层的程序——它们的含义由[规范](/reference/spec)中的规则确定，
不兼容的变更要等到 2.0。实验层（Experimental）和实验室（Laboratory）不作这样的承诺。

本页是承诺本身。今天实际能运行的内容，在[状态](/status/)页面上是测量出来的；每一处变更都在[更新日志](/changelog/)中。

## 一句话

> **Quantum——用 XML 编写的声明式 Web 应用，语言内置 AI 与 RAG。
> 无需构建工具链，无需 JavaScript，无需前端框架。**

不符合这句话的东西，就不属于 README 或介绍文字。它可以继续存在——在另一个层级，或者另一个仓库中。

## 面向谁

独立开发者和小团队，构建内部工具、仪表盘、管理后台和 AI 应用，并且不想要前端构建工具链。

---

## 层级

### 核心层——框架本身

有文档、经过端到端测试、稳定。这里出现破坏是严重缺陷。一个标签进入核心层，必须具备：
`SPEC.md` 中的一条规则以及引用它的测试、一个能运行的示例、一个指南页面，以及
`FEATURE_STATUS.md` 中的一行。

| 标签 | 作用 |
|---|---|
| `q:component` | 组合的单元，配合 `q:param` / `q:return` |
| `q:set` | 变量和作用域（`session.` / `application.` / `request.`） |
| `q:if` | 条件（`q:elseif` / `q:else`） |
| `q:loop` | 迭代（数组、列表、范围、查询） |
| `q:function` | 可复用的函数，配合 `q:param` / `q:return` |
| `q:query` | 参数化 SQL——必须使用 `q:param`，从构造上杜绝注入；分页、schema 检查（`quantum check`）、变更历史（DB-11） |
| `q:transaction` | 一起提交或一起回滚的查询（DB-4） |
| `q:action` | 表单处理，配合 `q:redirect` 和 `q:flash`；`q:param` 中的规则在服务器上校验，并显示在对应字段旁边 |
| `q:invoke` | 调用函数、组件或 HTTP 服务 |
| `q:data` | 导入和转换 CSV/JSON/XML |
| `q:import` / `q:slot` | 组件组合 |
| `q:file` | 上传到 `paths.uploads`，以及由页面决定谁可以下载（FILE-1、FILE-2） |
| `q:mail` | 通过 `mail:` 配置发送邮件，开发时有日志模式（MAIL-1、MAIL-2） |
| `ui:*`——核心集合 | 页面中的界面，列在 SPEC UI-7 中。浏览器（`quantum start`）、终端（`quantum console`）和窗口（`quantum desktop`，在本地窗口中显示页面）以相同的含义绘制它们；同一份一致性脚本在真实浏览器和终端中运行 |
| `require_auth` / `require_role` | 基于 `session` 作用域、按组件进行的身份认证和授权；表达式中的 `hashPassword` / `verifyPassword` |

### AI 层——项目存在的理由

与核心层相同的约定，外加每次发布前针对真实模型的实时测试。这是 Quantum 拥有、而其他声明式框架没有的东西。

| 标签 | 作用 | 验证依据 |
|---|---|---|
| `q:llm` | 补全与对话；`knowledge=` 基于知识库回答并引用来源；`stream="true"` 边生成边发送回答 | IA-1…IA-8、`projects/docs-assistant` |
| `q:knowledge` | 基于文本、文件和查询的向量知识库（RAG） | IA-2、IA-6、IA-8、`projects/docs-assistant` |
| `q:agent` | 工具在 `.q` 中声明的智能体，带有失败约定和时间预算 | IA-4、IA-5、`projects/shop-agent` |

### 实验层——存在，但不作承诺

保留并且可以工作，但**不出现在 README 和介绍中**，不保证 API 稳定。它进入核心层需要同样严格的条件：
一条 SPEC 规则及其测试、一个示例、一个指南页面，以及状态页中的一行。

| 领域 | 标签 |
|---|---|
| 多智能体 | `q:team`——还没有 SPEC 规则，也没有验证应用 |
| 任务 | `q:job`、`q:schedule`、`q:thread` |
| 消息 | `q:message`、`q:queue`、`q:subscribe`、`q:messageAck`、`q:messageNack`、`q:websocket`、`q:websocket-send`、`q:websocket-close` |
| 服务 | `q:log`、`q:dump` |
| 脚本 | `q:python`、`q:pyclass`、`q:pyimport`——**默认关闭**，用 `security.python_scripting` 开启（见 SECURITY.md） |
| 事件 | `q:dispatchEvent` |
| 装饰器 | `q:decorator` / `q:pydecorator`——有解析器和 AST 节点，但运行时中没有任何使用者；要么为 `q:function` 设计装饰器，要么移除这些标签。在此之前不写文档 |
| UI / 其他目标 | 核心集合之外的 `ui:*` 元素（仅浏览器；终端会说明它不绘制这些元素）；独立的 `q:application type="ui"` 构建（`--target html`/`textual`，仅布局，UI-8）；终端目标（`qt:`）、htmx、islands |

### 实验室——留在仓库中，不在承诺范围内

这些项目**留在仓库中**，因为它们给语言施加压力——在"玩"的过程中，核心需要的功能和缺陷才会显现。
它们不出现在介绍中，没有稳定性承诺，运行时会在第一次运行时给出一次警告（`quantum/core/tiers.py`）。
它们的测试在 CI 中有自己独立的任务（`pytest -m laboratory`），和主任务一样是必需的；这样，破坏了游戏的核心变更会被发现——
而 CI 变红时也能立刻看出是哪一边出了问题。

| 领域 | 说明 |
|---|---|
| 2D 游戏引擎（`qg:`）、Godot 代码生成 | `projects/` 和 `examples/` 中的游戏由代码生成器构建；永远不要手动编辑生成的输出。破坏了某个游戏的语言变更，要在同一次变更中迁移它的 `.q` 源文件 |
| `quantum-as4`（MXML/AS4 → JS 编译器） | `test_transpiler_comprehensive.py` 中有一个未解决的回归 |
| `quantum run --target mobile`（React Native） | 自行把 `q:set`/`q:function` 翻译成 JavaScript——与"一个运行时"正好相反。手机不在 1.0 的范围内。运行时警告一次（`tiers.warn_ui_target`） |

---

## 如何避免它过时

`ROADMAP.md` 之所以过时，是因为它靠手工维护、却没人检查。防线如下：

1. **`FEATURE_STATUS.md` 是生成的**，通过真正运行示例得到（`scripts/generate-feature-status.py`）。
2. **`manifest.yaml` 对"能不能用"没有发言权**——29 个靠手工同步的文件，正是它们走样的原因。
3. **引擎强制执行层级**（`quantum/core/tiers.py`，在 `tests/unit/test_tiers.py` 中测试）；本页与那个文件一起修改。
4. **本文件只能通过明确的决定来修改**，而且修改很小：在层级之间移动一个标签。

## 1.0 的变化

| 变化 | 原因 |
|---|---|
| 层级名称改为英文：Core、AI、Experimental、Laboratory | 仓库使用英文 |
| `q:file`、`q:mail` 和 `q:transaction` → 核心层 | 每个都有带测试的 SPEC 规则（FILE-1/2、MAIL-1/2、DB-4），并且有一个在 CI 中使用它的应用（`projects/helpdesk`、`projects/blog`） |
| `q:team` → 实验层 | 没有 SPEC 规则，也没有验证应用；AI 层只承诺经过验证的东西 |
| `ui:*` 核心集合 → 核心层（0.16） | UI-1…UI-14、一致性脚本、三个渲染器 |
| `q:decorator` / `q:transaction` 曾经"没有层级" | `q:transaction` 有了它的规则（DB-4）；装饰器归入实验层，见上面的说明 |
