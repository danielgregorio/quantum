<!-- Negative: Missing required var attribute -->
<!-- Expected error: Dump requires 'var' attribute -->
<q:component name="DumpNegMissingVar" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="data" value="test" />
  <q:dump />

  <q:return value="Error" />
</q:component>
