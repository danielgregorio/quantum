<!-- Positive: Dump mixed types array -->
<!-- Category: Edge Cases -->
<q:component name="DumpEdgeMixedTypesArray" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="mixed" value='[1, "two", true, null, {"key": "value"}]' operation="json" />
  <q:dump var="{mixed}" label="Mixed Types" />

  <q:return value="Dumped" />
</q:component>
