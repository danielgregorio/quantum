<!-- Positive: Dump data from nested loops -->
<!-- Category: Complex Scenarios -->
<q:component name="DumpComplexDumpNestedLoopData" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="matrix" value='[[1,2,3],[4,5,6],[7,8,9]]' operation="json" />
  <q:loop var="row" in="{matrix}">
    <q:dump var="{row}" label="Row Data" />
  </q:loop>

  <q:return value="Dumped" />
</q:component>
