<!-- Negative: Self-closing tag with invalid syntax -->
<!-- Expected error: Log tag must be self-closing or properly closed -->
<q:component name="LogNegSelfClosingTag" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:log level="info" message="Test">
    <!-- Log should not have child elements -->
  </q:log>

  <q:return value="Error" />
</q:component>
