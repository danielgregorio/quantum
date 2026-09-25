<q:component name="Contacts">
  <q:query name="contacts" datasource="db">
    SELECT id, name FROM contacts ORDER BY name
  </q:query>

  <ui:window title="Contacts">
    <q:if condition="flash">
      <ui:alert variant="success">{flash}</ui:alert>
    </q:if>
    <q:loop query="contacts">
      <ui:hbox gap="sm">
        <ui:text>{contacts.name}</ui:text>
        <!-- A link, not a button: opening it only asks. -->
        <ui:link to="/delete/{contacts.id}">Delete</ui:link>
      </ui:hbox>
    </q:loop>
  </ui:window>
</q:component>
