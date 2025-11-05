<!-- Negative: Invalid JSON in context attribute -->
<!-- Expected error: Invalid JSON in 'context' attribute -->
<q:component name="LogNegInvalidContextJSON" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:log level="info" message="Test" context="{invalid json structure}" />

  <q:return value="Error" />
</q:component>
