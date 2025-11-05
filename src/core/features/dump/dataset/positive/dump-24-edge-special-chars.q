<!-- Positive: Dump special characters -->
<!-- Category: Edge Cases -->
<q:component name="DumpEdgeSpecialChars" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="special" value="&lt;&gt;&amp;&quot;" />
  <q:dump var="{special}" label="Special Chars" />

  <q:return value="Dumped" />
</q:component>
