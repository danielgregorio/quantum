<!-- Negative: Invalid 'when' expression syntax -->
<!-- Expected error: Invalid expression in 'when' attribute -->
<q:component name="LogNegInvalidWhenExpression" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:log level="info" message="Test" when="{invalid syntax here}" />

  <q:return value="Error" />
</q:component>
