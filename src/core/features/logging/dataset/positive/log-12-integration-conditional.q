<!-- Positive: Conditional logging with q:if -->
<!-- Category: Integration Patterns -->
<q:component name="LogIntegrationConditional" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="status" value="error" />

  <q:if condition="{status == 'error'}">
    <q:log level="error" message="Error status detected" />
  <q:else>
    <q:log level="info" message="Status OK" />
  </q:if>

  <q:return value="Conditional log" />
</q:component>
