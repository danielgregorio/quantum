<!-- Positive: Logging with array as context -->
<!-- Category: Edge Cases -->
<q:component name="LogEdgeArrayContext" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="items" value='["apple", "banana", "cherry"]' operation="json" />
  <q:log level="info" message="Items processed" context="{items}" />

  <q:return value="Array context logged" />
</q:component>
