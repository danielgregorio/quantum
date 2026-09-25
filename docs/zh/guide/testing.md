---
source: guide/testing.md
source_hash: d3d9fb557d8b
---

# 测试应用（`quantum test`）

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/testing)为准。
:::

Quantum 应用用它自己的语言来测试。`*.test.q` 文件中的测试访问页面、提交动作，
并检查发生了什么——重定向、提示消息、数据库中的行、字段旁边的错误——使用的是应用本来就在用的词汇。
`quantum test` 针对真实的服务器运行它们，每个测试都使用全新的数据库，只要有一个失败就以 `1` 退出。

不需要 Python，不需要浏览器，不需要 CSS 选择器。

## 第一个测试 {#a-first-test}

一个小小的笔记应用。保存为 `quantum.config.yaml`：

```yaml
datasources:
  db:
    driver: sqlite
    database: ./data/notes.db
    history: true
```

保存为 `migrations/V001_notes.sql`：

```sql
CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'idea' CHECK (kind IN ('idea', 'todo')),
    created_at TEXT DEFAULT (datetime('now'))
);
INSERT INTO notes (title) VALUES ('Read the guide');
```

保存为 `components/index.q`：

```xml
<q:component name="Notes">
  <q:action name="add" method="POST">
    <q:param name="title" required="true" minlength="3" />
    <q:param name="kind" default="idea" enum="idea,todo" />
    <q:query name="added" datasource="db">
      INSERT INTO notes (title, kind) VALUES (:title, :kind)
      <q:param name="title" value="{title}" type="string" />
      <q:param name="kind" value="{kind}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Added: {title}" />
  </q:action>

  <q:query name="notes" datasource="db">SELECT title, kind FROM notes ORDER BY id</q:query>

  <ui:window title="Notes">
    <ui:vbox gap="md" padding="lg">
      <q:if condition="flash"><ui:alert variant="success">{flash}</ui:alert></q:if>
      <ui:form on-submit="add">
        <ui:input bind="title" />
        <ui:button variant="primary">Add</ui:button>
      </ui:form>
      <ui:text>{notes_result.recordCount} notes</ui:text>
      <q:loop query="notes"><ui:text>{notes.title} ({notes.kind})</ui:text></q:loop>
    </ui:vbox>
  </ui:window>
</q:component>
```

以及它的测试。保存为 `tests/notes.test.q`：

```xml
<q:test name="the list" page="/">
  <test:visit />
  <test:expect text="1 notes" />
  <test:expect text="Read the guide (idea)" />
</q:test>

<q:test name="add a note" page="/">
  <test:submit action="add" title="Buy bread" kind="todo" />
  <test:expect redirect="/" flash="Added: Buy bread" />
  <test:expect table="notes" count="1" where="title = 'Buy bread' AND kind = 'todo'" />
  <test:expect text="2 notes" />
  <test:expect history="notes" action="add" op="insert" count="1" />
</q:test>

<q:test name="a title needs three letters" page="/">
  <test:submit action="add" title="x" />
  <test:expect error="title" message="Must be at least 3 characters" />
  <test:expect table="notes" count="1" />
</q:test>
```

在应用的文件夹中运行它们：

```bash
quantum test
```

<!-- report: pass -->
```text
tests/notes.test.q
  PASS  the list  (31 ms)
  PASS  add a note  (38 ms)
  PASS  a title needs three letters  (27 ms)
3 passed, 0 failed
```

每个测试都从同一个地方开始：一个由 `migrations/` 构建的新数据库，里面只有 `Read the guide`。
`a title needs three letters` 开始时，`add a note` 写入的内容已经不在了。

## 当测试失败时 {#when-a-test-fails}

把 `add a note` 中的提示消息改成 `flash="Added: Buy milk"`，然后再运行一次。报告会指出
失败的步骤及其行号，以及应用实际做了什么：

<!-- report: fail -->
```text
tests/notes.test.q
  PASS  the list  (29 ms)
  FAIL  add a note  (35 ms)
        tests/notes.test.q:9  <test:expect redirect="/" flash="Added: Buy milk"/>
        expected flash "Added: Buy milk", got "Added: Buy bread"
  PASS  a title needs three letters  (26 ms)
2 passed, 1 failed
```

`quantum test` 以 `1` 退出，所以 CI 任务会随之失败。

当页面本身失败时——无法求值的表达式、被数据库拒绝的 SQL——发出请求的那个步骤会带着错误
以及**页面**的行号一起失败：

```text
        tests/bill.test.q:2  <test:visit/>
        the server answered 500: ComponentExecutionError: …
        page: components/bill.q:4
```

请求返回错误状态码（`400` 或以上）的步骤会失败，除非紧接着的下一步说明它期望这个状态——
例如在访问一个不应存在的页面之后写 `<test:expect status="404"/>`。

## 测试放在哪里 {#where-tests-live}

`quantum test` 在给定的文件夹（默认是当前文件夹）中查找 `*.test.q`：

- **在页面旁边**——`components/admin/index.test.q` 测试 `components/admin/index.q`。
  `.test.q` 永远不会被当作页面提供，也不会生成路由；`quantum check` 把它当作测试文件读取。
- **在 `tests/` 中**——关于整个应用的测试套件，例如 `tests/signin.test.q`。

测试文件属于它上方最近的 `quantum.config.yaml` 所在的应用。
`quantum test projects/blog tests/one.test.q` 可以一次运行多个位置。

## 步骤 {#the-steps}

`q:test` 有一个 `name` 和它开始时所在的 `page`（默认为 `/`）。它的步骤按顺序运行。

| 步骤 | 作用 |
|---|---|
| `<test:given table="notes" title="Draft"/>` | 插入一行，并按数据表结构检查 |
| `<test:as user="Ana" role="admin" id="1"/>` | 不需要密码就登录 |
| `<test:visit/>` | 打开页面——或 `path="/other"`——其他属性作为查询字符串 |
| `<test:submit action="add" title="…"/>` | 提交动作，其他属性作为字段 |
| `<test:expect …/>` | 检查发生了什么 |

### `test:given`——测试需要的行 {#test-given-—-rows-the-test-needs}

```xml
<test:given table="notes" title="Draft" kind="todo" />
```

这一行按数据表结构的规则进入测试的数据库：不存在的数据表或列、不在 `CHECK (… IN …)`
列表中的值、`INTEGER` 列中的文本、什么都不指向的外键——每一种都会让这一步带着消息失败，
而不是插入应用本来不可能写入的东西。这一步省略的必填列会被自动填上：`CHECK … IN` 允许的第一个值、
外键所指向的数据表的第一行、一个数字，或者文本列的 `"<column> <n>"`。有多个数据源时，
用 `datasource="…"` 指明是哪一个。

### `test:as`——谁在使用应用 {#test-as-—-who-is-using-the-app}

```xml
<test:as user="Ana" role="admin" id="1" plan="pro" />
```

像登录一样设置会话：`session.userName` 为 `Ana`，`session.userRole` 为 `admin`，
`session.userId` 为 `1`，带 `require_auth` 和 `require_role` 的页面会让测试进入。
其他任何属性都是会话变量（上面的 `session.plan`）。要测试登录表单本身，就像真人一样提交它。

### `test:visit` 和 `test:submit`——浏览器做的事 {#test-visit-and-test-submit-—-what-a-browser-does}

`test:submit` 向测试当前所在的页面提交数据，就像那个页面上的表单一样：经过页面的守卫、
动作的 `q:param` 规则、历史、重定向和提示消息。两个步骤都像浏览器一样跟随重定向，
之后测试就位于它最终到达的页面——所以下一个 `test:submit` 会提交到那里。例如，
重定向到登录页面之后，测试就在 `/login` 上。

只有一个 `q:action` 的页面，无论提交的名字是什么都会运行它；如果页面运行的动作不是这一步
指明的那个，这一步就会失败——否则测试会在测试错误的动作时通过。

## `test:expect` 检查什么 {#what-test-expect-checks}

每个属性是一条断言；同一个 `test:expect` 上的多条断言必须全部成立。

| 断言 | 成立的条件 |
|---|---|
| `status="302"` | 请求返回了这个状态码（在跟随任何重定向之前） |
| `redirect="/?added=1"` | 它重定向到这里：路径、查询和 `#fragment` |
| `flash="Added: Buy bread"` | 它设置了恰好是这样的提示消息 |
| `text="2 notes"` | 测试当前所在的页面显示这段文本（去掉标签，合并空白） |
| `no-text="Draft"` | ……不显示它 |
| `error="title"` | 提交因这个字段上的错误被拒绝；`message="…"` 检查消息 |
| `var="filter" value="open"` | 页面（或动作）结束时这个变量的值，按文本比较 |
| `queries="2"`、`queries="at most 3"` | 请求运行了这么多次数据库查询 |
| `table="notes"` | 数据库的这张表中有行——`where="…"` 筛选，`count="N"` 检查数量 |
| `history="notes"` | `history: true` 记录了这张表的变更——配合 `action`、`op`（`insert`、`update`、`delete`）、`user`、`where`、`count` |

`queries` 能发现每行运行一次查询的页面：3 行的列表和 300 行的列表都应该是 `queries="2"`。

## 词汇之外什么都没有 {#nothing-outside-the-vocabulary}

上面的步骤和断言就是这门语言的全部。不在其中的标签、不存在的断言、没有 `table` 或 `history`
可数的 `count`——每一种都是带行号的解析错误，绝不会是一个悄悄什么都不做的步骤：

```text
tests/notes.test.q: <test:click> is not a test step. The steps are: test:given, test:as, test:visit, test:submit, test:expect
  at line 4: <test:click text="Add" />
```

## 在 CI 中 {#in-ci}

所有测试都通过时，`quantum test` 以 `0` 退出，否则以 `1` 退出——包括文件无法解析、路径不存在
或找不到任何测试的情况。在应用的文件夹中把它作为 CI 的一个步骤运行：

```bash
quantum test
```

## 目前的限制 {#limits-for-now}

- 只支持 `sqlite` 数据源：每个测试构建自己的 SQLite 数据库。
- 有多个数据源和一个 `migrations/` 文件夹时，迁移必须说明它们构建的是哪个数据源；测试会失败并说明这一点。
- 在界面上点击操作（`test:click`、`test:fill`）、同一个测试在 Web 和终端上运行、根据动作规则
  生成的测试、录制的 AI 回答以及覆盖率，都在计划中，尚未实现。

另请参见：[动作与表单](/zh/guide/actions)、[数据库查询](/zh/guide/query)、[身份认证](/zh/guide/authentication)。
