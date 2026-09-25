---
source: guide/why-quantum.md
source_hash: b3e57fbe210d
---

# 为什么选择 Quantum

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/why-quantum)为准。
:::

**Quantum 用声明式的 XML 页面构建 Web 应用——数据库、表单、会话和 AI
都在语言本身之中。无需构建工具链，无需 JavaScript，无需前端框架。**

它面向独立开发者或小团队，用来构建内部工具、仪表盘、管理后台以及使用语言模型的应用——
也就是那种前端构建工具链的成本比产品本身还高的软件。

## 一个页面是什么样子

```xml
<q:component name="Tasks">
  <q:action name="add" method="POST">
    <q:param name="title" required="true" minlength="3" />
    <q:query name="added" datasource="db">
      INSERT INTO tasks (title) VALUES (:title)
      <q:param name="title" value="{title}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Added: {title}" />
  </q:action>

  <q:query name="tasks" datasource="db">SELECT id, title FROM tasks ORDER BY id</q:query>

  <ui:window title="Tasks">
    <q:if condition="flash"><ui:alert variant="info">{flash}</ui:alert></q:if>
    <ui:form on-submit="add" submit="Add" />
    <ui:table source="{tasks}" />
  </ui:window>
</q:component>
```

这就是完整的功能：表单根据动作的 `q:param` 生成字段（`required` 和 `minlength`
在浏览器和服务器上都会校验），查询天然是参数化的，而且同一个页面可以运行在浏览器
（`quantum start`）、终端（`quantum console`）和桌面窗口（`quantum desktop`）中。

## 有什么不同

- **一个页面一个文件，从上到下。** 访问控制、动作、查询和界面按照它们执行的顺序排列
  （[页面如何运行](/guide/how-a-page-runs)）。
- **规则只写在一个地方。** `q:param` 说明一个字段必须满足什么；表单、服务器和
  `quantum check` 都读取它。
- **AI 是语言的一部分。** `q:llm` 基于 `q:knowledge` 知识库回答并引用来源，
  可以边生成边输出；`q:agent` 调用你用 Quantum 函数编写的工具——每一项都有页面可以处理的
  失败约定（[AI](/guide/ai)）。
- **它不假装成功。** 没有配置服务器的邮件、无法读取的知识来源、不起作用的属性：
  每一种都是一个告诉你该怎么做的错误，而不是悄无声息的"成功"。

## 我们如何知道它能用

- 一份带编号规则的[规范](https://github.com/danielgregorio/quantum/blob/main/SPEC.md)；
  如果某条规则没有测试，测试套件就会失败。
- `projects/` 中的真实应用，每一个都在 CI 中进行端到端测试：一个任务列表（浏览器、终端、
  桌面）、一个博客、一个仪表盘、一个带上传和邮件的工单系统、一个文档助手（RAG），
  以及一个基于 SQLite 数据库的智能体。AI 应用还会针对真实的模型服务器进行测试。
- 每次发布都会从 PyPI 安装到一个干净的环境中运行。

## 它不是什么

- **不是移动端框架。** 手机不在 1.0 的范围内；React Native 目标只是一个实验。
- **不是 SPA 框架。** 页面在服务器端渲染；浏览器拿到的是 HTML，外加页面需要时的小段脚本
  （边输入边搜索、流式回答）。
- **不绑定某个模型厂商，但也不是魔法。** 小型本地模型的回答不如大模型；Quantum
  会显示来源，方便读者核对。
- **SQLite 优先。** PostgreSQL 和 MySQL 驱动已经存在，但使用得较少；迁移、schema 计划和
  `quantum check` 都是在 SQLite 上验证过的。

每个部分承诺什么，见[稳定性](/zh/stability/)：核心层和 AI 层是稳定的；实验层可以使用但不承诺稳定；
实验室（游戏、Godot、AS4）留在仓库中，用来推动语言的发展。
