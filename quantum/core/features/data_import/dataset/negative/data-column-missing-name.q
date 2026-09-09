<!-- Negative: Column missing required 'name' attribute -->
<!-- Expected error: Column requires 'name' attribute -->
<q:component name="DataColumnMissingName" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="users" source="data/users.csv" type="csv">
    <q:column type="integer" />
  </q:data>

  <q:return value="Error" />
</q:component>
