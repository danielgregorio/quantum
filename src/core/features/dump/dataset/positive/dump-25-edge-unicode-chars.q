<!-- Positive: Dump Unicode characters -->
<!-- Category: Edge Cases -->
<q:component name="DumpEdgeUnicodeChars" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="unicode" value="你好 🌍" />
  <q:dump var="{unicode}" label="Unicode" />

  <q:return value="Dumped" />
</q:component>
