<!-- Positive: Dump data import result -->
<!-- Category: Integration Patterns -->
<q:component name="DumpIntegrationDataImportResult" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="users" source="data/users.csv" type="csv">
    <q:column name="id" type="integer" />
    <q:column name="name" type="string" />
  </q:data>
  <q:dump var="{users}" label="Imported Users" />

  <q:return value="Dumped" />
</q:component>
