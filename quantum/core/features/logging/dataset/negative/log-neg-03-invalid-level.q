<!-- Negative: Invalid log level -->
<!-- Expected error: Invalid log level 'invalid'. Must be one of: trace, debug, info, warning, error, critical -->
<q:component name="LogNegInvalidLevel" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:log level="invalid" message="Invalid level test" />

  <q:return value="Error" />
</q:component>
