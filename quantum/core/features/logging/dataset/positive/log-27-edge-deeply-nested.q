<!-- Positive: Logging with deeply nested context -->
<!-- Category: Edge Cases -->
<q:component name="LogEdgeDeeplyNested" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="nested" value='{"a": {"b": {"c": {"d": {"e": "deep"}}}}}' operation="json" />
  <q:log level="debug" message="Deeply nested structure" context="{nested}" />

  <q:return value="Nested context logged" />
</q:component>
