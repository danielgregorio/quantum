<!-- Positive: Dump nested object -->
<!-- Category: Basic Patterns -->
<q:component name="DumpBasicNestedObject" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="nested" value='{"user": {"name": "Bob", "address": {"city": "NYC"}}}' operation="json" />
  <q:dump var="{nested}" />

  <q:return value="Dumped" />
</q:component>
