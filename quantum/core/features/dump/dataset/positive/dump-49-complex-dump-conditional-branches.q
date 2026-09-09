<!-- Positive: Dump from different conditional branches -->
<!-- Category: Complex Scenarios -->
<q:component name="DumpComplexDumpConditionalBranches" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="role" value="admin" />
  <q:if condition="{role == 'admin'}">
    <q:set var="permissions" value='["read", "write", "delete"]' operation="json" />
    <q:dump var="{permissions}" label="Admin Permissions" />
  <q:else>
    <q:set var="permissions" value='["read"]' operation="json" />
    <q:dump var="{permissions}" label="User Permissions" />
  </q:if>

  <q:return value="Dumped" />
</q:component>
