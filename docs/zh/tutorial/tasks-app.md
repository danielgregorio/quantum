---
source: tutorial/tasks-app.md
source_hash: 0b96f8323cd6
---

# 构建任务应用

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/tutorial/tasks-app)为准。
:::

本教程从一个空文件夹开始构建一个完整的应用：一个任务列表，带有经过校验的表单、完成和删除按钮、一个筛选器、一个可以就地编辑的可排序表格、一个记录每次修改历史的编辑页面，以及一个测试套件。它是
[`projects/tarefas`](https://github.com/danielgregorio/quantum/tree/main/projects/tarefas)
的英文版孪生应用——Quantum 自己的 CI 运行的应用之一——最终得到的代码与它相同。本页的代码与英文原文一样保持英文。

你不需要写 JavaScript，也不需要写 Python。每一步都是一个完整、可运行的应用，本页的代码由 Quantum 的测试套件按原样运行（`tests/docs/test_tutorial_tasks_app.py`）：你读到的就是运行的。

## 1. 安装并创建项目

你需要 Python 3.12 或更新版本。

```bash
pip install quantum-framework
mkdir tasks && cd tasks
```

一个应用就是一个带有 `quantum.config.yaml` 的文件夹。这个配置说明页面和数据库迁移放在哪里，并声明一个名为 `db` 的 SQLite 数据库。

保存为 `quantum.config.yaml`：

```yaml
server:
  port: 8080
  host: 127.0.0.1

paths:
  components: ./components
  migrations: ./migrations

datasources:
  db:
    driver: sqlite
    database: ./data/tasks.db
```

数据表来自迁移：`migrations/` 中的普通 SQL 文件，按顺序应用。`CHECK` 约束在后面很重要：Quantum 会读取它，并在编辑表单和表格编辑器中拒绝列表之外的优先级，而你无需再写一遍这条规则。

保存为 `migrations/V001_tasks.sql`：

```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    done INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

INSERT INTO tasks (title, priority) VALUES
    ('Read the Quantum guide', 'high'),
    ('Write the first page', 'medium');
INSERT INTO tasks (title, priority, done) VALUES
    ('Install Quantum', 'low', 1);
```

创建数据库（它位于 `data/tasks.db`）：

```bash
quantum migrate up
```

### 第一个页面

`components/` 中的一个文件就是一个页面：`components/index.q` 响应 `/`。两个查询读取数据库，`ui:*` 标签排列结果：一个显示计数的侧边面板，以及列表，每个任务一行。

保存为 `components/index.q`：

```xml
<q:component name="Tasks">
  <q:query name="summary" datasource="db">
    SELECT COUNT(*) AS total, COALESCE(SUM(done = 0), 0) AS open, COALESCE(SUM(done), 0) AS finished
    FROM tasks
  </q:query>

  <q:query name="tasks" datasource="db">
    SELECT id, title, priority, done FROM tasks
    ORDER BY done, CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id DESC
  </q:query>

  <ui:window title="Tasks">
    <ui:hbox gap="lg" padding="lg" stack-below="md" id="main">

      <ui:vbox width="260" gap="md" id="side">
        <ui:panel title="Summary">
          <ui:vbox gap="sm">
            <ui:text>Total: {summary.total}</ui:text>
            <ui:text>Open: {summary.open}</ui:text>
            <ui:text>Done: {summary.finished}</ui:text>
          </ui:vbox>
        </ui:panel>
      </ui:vbox>

      <ui:vbox gap="md" grow="true" id="content">
        <q:loop query="tasks">
          <ui:hbox gap="sm" align="center">
            <ui:badge variant="secondary">{tasks.priority}</ui:badge>
            <ui:text>{tasks.title}</ui:text>
          </ui:hbox>
        </q:loop>
      </ui:vbox>

    </ui:hbox>
  </ui:window>
</q:component>
```

```bash
quantum start
```

打开 http://127.0.0.1:8080：三个任务和它们的计数。在窄屏上，面板会堆叠在列表上方（[UI](/guide/ui)）。

## 2. 创建任务，并进行校验

表单把字段提交给一个 `q:action`。动作的 `q:param` 就是它的规则：`title` 是必填的，长度在 3 到 200 个字符之间，`priority` 是三个值之一。违反规则的值永远不会到达 SQL：页面会带着字段旁的消息和已输入的内容返回（[Actions and forms](/guide/actions)）。

插入之后，`q:redirect` 带着一条提示消息（flash）把浏览器送回列表，由 `q:if condition="flash"` 块显示一次。表单根据它提交到的动作来绘制字段：`ui:input bind="title"` 会成为一个必填的文本字段，带有取自规则的 `minlength="3"`。

保存为 `components/index.q`：

```xml
<q:component name="Tasks">
  <q:action name="create" method="POST">
    <q:param name="title" required="true" minlength="3" maxlength="200" />
    <q:param name="priority" default="medium" enum="low,medium,high" />
    <q:query name="added" datasource="db">
      INSERT INTO tasks (title, priority) VALUES (:title, :priority)
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Created: {title}" />
  </q:action>

  <q:query name="summary" datasource="db">
    SELECT COUNT(*) AS total, COALESCE(SUM(done = 0), 0) AS open, COALESCE(SUM(done), 0) AS finished
    FROM tasks
  </q:query>

  <q:query name="tasks" datasource="db">
    SELECT id, title, priority, done FROM tasks
    ORDER BY done, CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id DESC
  </q:query>

  <ui:window title="Tasks">
    <ui:hbox gap="lg" padding="lg" stack-below="md" id="main">

      <ui:vbox width="260" gap="md" id="side">
        <ui:panel title="Summary">
          <ui:vbox gap="sm">
            <ui:text>Total: {summary.total}</ui:text>
            <ui:text>Open: {summary.open}</ui:text>
            <ui:text>Done: {summary.finished}</ui:text>
          </ui:vbox>
        </ui:panel>
      </ui:vbox>

      <ui:vbox gap="md" grow="true" id="content">
        <q:if condition="flash">
          <ui:alert variant="success">{flash}</ui:alert>
        </q:if>

        <ui:form on-submit="create">
          <ui:hbox gap="sm">
            <ui:input bind="title" placeholder="What needs to be done?" required="true" grow="true" />
            <ui:select bind="priority" options="medium,high,low" />
            <ui:button variant="primary">Create</ui:button>
          </ui:hbox>
        </ui:form>

        <q:loop query="tasks">
          <ui:hbox gap="sm" align="center">
            <ui:badge variant="secondary">{tasks.priority}</ui:badge>
            <ui:text>{tasks.title}</ui:text>
          </ui:hbox>
        </q:loop>
      </ui:vbox>

    </ui:hbox>
  </ui:window>
</q:component>
```

试试空标题，再试试只有一个字母的标题：表单会在字段旁边说明哪里有问题。

## 3. 完成和删除

再加两个动作，分别由行中的一个按钮调用。`with="id={tasks.id}"` 发送该行的 id，`q:param` 上的 `type="integer"` 会在 `UPDATE` 或 `DELETE` 运行之前拒绝任何不是数字的值。

保存为 `components/index.q`：

```xml
<q:component name="Tasks">
  <q:action name="create" method="POST">
    <q:param name="title" required="true" minlength="3" maxlength="200" />
    <q:param name="priority" default="medium" enum="low,medium,high" />
    <q:query name="added" datasource="db">
      INSERT INTO tasks (title, priority) VALUES (:title, :priority)
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Created: {title}" />
  </q:action>

  <q:action name="toggle" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:query name="toggled" datasource="db">
      UPDATE tasks SET done = 1 - done WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" />
  </q:action>

  <q:action name="delete" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:query name="removed" datasource="db">
      DELETE FROM tasks WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Task deleted." />
  </q:action>

  <q:query name="summary" datasource="db">
    SELECT COUNT(*) AS total, COALESCE(SUM(done = 0), 0) AS open, COALESCE(SUM(done), 0) AS finished
    FROM tasks
  </q:query>

  <q:query name="tasks" datasource="db">
    SELECT id, title, priority, done FROM tasks
    ORDER BY done, CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id DESC
  </q:query>

  <ui:window title="Tasks">
    <ui:hbox gap="lg" padding="lg" stack-below="md" id="main">

      <ui:vbox width="260" gap="md" id="side">
        <ui:panel title="Summary">
          <ui:vbox gap="sm">
            <ui:text>Total: {summary.total}</ui:text>
            <ui:text>Open: {summary.open}</ui:text>
            <ui:text>Done: {summary.finished}</ui:text>
          </ui:vbox>
        </ui:panel>
      </ui:vbox>

      <ui:vbox gap="md" grow="true" id="content">
        <q:if condition="flash">
          <ui:alert variant="success">{flash}</ui:alert>
        </q:if>

        <ui:form on-submit="create">
          <ui:hbox gap="sm">
            <ui:input bind="title" placeholder="What needs to be done?" required="true" grow="true" />
            <ui:select bind="priority" options="medium,high,low" />
            <ui:button variant="primary">Create</ui:button>
          </ui:hbox>
        </ui:form>

        <q:loop query="tasks">
          <ui:hbox gap="sm" align="center">
            <ui:badge variant="secondary">{tasks.priority}</ui:badge>
            <ui:text>{tasks.title}</ui:text>
            <ui:button on-click="toggle" with="id={tasks.id}">{'Reopen' if tasks.done else 'Finish'}</ui:button>
            <ui:button on-click="delete" with="id={tasks.id}" variant="danger">Delete</ui:button>
          </ui:hbox>
        </q:loop>
      </ui:vbox>

    </ui:hbox>
  </ui:window>
</q:component>
```

## 4. 筛选列表

页面用 `q:set` 从地址中读取 `?show=`，并把它作为参数交给查询，绝不会拼接进 SQL。侧边面板得到三个链接，`toggle` 动作在重定向时保留当前筛选，空列表会明确说明。

保存为 `components/index.q`：

```xml
<q:component name="Tasks">
  <q:action name="create" method="POST">
    <q:param name="title" required="true" minlength="3" maxlength="200" />
    <q:param name="priority" default="medium" enum="low,medium,high" />
    <q:query name="added" datasource="db">
      INSERT INTO tasks (title, priority) VALUES (:title, :priority)
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Created: {title}" />
  </q:action>

  <q:action name="toggle" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:param name="show" default="all" enum="all,open,done" />
    <q:query name="toggled" datasource="db">
      UPDATE tasks SET done = 1 - done WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/?show={show}" />
  </q:action>

  <q:action name="delete" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:query name="removed" datasource="db">
      DELETE FROM tasks WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Task deleted." />
  </q:action>

  <q:set name="show" value="{query.show}" default="all" />

  <q:query name="summary" datasource="db">
    SELECT COUNT(*) AS total, COALESCE(SUM(done = 0), 0) AS open, COALESCE(SUM(done), 0) AS finished
    FROM tasks
  </q:query>

  <q:query name="tasks" datasource="db">
    SELECT id, title, priority, done FROM tasks
    WHERE :show = 'all' OR (:show = 'open' AND done = 0) OR (:show = 'done' AND done = 1)
    ORDER BY done, CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id DESC
    <q:param name="show" value="{show}" type="string" />
  </q:query>

  <ui:window title="Tasks">
    <ui:hbox gap="lg" padding="lg" stack-below="md" id="main">

      <ui:vbox width="260" gap="md" id="side">
        <ui:panel title="Summary">
          <ui:vbox gap="sm">
            <ui:text>Total: {summary.total}</ui:text>
            <ui:text>Open: {summary.open}</ui:text>
            <ui:text>Done: {summary.finished}</ui:text>
          </ui:vbox>
        </ui:panel>
        <ui:panel title="Show">
          <ui:vbox gap="sm">
            <ui:link to="/?show=all">All</ui:link>
            <ui:link to="/?show=open">Open</ui:link>
            <ui:link to="/?show=done">Done</ui:link>
          </ui:vbox>
        </ui:panel>
      </ui:vbox>

      <ui:vbox gap="md" grow="true" id="content">
        <q:if condition="flash">
          <ui:alert variant="success">{flash}</ui:alert>
        </q:if>

        <ui:form on-submit="create">
          <ui:hbox gap="sm">
            <ui:input bind="title" placeholder="What needs to be done?" required="true" grow="true" />
            <ui:select bind="priority" options="medium,high,low" />
            <ui:button variant="primary">Create</ui:button>
          </ui:hbox>
        </ui:form>

        <q:loop query="tasks">
          <ui:hbox gap="sm" align="center">
            <ui:badge variant="secondary">{tasks.priority}</ui:badge>
            <ui:text>{tasks.title}</ui:text>
            <ui:button on-click="toggle" with="id={tasks.id}, show={show}">{'Reopen' if tasks.done else 'Finish'}</ui:button>
            <ui:button on-click="delete" with="id={tasks.id}" variant="danger">Delete</ui:button>
          </ui:hbox>
        </q:loop>

        <q:if condition="tasks_result.recordCount == 0">
          <ui:text>No tasks here.</ui:text>
        </q:if>
      </ui:vbox>

    </ui:hbox>
  </ui:window>
</q:component>
```

`http://127.0.0.1:8080/?show=done` 现在只列出已完成的任务。

## 5. 能自己排序和编辑的表格

第二个页面 `components/sheet.q` 响应 `/sheet`。查询是 `sortable` 并分页的，带 `edit="tasks"` 的 `ui:table` 把每个单元格变成一个小表单，保存一行中的一列。你不需要写任何动作：表的结构就是规则，因此 `CHECK` 列表之外的优先级会被拒绝，单元格会说明原因（[UI](/guide/ui)）。

保存为 `components/sheet.q`：

```xml
<q:component name="Sheet">
  <q:query name="tasks" datasource="db" sortable="true" paginate="true" page_size="20">
    SELECT id, title, priority, done FROM tasks ORDER BY id
  </q:query>

  <ui:window title="Task sheet">
    <ui:vbox gap="md" padding="lg">
      <ui:hbox gap="md">
        <ui:link to="/">Back</ui:link>
        <ui:text>Click a header to sort; edit a cell and confirm with ✓ (or Enter).</ui:text>
      </ui:hbox>
      <q:if condition="flash">
        <ui:alert variant="{flashType == 'error' and 'danger' or 'success'}">{flash}</ui:alert>
      </q:if>
      <ui:table source="{tasks}" sort="true" edit="tasks" datasource="db">
        <ui:column key="title" label="Title" />
        <ui:column key="priority" label="Priority" />
        <ui:column key="done" label="Done" />
      </ui:table>
      <ui:pager for="tasks" />
    </ui:vbox>
  </ui:window>
</q:component>
```

从侧边面板链接到它：

保存为 `components/index.q`：

```xml
<q:component name="Tasks">
  <q:action name="create" method="POST">
    <q:param name="title" required="true" minlength="3" maxlength="200" />
    <q:param name="priority" default="medium" enum="low,medium,high" />
    <q:query name="added" datasource="db">
      INSERT INTO tasks (title, priority) VALUES (:title, :priority)
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Created: {title}" />
  </q:action>

  <q:action name="toggle" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:param name="show" default="all" enum="all,open,done" />
    <q:query name="toggled" datasource="db">
      UPDATE tasks SET done = 1 - done WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/?show={show}" />
  </q:action>

  <q:action name="delete" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:query name="removed" datasource="db">
      DELETE FROM tasks WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Task deleted." />
  </q:action>

  <q:set name="show" value="{query.show}" default="all" />

  <q:query name="summary" datasource="db">
    SELECT COUNT(*) AS total, COALESCE(SUM(done = 0), 0) AS open, COALESCE(SUM(done), 0) AS finished
    FROM tasks
  </q:query>

  <q:query name="tasks" datasource="db">
    SELECT id, title, priority, done FROM tasks
    WHERE :show = 'all' OR (:show = 'open' AND done = 0) OR (:show = 'done' AND done = 1)
    ORDER BY done, CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id DESC
    <q:param name="show" value="{show}" type="string" />
  </q:query>

  <ui:window title="Tasks">
    <ui:hbox gap="lg" padding="lg" stack-below="md" id="main">

      <ui:vbox width="260" gap="md" id="side">
        <ui:panel title="Summary">
          <ui:vbox gap="sm">
            <ui:text>Total: {summary.total}</ui:text>
            <ui:text>Open: {summary.open}</ui:text>
            <ui:text>Done: {summary.finished}</ui:text>
          </ui:vbox>
        </ui:panel>
        <ui:panel title="Show">
          <ui:vbox gap="sm">
            <ui:link to="/?show=all">All</ui:link>
            <ui:link to="/?show=open">Open</ui:link>
            <ui:link to="/?show=done">Done</ui:link>
            <ui:link to="/sheet">Sheet</ui:link>
          </ui:vbox>
        </ui:panel>
      </ui:vbox>

      <ui:vbox gap="md" grow="true" id="content">
        <q:if condition="flash">
          <ui:alert variant="success">{flash}</ui:alert>
        </q:if>

        <ui:form on-submit="create">
          <ui:hbox gap="sm">
            <ui:input bind="title" placeholder="What needs to be done?" required="true" grow="true" />
            <ui:select bind="priority" options="medium,high,low" />
            <ui:button variant="primary">Create</ui:button>
          </ui:hbox>
        </ui:form>

        <q:loop query="tasks">
          <ui:hbox gap="sm" align="center">
            <ui:badge variant="secondary">{tasks.priority}</ui:badge>
            <ui:text>{tasks.title}</ui:text>
            <ui:button on-click="toggle" with="id={tasks.id}, show={show}">{'Reopen' if tasks.done else 'Finish'}</ui:button>
            <ui:button on-click="delete" with="id={tasks.id}" variant="danger">Delete</ui:button>
          </ui:hbox>
        </q:loop>

        <q:if condition="tasks_result.recordCount == 0">
          <ui:text>No tasks here.</ui:text>
        </q:if>
      </ui:vbox>

    </ui:hbox>
  </ui:window>
</q:component>
```

## 6. 带历史记录的编辑页面

为数据库打开修改历史：动作的每一次写入都会被记录，包括是谁做的、改了什么。

保存为 `quantum.config.yaml`：

```yaml
server:
  port: 8080
  host: 127.0.0.1

paths:
  components: ./components
  migrations: ./migrations

datasources:
  db:
    driver: sqlite
    database: ./data/tasks.db
    history: true          # every change made by an action is recorded
```

编辑页面是 `components/task/[id].q`：文件名中的 `[id]` 响应 `/task/1`、`/task/2`……并给页面一个 `id` 变量。

它的动作指定一张表和若干列，而不是声明 `q:param`，所以规则来自表结构（`title` 是 `NOT NULL`，`priority` 在 `CHECK` 列表中）。没有自己字段的 `ui:form` 会为每一列绘制一个字段并填入任务的值，`ui:history` 列出对这个任务做过的每一次修改。

保存为 `components/task/[id].q`：

```xml
<q:component name="EditTask">
  <q:action name="save" method="POST" table="tasks" datasource="db" columns="title,priority">
    <q:query name="saved" datasource="db">
      UPDATE tasks SET title = :title, priority = :priority WHERE id = :id
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Saved: {title}" />
  </q:action>

  <q:query name="task" datasource="db">
    SELECT id, title, priority FROM tasks WHERE id = :id
    <q:param name="id" value="{id}" type="integer" />
  </q:query>

  <ui:window title="Edit task">
    <ui:vbox gap="md" padding="lg">
      <ui:link to="/">Back</ui:link>
      <q:if condition="task_result.recordCount == 0">
        <ui:alert variant="danger">That task does not exist.</ui:alert>
      </q:if>
      <q:else>
        <ui:form on-submit="save" values="{task}" submit="Save" />
        <ui:section title="History">
          <ui:history table="tasks" key="{id}" datasource="db" />
        </ui:section>
      </q:else>
    </ui:vbox>
  </ui:window>
</q:component>
```

再在每一行加一个 *Edit* 链接：

保存为 `components/index.q`：

```xml
<q:component name="Tasks">
  <q:action name="create" method="POST">
    <q:param name="title" required="true" minlength="3" maxlength="200" />
    <q:param name="priority" default="medium" enum="low,medium,high" />
    <q:query name="added" datasource="db">
      INSERT INTO tasks (title, priority) VALUES (:title, :priority)
      <q:param name="title" value="{title}" type="string" />
      <q:param name="priority" value="{priority}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Created: {title}" />
  </q:action>

  <q:action name="toggle" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:param name="show" default="all" enum="all,open,done" />
    <q:query name="toggled" datasource="db">
      UPDATE tasks SET done = 1 - done WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/?show={show}" />
  </q:action>

  <q:action name="delete" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:query name="removed" datasource="db">
      DELETE FROM tasks WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Task deleted." />
  </q:action>

  <q:set name="show" value="{query.show}" default="all" />

  <q:query name="summary" datasource="db">
    SELECT COUNT(*) AS total, COALESCE(SUM(done = 0), 0) AS open, COALESCE(SUM(done), 0) AS finished
    FROM tasks
  </q:query>

  <q:query name="tasks" datasource="db">
    SELECT id, title, priority, done FROM tasks
    WHERE :show = 'all' OR (:show = 'open' AND done = 0) OR (:show = 'done' AND done = 1)
    ORDER BY done, CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, id DESC
    <q:param name="show" value="{show}" type="string" />
  </q:query>

  <ui:window title="Tasks">
    <ui:hbox gap="lg" padding="lg" stack-below="md" id="main">

      <ui:vbox width="260" gap="md" id="side">
        <ui:panel title="Summary">
          <ui:vbox gap="sm">
            <ui:text>Total: {summary.total}</ui:text>
            <ui:text>Open: {summary.open}</ui:text>
            <ui:text>Done: {summary.finished}</ui:text>
          </ui:vbox>
        </ui:panel>
        <ui:panel title="Show">
          <ui:vbox gap="sm">
            <ui:link to="/?show=all">All</ui:link>
            <ui:link to="/?show=open">Open</ui:link>
            <ui:link to="/?show=done">Done</ui:link>
            <ui:link to="/sheet">Sheet</ui:link>
          </ui:vbox>
        </ui:panel>
      </ui:vbox>

      <ui:vbox gap="md" grow="true" id="content">
        <q:if condition="flash">
          <ui:alert variant="success">{flash}</ui:alert>
        </q:if>

        <ui:form on-submit="create">
          <ui:hbox gap="sm">
            <ui:input bind="title" placeholder="What needs to be done?" required="true" grow="true" />
            <ui:select bind="priority" options="medium,high,low" />
            <ui:button variant="primary">Create</ui:button>
          </ui:hbox>
        </ui:form>

        <q:loop query="tasks">
          <ui:hbox gap="sm" align="center">
            <ui:badge variant="secondary">{tasks.priority}</ui:badge>
            <ui:text>{tasks.title}</ui:text>
            <ui:link to="/task/{tasks.id}">Edit</ui:link>
            <ui:button on-click="toggle" with="id={tasks.id}, show={show}">{'Reopen' if tasks.done else 'Finish'}</ui:button>
            <ui:button on-click="delete" with="id={tasks.id}" variant="danger">Delete</ui:button>
          </ui:hbox>
        </q:loop>

        <q:if condition="tasks_result.recordCount == 0">
          <ui:text>No tasks here.</ui:text>
        </q:if>
      </ui:vbox>

    </ui:hbox>
  </ui:window>
</q:component>
```

这就是整个应用：151 行 `.q`，13 行 SQL，0 行 JavaScript。

## 7. 测试它

Quantum 应用用它自己的语言来测试（[Testing an App](/guide/testing)）。每个 `q:test` 都从由你的迁移构建的全新数据库开始，访问页面、提交动作，并检查重定向、提示消息、字段上的错误、表中的行以及历史记录。

保存为 `tests/tasks.test.q`：

```xml
<q:test name="the list shows the summary and the tasks" page="/">
  <test:visit />
  <test:expect text="Total: 3" />
  <test:expect text="Open: 2" />
  <test:expect text="Done: 1" />
  <test:expect text="Write the first page" />
</q:test>

<q:test name="create a task" page="/">
  <test:submit action="create" title="Test the UI" priority="high" />
  <test:expect status="302" redirect="/" flash="Created: Test the UI" />
  <test:expect table="tasks" count="1" where="title = 'Test the UI' AND priority = 'high'" />
  <test:expect text="Total: 4" />
</q:test>

<q:test name="a title that is too short is refused on its field" page="/">
  <test:submit action="create" title="x" />
  <test:expect redirect="/" />
  <test:expect error="title" />
  <test:expect text="at least 3 characters" />
  <test:expect table="tasks" count="3" />
</q:test>

<q:test name="a priority outside the list is refused" page="/">
  <test:submit action="create" title="With a wrong priority" priority="urgent" />
  <test:expect error="priority" />
  <test:expect table="tasks" count="0" where="title = 'With a wrong priority'" />
</q:test>

<q:test name="finish a task and show the open ones" page="/">
  <test:given table="tasks" title="Buy bread" />
  <test:expect table="tasks" count="1" where="title = 'Buy bread' AND done = 0" />
  <test:submit action="toggle" id="4" show="open" />
  <test:expect redirect="/?show=open" />
  <test:expect table="tasks" count="1" where="id = 4 AND done = 1" />
  <test:expect no-text="Buy bread" />
  <test:expect text="Read the Quantum guide" />
</q:test>

<q:test name="delete a task" page="/">
  <test:submit action="delete" id="2" />
  <test:expect redirect="/" flash="Task deleted." />
  <test:expect table="tasks" count="0" where="id = 2" />
  <test:expect text="Total: 2" />
</q:test>

<q:test name="the page runs a fixed number of queries" page="/">
  <test:given table="tasks" />
  <test:given table="tasks" />
  <test:visit />
  <test:expect queries="2" />
  <test:expect var="show" value="all" />
</q:test>

<q:test name="the filter comes from the query string" page="/">
  <test:visit show="done" />
  <test:expect var="show" value="done" />
  <test:expect text="Install Quantum" />
  <test:expect no-text="Read the Quantum guide" />
</q:test>
```

测试也可以放在它所测试的页面旁边：

保存为 `components/sheet.test.q`：

```xml
<q:test name="a cell edit is saved and recorded in the history" page="/sheet">
  <test:submit action="__edit" __table="tasks" __key="1" __column="priority" value="low" />
  <test:expect redirect="/sheet" flash="Saved: priority" />
  <test:expect table="tasks" count="1" where="id = 1 AND priority = 'low'" />
  <test:expect history="tasks" count="1" op="update" where="id = 1" />
</q:test>

<q:test name="a cell refuses a value the schema does not allow" page="/sheet">
  <test:submit action="__edit" __table="tasks" __key="1" __column="priority" value="urgent" />
  <test:expect table="tasks" count="1" where="id = 1 AND priority = 'high'" />
  <test:expect history="tasks" count="0" />
</q:test>

<q:test name="the edit form validates with the schema's rules" page="/task/1">
  <test:submit action="save" title="" priority="urgent" />
  <test:expect error="title" message="Required" />
  <test:expect error="priority" message="Must be one of: low, medium, high" />
  <test:expect table="tasks" count="1" where="id = 1 AND title = 'Read the Quantum guide'" />
</q:test>

<q:test name="an edit is saved and shows in the task's history" page="/task/1">
  <test:as user="ana" />
  <test:submit action="save" title="Read the whole guide" priority="low" />
  <test:expect redirect="/" flash="Saved: Read the whole guide" />
  <test:expect table="tasks" count="1" where="id = 1 AND title = 'Read the whole guide' AND priority = 'low'" />
  <test:expect history="tasks" action="save" op="update" user="ana" where="id = 1" count="1" />
  <test:visit path="/task/1" />
  <test:expect text="title: Read the Quantum guide → Read the whole guide" />
</q:test>

<q:test name="a task that does not exist" page="/task/99">
  <test:visit />
  <test:expect text="That task does not exist" />
</q:test>
```

运行它们：

```bash
quantum test
```

<!-- report: pass -->
```text
components/sheet.test.q
  PASS  a cell edit is saved and recorded in the history  (304 ms)
  PASS  a cell refuses a value the schema does not allow  (32 ms)
  PASS  the edit form validates with the schema's rules  (35 ms)
  PASS  an edit is saved and shows in the task's history  (55 ms)
  PASS  a task that does not exist  (33 ms)
tests/tasks.test.q
  PASS  the list shows the summary and the tasks  (29 ms)
  PASS  create a task  (47 ms)
  PASS  a title that is too short is refused on its field  (34 ms)
  PASS  a priority outside the list is refused  (33 ms)
  PASS  finish a task and show the open ones  (39 ms)
  PASS  delete a task  (34 ms)
  PASS  the page runs a fixed number of queries  (33 ms)
  PASS  the filter comes from the query string  (26 ms)
13 passed, 0 failed
```

测试失败时 `quantum test` 以 `1` 退出，所以它可以原样在 CI 中运行。

## 8. 同一个应用，在别处运行

`ui:*` 页面不只是 HTML：

```bash
quantum console    # the same pages in the terminal
quantum desktop    # in a desktop window (pip install "quantum-framework[desktop]")
```

## 接下来去哪里

- [Actions and forms](/guide/actions)：`q:param` 接受的每一条规则
- [Queries](/guide/query)：参数、分页和历史记录
- [UI](/guide/ui)：`ui:*` 标签
- [Testing an App](/guide/testing)：每一个 `test:` 步骤
