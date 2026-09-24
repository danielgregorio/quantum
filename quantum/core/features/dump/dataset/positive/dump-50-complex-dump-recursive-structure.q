<!-- Positive: Dump recursive data structure -->
<!-- Category: Complex Scenarios -->
<q:component name="DumpComplexDumpRecursiveStructure" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="tree" value='{"value": 1, "children": [{"value": 2, "children": []}, {"value": 3, "children": [{"value": 4, "children": []}]}]}' operation="json" />
  <q:dump var="{tree}" depth="5" label="Tree Structure" />

  <q:return value="Dumped" />
</q:component>
