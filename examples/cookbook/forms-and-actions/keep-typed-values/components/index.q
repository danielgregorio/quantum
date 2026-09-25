<q:component name="Contact">
  <q:action name="send" method="POST">
    <q:param name="email" type="email" required="true" />
    <q:param name="body" required="true" minlength="20" maxlength="2000" />
    <q:query name="saved" datasource="db">
      INSERT INTO messages (email, body) VALUES (:email, :body)
      <q:param name="email" value="{email}" type="string" />
      <q:param name="body" value="{body}" type="string" />
    </q:query>
    <q:redirect url="/" flash="Thanks, we got your message." />
  </q:action>

  <ui:window title="Contact us">
    <q:if condition="flash">
      <ui:alert variant="{flashType == 'error' and 'danger' or 'success'}">{flash}</ui:alert>
    </q:if>
    <!-- Nothing to write for the values: after a refusal, the next render of
         this form fills each field with what was sent (UI-9), once. -->
    <ui:form on-submit="send">
      <ui:formitem label="Your e-mail"><ui:input bind="email" /></ui:formitem>
      <ui:formitem label="Message"><ui:input bind="body" rows="6" /></ui:formitem>
      <ui:button variant="primary">Send</ui:button>
    </ui:form>
  </ui:window>
</q:component>
