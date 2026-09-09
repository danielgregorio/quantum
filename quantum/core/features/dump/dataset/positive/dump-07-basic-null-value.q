<!-- Positive: Dump null value -->
<!-- Category: Basic Patterns -->
<q:component name="DumpBasicNullValue" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="nullVal" value="null" operation="json" />
  <q:dump var="{nullVal}" />

  <q:return value="Dumped" />
</q:component>
