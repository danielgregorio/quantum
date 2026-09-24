<!-- Positive: Logging with computed message -->
<!-- Category: Integration Patterns -->
<q:component name="LogIntegrationComputedMessage" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="count" value="5" />
  <q:set var="status" value="active" />
  <q:set var="logMessage" value="Found {count} {status} users" />

  <q:log level="info" message="{logMessage}" />

  <q:return value="Computed message logged" />
</q:component>
