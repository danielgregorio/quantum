<!-- Negative: Invalid format attribute -->
<!-- Expected error: Invalid dump format 'invalid'. Must be one of: html, json, text -->
<q:component name="DumpNegInvalidFormat" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="data" value="test" />
  <q:dump var="{data}" format="invalid" />

  <q:return value="Error" />
</q:component>
