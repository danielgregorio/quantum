<!-- Positive: Logging with null context (edge case) -->
<!-- Category: Edge Cases -->
<q:component name="LogEdgeNullContext" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="nullValue" value="null" operation="json" />
  <q:log level="info" message="Null context test" context="{nullValue}" />

  <q:return value="Null context logged" />
</q:component>
