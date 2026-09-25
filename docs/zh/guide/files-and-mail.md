---
source: guide/files-and-mail.md
source_hash: 03999c32bb66
---
# 文件和邮件

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/files-and-mail)为准。
:::

表单可以接收文件，页面可以把文件交还出去，动作可以发送邮件。`projects/helpdesk` 三者都用到了：带附件的工单，以及发给支持团队和提交人的邮件。

## 接收文件 {#taking-a-file}

把文件声明为动作的参数。`accept` 和 `maxsize` 是和 `minlength` 一样的规则：违反它们的文件永远不会到达动作，表单会在字段旁边说明原因。

```xml
<q:action name="open" method="POST">
  <q:param name="title" required="true" minlength="5" />
  <q:param name="attachment" type="file" maxsize="5MB" accept=".png,.jpg,.pdf" />

  <q:if condition="attachment">
    <q:file action="upload" file="{attachment}" result="saved" />
    <!-- saved.filename, saved.original_filename, saved.size, saved.mimetype -->
  </q:if>
  <q:redirect url="/" flash="Ticket opened: {title}" />
</q:action>

<ui:form on-submit="open" submit="Open ticket">
  <ui:input bind="title" />
  <ui:input bind="attachment" />
</ui:form>
```

表单知道动作接收文件：它以 `multipart/form-data` 提交，`attachment` 是一个提供 `.png,.jpg,.pdf` 的文件输入框。这两样你都不用写。

文件保存在 `paths.uploads` 下（除非配置另有说明，否则是 `./uploads`），使用安全的文件名；`destination="invoices"` 把它放到其中的一个文件夹里。请保存 `saved.filename`——以后靠它找回文件。

`q:file action` 可以是 `upload`、`delete` 或 `send`（见下文）；其他值无法通过解析：

```xml
<q:file action="copy" file="{attachment}" />
```

**Error:** `<q:file action="copy">: use upload, delete or send`

多行字段写作 `<ui:input bind="description" rows="6" />`。

## 交还文件 {#handing-a-file-back}

上传的文件**不会**作为静态文件提供：否则任何拿到 URL 的人都能读取。由一个页面发送文件，并决定谁可以得到它：

```xml
<!-- components/attachment/[id].q -->
<q:component name="Attachment">
  <q:query name="ticket" datasource="db">
    SELECT attachment, attachment_name FROM tickets WHERE id = :id AND attachment IS NOT NULL
    <q:param name="id" value="{id}" type="integer" />
  </q:query>
  <q:if condition="ticket_result.recordCount == 1">
    <q:file action="send" file="{ticket[0].attachment}" name="{ticket[0].attachment_name}" />
  </q:if>
  <p>There is no attachment for ticket #{id}.</p>
</q:component>
```

`q:file action="send"` 以文件下载结束页面。保存的文件名来自数据库，从不来自 URL；`paths.uploads` 之外的路径会被拒绝，缺失的文件返回 404。给页面加上一个守卫（`require_auth`，或带 `q:redirect` 的 `q:if`），只有该拿到的人才能拿到。

## 发送邮件 {#sending-mail}

动作用 `q:mail` 发送消息；服务器是 `quantum.config.yaml` 的 `mail:` 部分。出自示例[开发环境中的邮件](../cookbook/files-and-mail/mail-in-development.md)，按所示经过测试：

<<< @/../examples/cookbook/files-and-mail/mail-in-development/components/index.q{xml}

<<< @/../examples/cookbook/files-and-mail/mail-in-development/quantum.config.yaml{yaml}

`host: log` 把每条消息写入日志而不是发送——在开发中使用它。没有 `mail:` 部分时，`q:mail` 是一个说明这一点的错误；它从不假装发送：

```xml
<q:mail to="ana@example.com" subject="Welcome">Hello, Ana!</q:mail>
```

**Error:** `q:mail needs a mail server`

### 当服务器拒绝时 {#when-the-server-says-no}

服务器不接受的消息会带着服务器给出的原因停止动作。如果动作的其余部分无论如何都要执行，就写 `onerror="continue"` 并检查 `<name>_result.success`——出自示例[当邮件服务器拒绝时](../cookbook/files-and-mail/mail-server-refuses.md)，其中即使确认邮件无法发送，订单也会保存：

<<< @/../examples/cookbook/files-and-mail/mail-server-refuses/components/index.q{xml}

helpdesk（`projects/helpdesk`）也是这样做的：它先保存工单，并在提示消息中说明哪封邮件没能发出。

## 规则 {#rules}

SPEC 中的 [FILE-1、FILE-2、MAIL-1、MAIL-2 和 UI-14](https://github.com/danielgregorio/quantum/blob/main/SPEC.md)。
