<q:component name="ConfirmDelete">
  <q:action name="remove" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:query name="removed" datasource="db">
      DELETE FROM contacts WHERE id = :id
      <q:param name="id" value="{id}" type="integer" />
    </q:query>
    <q:redirect url="/" flash="Deleted." />
  </q:action>

  <q:query name="contact" datasource="db">
    SELECT id, name FROM contacts WHERE id = :id
    <q:param name="id" value="{id}" type="integer" />
  </q:query>

  <ui:window title="Delete a contact">
    <q:if condition="contact_result.recordCount == 0">
      <ui:text>That contact is already gone.</ui:text>
    </q:if>
    <q:else>
      <ui:text>Delete {contact.name}? This cannot be undone.</ui:text>
      <ui:hbox gap="sm">
        <ui:button on-click="remove" with="id={contact.id}" variant="danger">Yes, delete</ui:button>
        <ui:link to="/">Cancel</ui:link>
      </ui:hbox>
    </q:else>
  </ui:window>
</q:component>
