<!-- Test Simple Databinding -->
<q:component name="TestDatabinding" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="3">
    <q:return value="Number {i}" />
  </q:loop>
</q:component>