<!-- Positive: Dump empty object -->
<!-- Category: Edge Cases -->
<q:component name="DumpEdgeEmptyObject" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="emptyObj" value='{}' operation="json" />
  <q:dump var="{emptyObj}" label="Empty Object" />

  <q:return value="Dumped" />
</q:component>
