<!-- Positive: Logging with structured context data -->
<!-- Category: Basic Patterns -->
<q:component name="LogStructuredContext" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="user" value='{"id": 123, "name": "Bob", "role": "admin"}' operation="json" />
  <q:log level="info" message="User authenticated" context="{user}" />

  <q:return value="Logged with context" />
</q:component>
