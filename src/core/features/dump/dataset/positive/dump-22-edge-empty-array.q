<!-- Positive: Dump empty array -->
<!-- Category: Edge Cases -->
<q:component name="DumpEdgeEmptyArray" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="emptyArr" value='[]' operation="json" />
  <q:dump var="{emptyArr}" label="Empty Array" />

  <q:return value="Dumped" />
</q:component>
