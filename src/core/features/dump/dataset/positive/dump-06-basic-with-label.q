<!-- Positive: Dump with label attribute -->
<!-- Category: Basic Patterns -->
<q:component name="DumpBasicWithLabel" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="data" value="test" />
  <q:dump var="{data}" label="Test Data" />

  <q:return value="Dumped" />
</q:component>
