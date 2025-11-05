<!-- Positive: Logging function execution -->
<!-- Category: Integration Patterns -->
<q:component name="LogIntegrationFunctionCall" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:function name="calculateTotal" params="price,quantity">
    <q:log level="debug" message="Calculating total for {price} x {quantity}" />
    <q:set var="total" value="{price * quantity}" operation="multiply" />
    <q:return value="{total}" />
  </q:function>

  <q:set var="result" value="{calculateTotal(100, 5)}" operation="function" />
  <q:log level="info" message="Total calculated: {result}" />

  <q:return value="{result}" />
</q:component>
