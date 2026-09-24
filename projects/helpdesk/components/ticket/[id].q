<q:component name="Ticket">
  <q:action name="close" method="POST">
    <q:query name="closed" datasource="db">
      UPDATE tickets SET status = 'closed' WHERE id = :id AND status = 'open'
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:query name="ticket" datasource="db">
      SELECT title, email FROM tickets WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:if condition="closed_result.recordCount == 1">
      <q:mail to="{ticket[0].email}" subject="Ticket #{id} closed" type="text">
Your ticket "{ticket[0].title}" (#{id}) was closed.
      </q:mail>
    </q:if>
    <q:redirect url="/ticket/{id}" flash="Ticket #{id} closed." />
  </q:action>

  <q:query name="ticket" datasource="db">
    SELECT id, title, description, email, status, attachment, attachment_name, opened_on
    FROM tickets WHERE id = :id
    <q:param name="id" value="{id}" type="integer" />
  </q:query>

  <ui:window title="Ticket">
    <ui:vbox gap="md" padding="lg">
      <ui:link to="/">All tickets</ui:link>
      <q:if condition="flash">
        <ui:alert variant="info">{flash}</ui:alert>
      </q:if>
      <q:if condition="ticket_result.recordCount == 0">
        <ui:alert variant="danger">There is no ticket #{id}.</ui:alert>
      </q:if>
      <q:else>
        <ui:header title="#{ticket[0].id} {ticket[0].title}" />
        <ui:text>From {ticket[0].email}, {ticket[0].opened_on}. Status: {ticket[0].status}.</ui:text>
        <ui:panel title="Description">
          <ui:text id="description">{ticket[0].description}</ui:text>
        </ui:panel>
        <q:if condition="ticket[0].attachment">
          <ui:link to="/attachment/{ticket[0].id}" id="attachment">Attachment: {ticket[0].attachment_name}</ui:link>
        </q:if>
        <q:if condition="ticket[0].status == 'open'">
          <ui:button on-click="close" variant="danger">Close ticket</ui:button>
        </q:if>
      </q:else>
    </ui:vbox>
  </ui:window>
</q:component>
