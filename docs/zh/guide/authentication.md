---
source: guide/authentication.md
source_hash: 6718120df989
---

# 身份认证

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/authentication)为准。
:::

Quantum 中的身份认证由核心中已有的三部分组成：要求登录的**页面属性**、记住谁已登录的
**会话**，以及如实检查登录的**密码函数**。没有单独的认证服务器，也没有 JavaScript。

## 保护一个页面 {#protecting-a-page}

```xml
<q:component name="dashboard" require_auth="true" require_role="admin"
             xmlns:q="https://quantum.lang/ns">
  <html><body>
    <p>Hello, {session.userName}</p>
  </body></html>
</q:component>
```

| 访问者 | 结果 |
|---------|--------|
| 未登录 | 重定向到 `/login` |
| 会话已过期 | 重定向到 `/login?expired=true` |
| 已登录，但 `session.userRole` 不是 `admin` | `403 Forbidden` |
| 以 `admin` 身份登录 | 这个页面 |

`require_role` 接受用逗号分隔的多个角色：`require_role="admin,editor"`。

页面的 `q:action` 也受到保护：没有会话的 POST 会被重定向，动作不会运行。

### 守卫 {#guards}

位于页面顶部、分支中带有 `q:redirect` 的 `q:if` 就是一个*守卫*。它在页面之前、
也在页面的每个动作之前运行：

```xml
<q:component name="login" xmlns:q="https://quantum.lang/ns">
  <!-- Already logged in? Go to the dashboard. -->
  <q:if condition="session.authenticated">
    <q:redirect url="/dashboard" />
  </q:if>
  <html><body><p>Please sign in.</p></body></html>
</q:component>
```

还不存在的会话键在条件中读作空值，所以对于没有登录的访问者，
`not session.authenticated` 为真。

两条规则防止守卫在失败时放行：

- 在有动作的页面上，守卫只能读取页面运行之前就存在的东西——`session`、`query`、`form`、
  `cookie`、路由段——而不能读取页面设置的变量。动作不会运行页面的语句，所以那个变量在那里
  并不存在。这是一个解析错误。
- 无法求值的守卫条件（没有 `session.user` 时的 `not session.user.is_admin`）是一个错误，而不是"假"。

要保护一个页面，优先使用 `require_auth` / `require_role`：它们的意思一目了然。

## 登录 {#logging-in}

登录会查找用户，将密码与保存的哈希比对，然后开启会话。这里的数据表是
`users (id, email, name, role, password_hash)`，位于 `quantum.config.yaml` 中声明的、
名为 `db` 的数据源中。

保存为 `components/login.q`：

```xml
<q:component name="login" xmlns:q="https://quantum.lang/ns">
  <q:action name="signIn" method="POST">
    <q:param name="email" type="email" required="true" />
    <q:param name="password" required="true" />

    <q:query name="user" datasource="db">
      SELECT id, name, role, password_hash FROM users WHERE email = :email
      <q:param name="email" value="{email}" type="string" />
    </q:query>

    <q:if condition="user.length == 1 and verifyPassword(password, user[0].password_hash)">
      <q:set name="session.authenticated" value="true" type="boolean" />
      <q:set name="session.userId" value="{user[0].id}" />
      <q:set name="session.userName" value="{user[0].name}" />
      <q:set name="session.userRole" value="{user[0].role}" />
      <q:set name="session.sessionExpiry" value="{dateAdd('h', 8)}" />
      <q:redirect url="/dashboard" />
    </q:if>

    <q:flash type="error" message="Invalid e-mail or password" />
    <q:redirect url="/login" />
  </q:action>

  <html><body>
    <q:if condition="flash"><p class="{flashType}">{flash}</p></q:if>
    <form method="POST" action="/login">
      <input name="email" type="email" />
      <input name="password" type="password" />
      <button>Sign in</button>
    </form>
  </body></html>
</q:component>
```

- 错误的密码和未知的电子邮件得到**同样的**消息，所以表单不会暴露哪些电子邮件有账号。
- `session.sessionExpiry` 是**必需的**。没有它的会话算作已过期——检查在失败时是关闭的。
  `dateAdd('h', 8)` 表示从现在起八小时。
- `session.authenticated`、`session.userRole` 和 `session.sessionExpiry` 是
  `require_auth` 和 `require_role` 读取的名字。

## 创建账号 {#creating-an-account}

保存哈希，永远不要保存密码：

```xml
<q:action name="createAccount" method="POST">
  <q:param name="email" type="email" required="true" />
  <q:param name="name" required="true" />
  <q:param name="password" required="true" minlength="10" />

  <q:query name="created" datasource="db">
    INSERT INTO users (email, name, role, password_hash)
    VALUES (:email, :name, 'user', :hash)
    <q:param name="email" value="{email}" type="string" />
    <q:param name="name" value="{name}" type="string" />
    <q:param name="hash" value="{hashPassword(password)}" type="string" />
  </q:query>

  <q:redirect url="/login" flash="Account created. Sign in with your e-mail." />
</q:action>
```

`hashPassword` 使用 bcrypt，每次调用都用新的盐。对于空密码、缺失的哈希，或任何不是
有效哈希的东西，`verifyPassword` 返回 false——从不报错。

## 退出登录 {#logging-out}

```xml
<q:action name="signOut" method="POST">
  <q:set name="session.authenticated" value="false" type="boolean" />
  <q:set name="session.userRole" value="" />
  <q:redirect url="/login" />
</q:action>
```

## 下一步 {#next-steps}

- [会话与作用域](/guide/sessions)——上面用到的会话值
- [动作与表单](/zh/guide/actions)——登录表单的字段是如何声明的
- [数据库查询](/zh/guide/query)——声明 `db` 数据源
