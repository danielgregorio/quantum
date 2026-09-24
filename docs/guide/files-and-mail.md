# Files and Mail

A form can take a file, a page can hand one back, and an action can send
e-mail. `projects/helpdesk` uses all three: tickets with an attachment, a
mail to the support team and to the requester.

## Taking a file

Declare the file as a param of the action. `accept` and `maxsize` are rules
like `minlength`: a file that breaks them never reaches the action, and the
form shows why next to the field.

```xml
<q:action name="open" method="POST">
  <q:param name="title" required="true" minlength="5" />
  <q:param name="attachment" type="file" maxsize="5MB" accept=".png,.jpg,.pdf" />

  <q:if condition="attachment">
    <q:file action="upload" file="{attachment}" result="saved" />
    <!-- saved.filename, saved.original_filename, saved.size, saved.mimetype -->
  </q:if>
  ...
</q:action>

<ui:form on-submit="open" submit="Open ticket">
  <ui:input bind="title" />
  <ui:input bind="attachment" />
</ui:form>
```

The form knows the action takes a file: it posts `multipart/form-data`, and
`attachment` is a file input offering `.png,.jpg,.pdf`. You write neither.

The file is saved under `paths.uploads` (`./uploads` unless the config says
otherwise), with a safe name; `destination="invoices"` puts it in a folder
inside it. Keep `saved.filename` — it is how you find the file again.

`q:file action` is `upload`, `delete` or `send` (below); anything else does not
parse:

```xml
<q:file action="copy" file="{attachment}" />
```

**Error:** `<q:file action="copy">: use upload, delete or send`

A multi-line field is `<ui:input bind="description" rows="6" />`.

## Handing a file back

Uploads are **not** served as static files: anyone with the URL could read
them. A page sends one, and decides who may have it:

```xml
<!-- components/attachment/[id].q -->
<q:component name="Attachment">
  <q:query name="ticket" datasource="db">
    SELECT attachment, attachment_name FROM tickets WHERE id = :id
    <q:param name="id" value="{id}" type="integer" />
  </q:query>
  <q:if condition="ticket_result.recordCount == 1">
    <q:file action="send" file="{ticket[0].attachment}" name="{ticket[0].attachment_name}" />
  </q:if>
  <p>There is no attachment for ticket #{id}.</p>
</q:component>
```

`q:file action="send"` ends the page with the file as a download. The stored
name comes from the database, never from the URL; a path outside
`paths.uploads` is refused, and a missing file answers 404. Put a guard on the
page (`require_auth`, or a `q:if` with `q:redirect`) and only the right people
get it.

## Sending mail

```xml
<q:mail to="{email}" subject="We received your ticket #{id}" type="text">
Hello, your ticket "{title}" was opened as #{id}.
</q:mail>
```

The server is in `quantum.config.yaml`:

```yaml
mail:
  host: ${SMTP_HOST:-log}
  port: ${SMTP_PORT:-587}
  username: ${SMTP_USER:-}
  password: ${SMTP_PASSWORD:-}
  tls: true
  from: helpdesk@example.com
```

`host: log` writes each message to the log instead of sending it — use it in
development. Without a `mail:` section, `q:mail` is an error that says so;
it never pretends to send:

```xml
<q:mail to="ana@example.com" subject="Welcome">Hello, Ana!</q:mail>
```

**Error:** `q:mail needs a mail server`

### When the server says no

A message the server does not take stops the action with the server's reason.
When the rest of the action must happen anyway, handle it:

```xml
<q:mail name="confirmation" to="{email}" subject="..." onerror="continue">...</q:mail>
<q:if condition="not confirmation_result.success">
  <!-- confirmation_result.error.message says why -->
</q:if>
```

The helpdesk saves the ticket first and says, in its message, when a mail
could not be sent.

## Rules

[FILE-1, FILE-2, MAIL-1, MAIL-2 and UI-14](https://github.com/danielgregorio/quantum/blob/main/SPEC.md)
in the SPEC.
