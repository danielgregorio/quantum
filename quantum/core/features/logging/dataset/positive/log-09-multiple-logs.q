<!-- Positive: Multiple log statements in sequence -->
<!-- Category: Basic Patterns -->
<q:component name="LogMultipleLogs" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:log level="info" message="Starting process" />
  <q:log level="debug" message="Validating input" />
  <q:log level="info" message="Process completed" />

  <q:return value="Multiple logs written" />
</q:component>
