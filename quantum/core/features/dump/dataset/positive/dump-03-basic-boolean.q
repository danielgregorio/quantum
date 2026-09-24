<!-- Positive: Dump basic boolean variable -->
<!-- Category: Basic Patterns -->
<q:component name="DumpBasicBoolean" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="isActive" value="true" operation="json" />
  <q:dump var="{isActive}" />

  <q:return value="Dumped" />
</q:component>
