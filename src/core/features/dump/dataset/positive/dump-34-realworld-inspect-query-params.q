<!-- Positive: Inspect query parameters -->
<!-- Category: Real-World Patterns -->
<q:component name="DumpRealworldInspectQueryParams" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="params" value='{"page": 1, "size": 20, "sort": "name", "filter": "active"}' operation="json" />
  <q:dump var="{params}" label="Query Parameters" />

  <q:return value="Dumped" />
</q:component>
