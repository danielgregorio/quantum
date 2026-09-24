<!-- Positive: Dump nested loop variables -->
<!-- Category: Integration Patterns -->
<q:component name="DumpIntegrationNestedLoopVars" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="matrix" value='[[1, 2], [3, 4]]' operation="json" />
  <q:loop var="row" in="{matrix}">
    <q:loop var="cell" in="{row}">
      <q:dump var="{cell}" label="Cell" />
    </q:loop>
  </q:loop>

  <q:return value="Dumped" />
</q:component>
