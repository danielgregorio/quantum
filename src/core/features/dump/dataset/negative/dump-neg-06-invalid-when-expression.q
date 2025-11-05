<!-- Negative: Invalid when expression -->
<!-- Expected error: Invalid expression in 'when' attribute -->
<q:component name="DumpNegInvalidWhenExpression" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="data" value="test" />
  <q:dump var="{data}" when="{invalid syntax}" />

  <q:return value="Error" />
</q:component>
