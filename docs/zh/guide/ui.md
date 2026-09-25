---
source: guide/ui.md
source_hash: 238a9346dd15
---

# 一个应用，多种界面

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/ui)为准。
:::

用 UI Engine 的元素——`ui:window`、`ui:panel`、`ui:table`、`ui:form`……——编写的页面，
同时是一个网页、一个终端应用和一个桌面窗口。只有一个运行时：页面的查询、动作和规则
在服务器上运行一次，每个渲染器只负责**绘制**结果。

| 用它打开 | 你得到 |
|---|---|
| `quantum start` | 浏览器中的页面 |
| `quantum console` | 终端中的同一个页面（Textual） |
| `quantum desktop` | 原生窗口中的同一个页面（pywebview） |

页面的逻辑不会被翻译成另一种语言，所以你写一次的规则——一次校验、一次登录、一个查询——
在每种界面上的行为都相同。

## 第一个界面 {#a-first-screen}

在一个项目（一个带有 `quantum.config.yaml` 的文件夹）中保存为 `components/index.q`，
然后运行 `quantum start`：

```xml
<q:component name="Counter">
  <q:action name="add" method="POST">
    <q:set name="current" value="{session.clicks}" default="0" type="number" />
    <q:set name="session.clicks" value="{current + 1}" />
    <q:redirect url="/" />
  </q:action>

  <q:set name="clicks" value="{session.clicks}" default="0" />

  <ui:window title="Counter">
    <ui:panel title="Clicks">
      <ui:text>You clicked {clicks} times.</ui:text>
      <ui:button on-click="add" variant="primary">Add</ui:button>
    </ui:panel>
  </ui:window>
</q:component>
```

**Shows:** `Clicks` · `You clicked 0 times.` · `Add`

现在在同一个文件夹中运行 `quantum console`：终端里是同样的面板、文本和按钮。
在那里按下 **Add** 会提交同一个 `q:action`，并有自己的会话，就像浏览器一样。

`quantum desktop` 在窗口中打开它。它需要一个额外的包：

```bash
pip install "quantum-framework[desktop]"
quantum desktop            # the home page
quantum desktop /reports   # another page, --width/--height to size the window
```

窗口的标题是第一个 `ui:window` 的 `title`——与浏览器标签页和终端显示的标题相同。

## 事件就是动作 {#events-are-actions}

按钮或表单不会在浏览器中调用代码：它向页面的一个 `q:action` 提交数据。动作校验、完成工作
然后重定向，和 Quantum 中的任何表单一样（参见[动作与表单](/zh/guide/actions)）。

- `<ui:button on-click="save">` 提交到 `<q:action name="save">`。
- `with="id={t.id}, filter={filter}"` 为这次提交添加字段——行中的按钮就是这样说明它属于哪一行的。
- `<ui:form on-submit="create">` 提交它的字段：`<ui:input bind="title">` 就是字段 `title`。

不对应页面上任何动作的事件是一个错误，它会列出页面的动作——绝不会是一个悄悄什么都不做的按钮。

## 来自数据的表格和列表 {#tables-and-lists-from-data}

`source=` 接受一个列表——一个 `q:query` 或一个数组——并为每一项画一行。行的变量名由
`as=` 指定（表格默认为 `row`，列表默认为 `item`），和 `q:loop` 完全一样：

```xml
<q:component name="People">
  <q:action name="delete" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:redirect url="/" flash="Deleted person {id}" />
  </q:action>

  <q:set name="people" type="array"
         value='[{"id": 1, "name": "Ana", "age": 30}, {"id": 2, "name": "Bia", "age": 25}]' />

  <ui:window title="People">
    <ui:table source="{people}" as="p">
      <ui:column key="name" label="Name" />
      <ui:column key="age" label="Age" align="right" />
      <ui:column label="">
        <ui:button on-click="delete" with="id={p.id}" variant="danger">Delete {p.name}</ui:button>
      </ui:column>
    </ui:table>

    <ui:list source="{people}" as="p">
      <ui:item><ui:text>{p.name} is {p.age} years old</ui:text></ui:item>
    </ui:list>
  </ui:window>
</q:component>
```

**Shows:** `Name` · `Age` · `Ana` · `30` · `Delete Bia` · `Bia is 25 years old`

- `<ui:column key="name">` 显示这一行的该字段，并进行转义。
- 带内容的列会为每一行绘制一次内容——按钮、链接、徽章。
- 不是列表的 `source`，或这一行没有的 `key`，是一个会说明原因的错误（附带这一行的字段）——
  绝不会是一个空表格。

有数据库时，数据来源是一个查询。从这里开始的示例使用这个数据库（CI 根据这个代码块构建它）：

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    done INTEGER NOT NULL DEFAULT 0
);
INSERT INTO tasks (title, priority) VALUES ('Write the guide', 'high'), ('Review it', 'low');

CREATE TABLE posts (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL);
WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 12)
INSERT INTO posts (title) SELECT 'Post ' || i FROM n;
```

```xml
<q:component name="Tasks">
  <q:query name="tasks" datasource="db">
    SELECT id, title FROM tasks ORDER BY id
  </q:query>
  <ui:window title="Tasks">
    <ui:table source="{tasks}">
      <ui:column key="title" label="Task" />
    </ui:table>
  </ui:window>
</q:component>
```

**Shows:** `Task` · `Write the guide` · `Review it`

## 长列表的分页 {#pages-of-a-long-list}

带 `paginate="true"` 的查询返回一页；页码是 URL 中的 `?page=`。`<ui:pager>` 画出链接：

```xml
<q:component name="Blog">
  <q:query name="posts" datasource="db" paginate="true" page_size="10">
    SELECT title FROM posts ORDER BY id DESC
  </q:query>
  <ui:window title="Blog">
    <ui:list source="{posts}" as="p"><ui:item><ui:text>{p.title}</ui:text></ui:item></ui:list>
    <ui:pager for="posts" />
  </ui:window>
</q:component>
```

**Shows:** `Post 12` · `Post 3`

12 篇文章分成两页：第一页显示从 `Post 12` 到 `Post 3`。

- 上一页、当前页附近的页码（第一页和最后一页总会显示，跳过的地方显示 `…`）、下一页。
  到两端时，上一页/下一页不是链接；只有一页时什么都不画。
- 链接会保留 URL 的其他参数：在 `/?tag=news&page=2` 上，它们指向 `/?tag=news&page=3`。
- `?page=abc` 或 `?page=-1` 就是第 1 页，从不报错。
- `window="1"` 显示更少的页码；当一个页面有两个分页列表时用 `param="p"`
  （同时在查询上写 `page="{query.p}"`）。

`projects/blog` 的首页就是这样分页的。

## 边输入边搜索 {#search-as-you-type}

```xml
<q:component name="Search">
  <q:set name="term" value="{query.q}" default="" />
  <q:query name="found" datasource="db">
    SELECT title FROM posts WHERE title LIKE :p
    <q:param name="p" value="%{term}%" type="string" />
  </q:query>
  <ui:window title="Search">
    <ui:input bind="q" search="results" placeholder="Search" />
    <ui:vbox id="results">
      <ui:list source="{found}" as="a"><ui:item><ui:text>{a.title}</ui:text></ui:item></ui:list>
    </ui:vbox>
  </ui:window>
</q:component>
```

**Shows:** `Post 1` · `Post 12`

- 每次输入停顿（`delay`，默认 300 毫秒）都会用 `?q=…` 请求同一个页面，并只替换
  `#results`——搜索由页面自己的查询完成。URL 也随之更新，所以结果可以分享或刷新。
- 它底层就是一个普通的 GET 表单：没有 JavaScript 时，按 Enter 搜索。
- URL 的其他参数会保留；`page` 会被去掉，所以新的搜索从 `<ui:pager>` 的第 1 页开始。
- 在终端中也一样：停顿之后重新请求页面，字段保持焦点。
- 页面上不存在的目标是一个错误——绝不会是一个什么都不替换的字段。

`projects/blog` 就是这样搜索的（`components/search.q`）。

## 会自己排序和编辑的表格 {#a-table-that-sorts-and-edits-itself}

```xml
<q:component name="Sheet">
  <q:query name="tasks" datasource="db" sortable="true">
    SELECT id, title, priority FROM tasks
  </q:query>
  <ui:window title="Tasks">
    <ui:table source="{tasks}" sort="true" edit="tasks" datasource="db">
      <ui:column key="title" label="Title" />
      <ui:column key="priority" label="Priority" />
    </ui:table>
  </ui:window>
</q:component>
```

**Shows:** `Title` · `Priority` · `low` · `medium` · `high`

每个单元格都是一个小表单：标题在它们的字段里，每个优先级是一个带有 `CHECK` 列表的下拉框。

- `sort="true"`：每个表头都是一个链接，按 `?sort=` 和 `?dir=` **在 SQL 中**对查询排序
  （查询上的 `sortable="true"`）——所以它可以和 `<ui:pager>` 一起使用。URL 中出现的、
  查询不返回的列会被忽略。
- `edit="tasks"`：该数据表每个显示的列都会在它的单元格中变成一个小表单（按 Enter 或 ✓ 保存）。
  你不用写任何动作：服务器只接受这个页面声明的数据表和列，运行页面的守卫，用数据表结构中
  该列的规则（NOT NULL、`CHECK … IN`、类型）校验值，并按主键更新一行。被拒绝的值会带着
  错误回到它的单元格。列上的 `edit="false"` 让它保持只读。
- 行中必须包含主键（`SELECT id, …`）。
- 它所做的事情会像任何动作一样显示在 [`/_dev`](/tools/dev-panel) 中。

`projects/tarefas` 在 `/planilha` 有一个这样的表格。

## 打开时带有值的表单 {#forms-that-open-with-values}

字段从页面获取初始值，所以同一个表单既能创建也能编辑：

```xml
<q:component name="Profile">
  <q:action name="save" method="POST">
    <q:param name="name" required="true" minlength="2" />
    <q:param name="notices" default="off" />
    <q:param name="plan" default="free" />
    <q:set name="session.name" value="{name}" />
    <q:redirect url="/" flash="Saved: {name}, notices {notices}, plan {plan}" />
  </q:action>

  <q:set name="name" value="{session.name}" default="Ana" />

  <ui:window title="Profile">
    <q:if condition="flash">
      <ui:alert variant="success">{flash}</ui:alert>
    </q:if>
    <ui:form on-submit="save">
      <ui:formitem label="Name">
        <ui:input bind="name" value="{name}" />
      </ui:formitem>
      <ui:checkbox bind="notices" label="Receive notices" checked="true" />
      <ui:radio bind="plan" options="free,pro" value="pro" />
      <ui:select bind="color" options="blue,green" value="green" />
      <ui:button variant="primary">Save</ui:button>
    </ui:form>
  </ui:window>
</q:component>
```

**Shows:** `Name` · `Receive notices` · `free` · `pro` · `Save`

`default=` 为第一次访问提供值（会话中还没有 `name`）。

- `ui:input`、`ui:select` 和 `ui:radio` 上用 `value=`；`ui:checkbox` 和 `ui:switch`
  上用 `checked=`（`true`，或一个表达式）。
- 勾选的复选框以 `on` 发送；没有勾选的**不会发送**——浏览器就是这样做的。所以动作写的是
  `<q:param name="notices" default="off">`。

## 知道动作规则的表单 {#forms-that-know-the-action-s-rules}

表单从它所提交的动作的 `q:param` 中获取每个字段的规则，所以你只需写一次：

```xml
<q:component name="SignUp">
  <q:action name="signUp" method="POST">
    <q:param name="name" required="true" minlength="3" />
    <q:param name="age" type="integer" min="18" />
    <q:param name="plan" enum="free,pro" default="free" />
    <q:redirect url="/" flash="Signed up: {name}" />
  </q:action>

  <ui:window title="Sign up">
    <ui:form on-submit="signUp">
      <ui:formitem label="Name"><ui:input bind="name" /></ui:formitem>
      <ui:formitem label="Age"><ui:input bind="age" /></ui:formitem>
      <ui:select bind="plan" />
      <ui:button>Sign up</ui:button>
    </ui:form>
  </ui:window>
</q:component>
```

**Shows:** `Name` · `Age` · `free` · `pro` · `Sign up`

- `name` 得到 `required minlength="3"`，`age` 得到 `type="number" min="18"`，
  下拉框得到 `enum` 作为选项——看一下页面源代码。浏览器会在提交之前检查它们。
- 服务器仍然会校验每个字段。当它拒绝时，页面会带着提交的值返回，并且**每个错误都在它的
  字段旁边**（终端中也是如此）。密码永远不会被带回。
- 你在字段上写的属性优先；`<ui:form rules="off">` 会关闭这一功能。
- `pattern` 只有在锚定时（`^…$`）才会交给浏览器：浏览器匹配整个值，服务器是搜索。

## 根据数据表生成的表单 {#forms-from-a-table}

当一个动作写入一张数据表时，它可以从数据表本身获取规则——也就是你已经在迁移中写好的
数据表结构（上面的 `tasks` 表）：

```xml
<q:component name="EditTask">
  <q:action name="save" method="POST" table="tasks" datasource="db" columns="title,priority">
    <q:param name="id" type="integer" required="true" />
    <q:query name="updated" datasource="db">
      UPDATE tasks SET title = :title, priority = :priority WHERE id = :id
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Saved: {title}" />
  </q:action>

  <q:query name="task" datasource="db">SELECT id, title, priority FROM tasks WHERE id = 1</q:query>

  <ui:window title="Edit task">
    <ui:form on-submit="save" values="{task}" submit="Save" />
  </ui:window>
</q:component>
```

**Shows:** `Title` · `Priority` · `low` · `high` · `Save`

- `title` 是 `NOT NULL` → 必填；`priority` 有 `CHECK … IN` → 一个带这些选项的下拉框，
  服务器会拒绝其他任何值。
- 表单没有自己的字段，所以它为每一列画一个字段——标签取自名字（`author_id` → "Author"），
  `BOOLEAN` 是复选框，外键是一个用被引用数据表的行填充的下拉框。`values="{task}"`
  让它打开时带着一行的值：一行代码就是一个编辑表单。
- `columns=` 选择列并确定顺序（默认：除主键外的所有列）。你在动作中写的 `q:param`
  优先于该列的规则。
- 可以为空的列留空时，以 `None` 到达动作；外键必须对应一个存在的行。
- 数据表结构从数据库读取，数据库文件变化时会重新读取——在迁移中添加一列，表单就会有这一列。
  `quantum check` 会报告不存在的数据表或列。

`projects/tarefas` 就是这样编辑任务的（`components/tarefa/[id].q`）。

## 自适应的布局 {#layout-that-adapts}

布局是声明式的，有三个断点：`sm`（640 px）、`md`（768 px）和 `lg`（1024 px）。
在终端中它们以列数计算（80、96 和 128）。

```xml
<q:component name="Dashboard">
  <ui:window title="Dashboard">
    <ui:hbox stack-below="md" gap="md">
      <ui:vbox width="260"><ui:text>Menu</ui:text></ui:vbox>
      <ui:vbox grow="true"><ui:text>Content</ui:text></ui:vbox>
    </ui:hbox>
    <ui:grid columns="1 sm:2 lg:3">
      <ui:text>One</ui:text><ui:text>Two</ui:text><ui:text>Three</ui:text>
    </ui:grid>
    <ui:text hide-below="md">Only on wide screens</ui:text>
  </ui:window>
</q:component>
```

**Shows:** `Menu` · `Content` · `One` · `Three`

- `stack-below="md"` 让 `ui:hbox` 的子元素在宽度小于 768 px 时上下排列，它们的固定宽度不再生效。
- `grow="true"` 占用这一行剩余的空间。
- `ui:grid columns="1 sm:2 lg:3"`：一列，从 `sm` 起两列，从 `lg` 起三列。
- `hide-below` / `hide-above` 在断点的一侧隐藏一个元素。

## 核心层组件集 {#the-core-set}

这些元素由浏览器、终端和桌面窗口以相同的含义绘制，并且同一个测试脚本——查看、填写、勾选、
选择、点击——无需修改就能在真实浏览器和终端中运行：

| 类别 | 元素 |
|---|---|
| 布局 | `window`、`hbox`、`vbox`、`grid`、`panel`、`section`、`scrollbox`、`spacer`、`rule`、`header`、`footer`、`card`（`card-header`、`card-body`、`card-footer`）、`tabpanel` / `tab` |
| 内容 | `text`、`badge`、`alert`、`link`、`image`、`progress` |
| 数据 | `table` / `column`、`list` / `item` |
| 表单 | `form`、`formitem`、`input`、`checkbox`、`switch`、`radio`、`select` / `option`、`button` |
| 数据功能 | `pager`（查询的分页）、`history`（一行的变更）、`stream`（边生成边显示的 AI 回答） |

其他任何 `ui:*` 元素——图表、模态框、提示框、日期选择器、菜单……——只在浏览器中工作，属于
**实验层**（参见 [UI 标签参考](/reference/ui)）。在终端中，这样的元素会显示
`[ui:chart is not drawn in the console]`，而不是在原处显示别的东西。

直接写在容器中的文本就是内容：`<ui:card-header>Summary</ui:card-header>`。
`ui:*` 元素之间可以有普通 HTML；终端会显示它的文本。

## 独立构建 {#standalone-builds}

`<q:application type="ui">` 配合 `quantum run app.q --target html`（一个 HTML 文件）或
`--target textual`（一个 Python 文件）**只绘制布局**：这些文件中没有运行时，所以其中的
`q:set`、`q:function` 或任何其他命令都是一个指向这里的错误。要给界面加上逻辑，请把它写成页面。

`--target mobile`（React Native）属于**实验室**：它自行把逻辑翻译成 JavaScript，没有稳定性承诺。
手机不属于 1.0 的范围。旧的 `--target desktop` 已移除；由 `quantum desktop` 取代。
