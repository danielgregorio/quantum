<!-- Test Set Increment -->
<q:component name="TestSetIncrement" xmlns:q="https://quantum.lang/ns">
  <!-- Teste: incremento -->
  <q:set name="counter" type="number" value="0" />
  <q:set name="counter" operation="increment" />
  <q:set name="counter" operation="increment" />
  <q:set name="counter" operation="increment" />
  <q:return value="Counter: {counter}" />
</q:component>
