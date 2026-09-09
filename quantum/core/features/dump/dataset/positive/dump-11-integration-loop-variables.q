<!-- Positive: Dump loop variables -->
<!-- Category: Integration Patterns -->
<q:component name="DumpIntegrationLoopVariables" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="items" value='[1, 2, 3]' operation="json" />
  <q:loop var="item" in="{items}">
    <q:dump var="{item}" label="Loop Item" />
  </q:loop>

  <q:return value="Dumped" />
</q:component>
