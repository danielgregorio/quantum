<!-- Positive: Logging with newline characters -->
<!-- Category: Edge Cases -->
<q:component name="LogEdgeNewlines" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:log level="info" message="Line 1&#10;Line 2&#10;Line 3" />

  <q:return value="Newlines logged" />
</q:component>
