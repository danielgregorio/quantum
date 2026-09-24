<!-- Positive: Dump same variable in multiple formats -->
<!-- Category: Complex Scenarios -->
<q:component name="DumpComplexMultipleFormatDumps" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="data" value='{"key": "value", "count": 42}' operation="json" />
  <q:dump var="{data}" format="html" label="HTML Format" />
  <q:dump var="{data}" format="json" label="JSON Format" />

  <q:return value="Dumped" />
</q:component>
