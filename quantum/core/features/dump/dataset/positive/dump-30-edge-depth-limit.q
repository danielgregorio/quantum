<!-- Positive: Dump with depth limit -->
<!-- Category: Edge Cases -->
<q:component name="DumpEdgeDepthLimit" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="nested" value='{"a": {"b": {"c": {"d": "deep"}}}}' operation="json" />
  <q:dump var="{nested}" depth="2" label="Depth Limited" />

  <q:return value="Dumped" />
</q:component>
