<!-- Positive: Dump all context variables -->
<!-- Category: Integration Patterns -->
<q:component name="DumpIntegrationAllContextVars" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="a" value="1" />
  <q:set var="b" value="2" />
  <q:set var="c" value="3" />
  <q:dump var="{a}" label="Var A" />
  <q:dump var="{b}" label="Var B" />
  <q:dump var="{c}" label="Var C" />

  <q:return value="Dumped" />
</q:component>
