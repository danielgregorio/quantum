<!-- Positive: Logging data import results -->
<!-- Category: Integration Patterns -->
<q:component name="LogIntegrationDataImport" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="users" source="data/users.csv" type="csv">
    <q:column name="id" type="integer" />
    <q:column name="name" type="string" />
  </q:data>

  <q:log level="info"
         message="Loaded {users_result.recordCount} users in {users_result.loadTime}ms"
         when="{users_result.success}" />

  <q:log level="error"
         message="Failed to load users: {users_result.error.message}"
         when="{!users_result.success}" />

  <q:return value="{users_result.recordCount}" />
</q:component>
