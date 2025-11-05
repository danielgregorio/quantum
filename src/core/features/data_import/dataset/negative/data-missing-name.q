<!-- Negative: Missing required 'name' attribute -->
<!-- Expected error: Data requires 'name' attribute -->
<q:component name="DataMissingName" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data source="data/users.csv" type="csv">
    <q:column name="id" type="integer" />
  </q:data>

  <q:return value="Error" />
</q:component>
