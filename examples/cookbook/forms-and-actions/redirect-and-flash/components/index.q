<q:component name="Notes">
  <q:action name="add" method="POST">
    <q:param name="text" required="true" maxlength="200" />
    <q:query name="added" datasource="db">
      INSERT INTO notes (text) VALUES (:text)
      <q:param name="text" value="{text}" type="string" />
    </q:query>
    <!-- The flash accepts expressions; its type is "success". -->
    <q:redirect url="/" flash="Added: {text}" />
  </q:action>

  <q:action name="clear" method="POST">
    <q:query name="finished" datasource="db">
      UPDATE notes SET done = 1 WHERE done = 0
    </q:query>
    <q:if condition="finished_result.recordCount == 0">
      <!-- A flash of another kind: q:flash sets both, the redirect keeps them. -->
      <q:flash type="warning">There was nothing to clear.</q:flash>
      <q:redirect url="/" />
    </q:if>
    <q:redirect url="/done" flash="Cleared {finished_result.recordCount} notes." />
  </q:action>

  <q:query name="notes" datasource="db">
    SELECT id, text FROM notes WHERE done = 0 ORDER BY id
  </q:query>

  <ui:window title="Notes">
    <!-- flash and flashType exist on every page, '' when there is none;
         a flash shows on the next page rendered, once. -->
    <q:if condition="flash">
      <ui:alert variant="{flashType}">{flash}</ui:alert>
    </q:if>
    <ui:form on-submit="add">
      <ui:hbox gap="sm">
        <ui:input bind="text" placeholder="A note" grow="true" />
        <ui:button variant="primary">Add</ui:button>
      </ui:hbox>
    </ui:form>
    <q:loop query="notes">
      <ui:text>{notes.text}</ui:text>
    </q:loop>
    <ui:button on-click="clear">Clear all</ui:button>
  </ui:window>
</q:component>
