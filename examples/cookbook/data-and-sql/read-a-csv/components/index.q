<q:component name="Customers">
  <!-- The path is relative to the app's folder. Declared columns are typed;
       the others come as text. -->
  <q:data name="customers" source="import/customers.csv" type="csv">
    <q:column name="id" type="integer" />
    <q:column name="age" type="integer" />
    <q:column name="active" type="boolean" />
    <q:transform>
      <q:filter condition="active" />
      <q:sort by="age" order="desc" />
    </q:transform>
  </q:data>

  <ui:window title="Active customers">
    <ui:table source="{customers}">
      <ui:column key="name" label="Name" />
      <ui:column key="age" label="Age" />
    </ui:table>
  </ui:window>
</q:component>
