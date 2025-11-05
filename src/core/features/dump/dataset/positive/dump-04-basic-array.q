<!-- Positive: Dump basic array -->
<!-- Category: Basic Patterns -->
<q:component name="DumpBasicArray" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="colors" value='["red", "green", "blue"]' operation="json" />
  <q:dump var="{colors}" />

  <q:return value="Dumped" />
</q:component>
