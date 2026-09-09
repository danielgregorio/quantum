<!-- Positive: Dump computed value -->
<!-- Category: Integration Patterns -->
<q:component name="DumpIntegrationComputedValue" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="price" value="100" />
  <q:set var="tax" value="{price * 0.1}" operation="multiply" />
  <q:dump var="{tax}" label="Tax Amount" />

  <q:return value="Dumped" />
</q:component>
