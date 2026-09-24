<!-- Negative: Missing required 'message' attribute -->
<!-- Expected error: Log requires 'message' attribute -->
<q:component name="LogNegMissingMessage" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:log level="info" />

  <q:return value="Error" />
</q:component>
