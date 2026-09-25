---
source: guide/quick-start.md
source_hash: e3d3a1ae34f9
---

# 快速开始

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/quick-start)为准。
:::

用 5 分钟构建你的第一个 Quantum 应用。

## 第 1 步：创建一个组件

创建一个名为 `counter.q` 的文件：

```xml
<q:component name="Counter" xmlns:q="https://quantum.lang/ns">
  <!-- Initialize state -->
  <q:set name="count" value="0" type="number" />

  <!-- Function to increment -->
  <q:function name="increment">
    <q:set name="count" value="{count + 1}" />
  </q:function>

  <!-- Function to decrement -->
  <q:function name="decrement">
    <q:set name="count" value="{count - 1}" />
  </q:function>

  <!-- Return current count -->
  <q:return value="Count: {count}" />
</q:component>
```

运行它：
```bash
quantum run counter.q
```

## 第 2 步：添加一个循环

创建 `todo-list.q`：

```xml
<q:component name="TodoList" xmlns:q="https://quantum.lang/ns">
  <!-- Define tasks as an array -->
  <q:set name="tasks" value='["Buy groceries", "Walk the dog", "Write code"]' />

  <!-- Loop through tasks: each q:return adds one item to the result -->
  <q:loop type="array" var="task" items="{tasks}">
    <q:return value="- {task}" />
  </q:loop>
</q:component>
```

输出：
```
["- Buy groceries", "- Walk the dog", "- Write code"]
```

循环中的 `q:return` 不会结束循环：每个值都会被收集起来，循环结束时组件返回这个列表——
就像 `q:if` 中的 `q:return` 会结束组件一样。一个没有执行任何 `q:return` 的循环，
会让执行继续到它后面的内容。

## 第 3 步：添加条件

创建 `weather.q`：

```xml
<q:component name="Weather" xmlns:q="https://quantum.lang/ns">
  <q:set name="temperature" value="25" type="number" />

  <q:if condition="temperature > 30">
    <q:return value="It's hot! Stay hydrated." />
  </q:if>
  <q:elseif condition="temperature > 20">
    <q:return value="Nice weather for a walk." />
  </q:elseif>
  <q:elseif condition="temperature > 10">
    <q:return value="Bring a jacket." />
  </q:elseif>
  <q:else>
    <q:return value="Bundle up, it's cold!" />
  </q:else>
</q:component>
```

## 第 4 步：提供一个网页

页面放在 `components/` 文件夹中；文件名就是 URL。创建 `components/index.q`：

```xml
<q:component name="index" xmlns:q="https://quantum.lang/ns">
  <q:set name="items" value='["Apple", "Banana", "Cherry"]' />
  <q:set name="a" value="10" type="number" />
  <q:set name="b" value="5" type="number" />

  <html>
  <head><title>My Quantum App</title></head>
  <body>
    <h1>Welcome to Quantum</h1>
    <ul>
      <q:loop type="array" var="item" items="{items}">
        <li>{item}</li>
      </q:loop>
    </ul>
    <p>{a} + {b} = {a + b}</p>
  </body>
  </html>
</q:component>
```

在包含 `components/` 的文件夹中启动服务器：

```bash
quantum start
```

打开 `http://localhost:8080`。`components/about.q` 会对应 `/about`。用 `quantum stop` 停止服务器。

> 文件里不要写 `<!DOCTYPE html>`：`.q` 是 XML，而 DOCTYPE 只能出现在根元素之前。
> 服务器会在响应中加上它。

## 第 5 步：读取数据库

创建一个只有一张表的 SQLite 数据库（任何 Python 都可以——Quantum 本来就需要它）：

```bash
python -c "import sqlite3, os; os.makedirs('data', exist_ok=True); c = sqlite3.connect('data/app.db'); c.execute('CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)'); c.executemany('INSERT INTO users (name, email) VALUES (?, ?)', [('Ana', 'ana@example.com'), ('Bruno', 'bruno@example.com')]); c.commit()"
```

在 `components/` 旁边的 `quantum.config.yaml` 中声明它：

```yaml
datasources:
  db:
    driver: sqlite
    database: ./data/app.db
```

创建 `components/users.q`：

```xml
<q:component name="users" xmlns:q="https://quantum.lang/ns">
  <q:query name="users" datasource="db">
    SELECT id, name, email FROM users ORDER BY name
  </q:query>

  <html><body>
    <h1>{users_result.recordCount} users</h1>
    <table>
      <q:loop query="users">
        <tr><td>{users.name}</td><td>{users.email}</td></tr>
      </q:loop>
    </table>
  </body></html>
</q:component>
```

重启服务器，打开 `http://localhost:8080/users`。

## 第 6 步：处理表单

添加一个表单和一个插入一行数据的 `q:action`——参数都经过声明，所以 SQL 永远不会接触到原始输入。
用下面的内容替换 `components/users.q`：

```xml
<q:component name="users" xmlns:q="https://quantum.lang/ns">
  <q:action name="add" method="POST">
    <q:param name="name" required="true" minlength="2" />
    <q:param name="email" type="email" required="true" />
    <q:query name="inserted" datasource="db">
      INSERT INTO users (name, email) VALUES (:name, :email)
      <q:param name="name" value="{name}" type="string" />
      <q:param name="email" value="{email}" type="string" />
    </q:query>
    <q:redirect url="/users" flash="Added {name}" />
  </q:action>

  <q:query name="users" datasource="db">
    SELECT id, name, email FROM users ORDER BY name
  </q:query>

  <html><body>
    <q:if condition="flash"><p>{flash}</p></q:if>
    <table>
      <q:loop query="users">
        <tr><td>{users.name}</td><td>{users.email}</td></tr>
      </q:loop>
    </table>
    <form method="POST" action="/users">
      <input name="name" /> <input name="email" type="email" />
      <button>Add</button>
    </form>
  </body></html>
</q:component>
```

## 接下来？

你已经学会了基础！接下来可以看看（以下页面为英文）：

- [动作与表单](/guide/actions)——校验、重定向、多个动作
- [身份认证](/guide/authentication)——带密码校验的登录
- [组件](/guide/components)——深入了解组件系统
- [状态管理](/guide/state-management)——更进一步的变量处理
- [AI](/guide/ai)——以标签形式调用 LLM、RAG 和智能体
- [数据库查询](/guide/query)——SQL 与数据操作
- [实用示例](/cookbook/)——经过测试的简短示例
