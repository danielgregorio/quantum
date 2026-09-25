<q:component name="Stock">
  <q:query name="items" datasource="db" sortable="true">
    SELECT id, name, shelf, quantity FROM items ORDER BY id
  </q:query>

  <ui:window title="Stock">
    <ui:vbox gap="md" padding="lg">
      <q:if condition="flash">
        <ui:alert variant="{flashType == 'error' and 'danger' or 'success'}">{flash}</ui:alert>
      </q:if>
      <!-- edit="items": each cell is a small form that saves one column of
           one row, checked against the table's schema. No action to write. -->
      <ui:table source="{items}" sort="true" edit="items" datasource="db">
        <ui:column key="name" label="Item" edit="false" />
        <ui:column key="shelf" label="Shelf" />
        <ui:column key="quantity" label="Quantity" align="right" />
      </ui:table>
    </ui:vbox>
  </ui:window>
</q:component>
