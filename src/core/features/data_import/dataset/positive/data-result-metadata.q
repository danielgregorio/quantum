<!-- Positive: Data import with result metadata -->
<q:component name="DataResultMetadata" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="users" source="data/users.csv" type="csv" result="dataResult">
    <q:column name="id" type="integer" />
    <q:column name="name" type="string" />
  </q:data>

  <!-- Access result metadata -->
  <q:if condition="{dataResult.success}">
    <q:return value="Loaded {dataResult.recordCount} users in {dataResult.loadTime}ms" />
  </q:if>
</q:component>
