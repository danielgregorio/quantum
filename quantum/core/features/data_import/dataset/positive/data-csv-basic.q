<!-- Positive: Basic CSV import with type conversion -->
<q:component name="CSVBasicImport" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="users" source="data/users.csv" type="csv">
    <q:column name="id" type="integer" />
    <q:column name="name" type="string" />
    <q:column name="age" type="integer" />
    <q:column name="active" type="boolean" />
  </q:data>

  <q:return value="{users}" />
</q:component>
