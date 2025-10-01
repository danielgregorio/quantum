<!-- Test Databinding with Arithmetic -->
<q:component name="TestDatabindingArithmetic" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="3">
    <q:return value="Item {i}, Next: {i + 1}" />
  </q:loop>
</q:component>