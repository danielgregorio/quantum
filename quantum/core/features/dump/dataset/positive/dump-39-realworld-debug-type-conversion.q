<!-- Positive: Debug type conversion -->
<!-- Category: Real-World Patterns -->
<q:component name="DumpRealworldDebugTypeConversion" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="stringNum" value="42" />
  <q:set var="intNum" value="42" operation="json" />
  <q:dump var="{stringNum}" label="String Number" />
  <q:dump var="{intNum}" label="Integer Number" />

  <q:return value="Dumped" />
</q:component>
