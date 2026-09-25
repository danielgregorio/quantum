<q:component name="Helpdesk">
  <q:action name="open" method="POST">
    <q:param name="message" required="true" minlength="10" />

    <!-- responseFormat="json": the model is asked for JSON, and the value is
         the parsed object — ticket.category, ticket.urgent. -->
    <q:llm name="ticket" responseFormat="json" temperature="0">
      <q:prompt>Classify this customer message. Answer with JSON only:
{"category": "billing" or "shipping" or "other", "urgent": true or false}
Message: {message}</q:prompt>
    </q:llm>

    <!-- A model's answer is input like any other: a category it made up is
         filed as "other" (the table's CHECK would refuse it). -->
    <q:set name="category" value="{ticket.category if ticket.category in ['billing', 'shipping'] else 'other'}" />

    <q:query name="saved" datasource="db">
      INSERT INTO tickets (message, category, urgent) VALUES (:message, :category, :urgent)
      <q:param name="message" value="{message}" type="string" />
      <q:param name="category" value="{category}" type="string" />
      <q:param name="urgent" value="{ticket.urgent == true}" type="boolean" />
    </q:query>
    <q:redirect url="/" flash="Filed under {category}." />
  </q:action>

  <q:query name="tickets" datasource="db">
    SELECT category, urgent, message FROM tickets ORDER BY id DESC
  </q:query>

  <ui:window title="Helpdesk">
    <q:if condition="flash">
      <ui:alert variant="success">{flash}</ui:alert>
    </q:if>
    <ui:form on-submit="open">
      <ui:input bind="message" rows="3" placeholder="How can we help?" />
      <ui:button variant="primary">Send</ui:button>
    </ui:form>
    <ui:table source="{tickets}" />
  </ui:window>
</q:component>
