<q:component name="Helpdesk">
  <!-- Open a ticket, with an optional attachment. The support team and the
       requester get an e-mail (MAIL-1); the attachment is stored under
       paths.uploads and only served through /attachment/<id> (FILE-2). -->

  <q:action name="open" method="POST">
    <q:param name="title" required="true" minlength="5" maxlength="120" />
    <q:param name="email" type="email" required="true" />
    <q:param name="description" required="true" minlength="10" maxlength="4000" />
    <q:param name="attachment" type="file" maxsize="5MB" accept=".png,.jpg,.jpeg,.pdf,.txt,.log" />

    <q:set name="support" value="support@example.com" />
    <q:set name="stored" value="" />
    <q:set name="sent_as" value="" />
    <q:if condition="attachment">
      <q:file action="upload" file="{attachment}" result="saved" />
      <q:set name="stored" value="{saved.filename}" />
      <q:set name="sent_as" value="{saved.original_filename}" />
    </q:if>

    <q:query name="ticket" datasource="db">
      INSERT INTO tickets (title, description, email, attachment, attachment_name)
      VALUES (:title, :description, :email, NULLIF(:stored, ''), NULLIF(:sent_as, ''))
      <q:param name="title" value="{title}" type="string" />
      <q:param name="description" value="{description}" type="string" />
      <q:param name="email" value="{email}" type="string" />
      <q:param name="stored" value="{stored}" type="string" />
      <q:param name="sent_as" value="{sent_as}" type="string" />
    </q:query>
    <q:set name="id" value="{ticket_result.lastInsertId}" />

    <q:mail name="alert" to="{support}" replyTo="{email}" subject="Ticket #{id}: {title}" type="text" onerror="continue">
New ticket #{id} from {email}

{description}
    </q:mail>
    <q:mail name="confirmation" to="{email}" subject="We received your ticket #{id}" type="text" onerror="continue">
Hello,

your ticket "{title}" was opened as #{id}. We will write back to this address.
    </q:mail>

    <!-- The ticket is saved either way; a mail that failed is said, not hidden. -->
    <q:set name="notice" value="" />
    <q:if condition="not alert_result.success or not confirmation_result.success">
      <q:set name="notice" value=" Some e-mail could not be sent; the ticket is saved." />
    </q:if>
    <q:redirect url="/ticket/{id}" flash="Ticket #{id} opened.{notice}" />
  </q:action>

  <q:query name="tickets" datasource="db">
    SELECT id, title, email, status, opened_on FROM tickets ORDER BY id DESC
  </q:query>

  <ui:window title="Helpdesk">
    <ui:vbox gap="md" padding="lg">
      <ui:header title="Helpdesk" />
      <q:if condition="flash">
        <ui:alert variant="info">{flash}</ui:alert>
      </q:if>

      <ui:panel title="Open a ticket">
        <ui:form on-submit="open" submit="Open ticket">
          <ui:input bind="title" placeholder="What is wrong?" />
          <ui:input bind="email" placeholder="you@example.com" />
          <ui:input bind="description" rows="6" placeholder="What happened, and what did you expect?" />
          <ui:input bind="attachment" />
        </ui:form>
      </ui:panel>

      <ui:panel title="Tickets">
        <ui:table source="{tickets}" as="t">
          <ui:column key="id" header="#" />
          <ui:column key="title" header="Title">
            <ui:link to="/ticket/{t.id}">{t.title}</ui:link>
          </ui:column>
          <ui:column key="status" header="Status" />
          <ui:column key="opened_on" header="Opened" />
        </ui:table>
      </ui:panel>
    </ui:vbox>
  </ui:window>
</q:component>
