<!-- Positive: Dump results of chained operations -->
<!-- Category: Complex Scenarios -->
<q:component name="DumpComplexDumpChainResults" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="input" value="100" />
  <q:dump var="{input}" label="Step 1: Input" />
  <q:set var="doubled" value="{input * 2}" operation="multiply" />
  <q:dump var="{doubled}" label="Step 2: Doubled" />
  <q:set var="final" value="{doubled + 50}" operation="add" />
  <q:dump var="{final}" label="Step 3: Final" />

  <q:return value="Dumped" />
</q:component>
