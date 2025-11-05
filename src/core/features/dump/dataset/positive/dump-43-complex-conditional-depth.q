<!-- Positive: Conditional dump with varying depth -->
<!-- Category: Complex Scenarios -->
<q:component name="DumpComplexConditionalDepth" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="complex" value='{"level1": {"level2": {"level3": {"level4": "deep"}}}}' operation="json" />
  <q:set var="showFull" value="false" operation="json" />
  <q:dump var="{complex}" depth="2" when="{!showFull}" label="Shallow" />
  <q:dump var="{complex}" depth="10" when="{showFull}" label="Deep" />

  <q:return value="Dumped" />
</q:component>
