<!-- Positive: Dump deeply nested structure -->
<!-- Category: Edge Cases -->
<q:component name="DumpEdgeDeeplyNested" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="deep" value='{"a": {"b": {"c": {"d": {"e": "value"}}}}}' operation="json" />
  <q:dump var="{deep}" label="Deep Nesting" />

  <q:return value="Dumped" />
</q:component>
