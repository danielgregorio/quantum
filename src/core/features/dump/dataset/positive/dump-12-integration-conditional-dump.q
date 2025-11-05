<!-- Positive: Conditional dump with when -->
<!-- Category: Integration Patterns -->
<q:component name="DumpIntegrationConditionalDump" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="error" value="true" operation="json" />
  <q:set var="errorMsg" value="Something failed" />
  <q:dump var="{errorMsg}" when="{error}" label="Error State" />

  <q:return value="Dumped" />
</q:component>
