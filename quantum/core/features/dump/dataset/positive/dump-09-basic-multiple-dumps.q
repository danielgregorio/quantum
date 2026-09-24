<!-- Positive: Multiple dump statements -->
<!-- Category: Basic Patterns -->
<q:component name="DumpBasicMultipleDumps" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="x" value="10" />
  <q:set var="y" value="20" />
  <q:dump var="{x}" label="X Value" />
  <q:dump var="{y}" label="Y Value" />

  <q:return value="Dumped" />
</q:component>
