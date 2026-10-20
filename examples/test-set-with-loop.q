<!-- Test Set With Loop -->
<q:component name="TestSetWithLoop" xmlns:q="https://quantum.lang/ns">
  <!-- Test: set with a loop -->
  <q:set name="total" type="number" value="0" />

  <q:loop type="range" var="i" from="1" to="5">
    <q:set name="total" operation="add" value="{i}" />
  </q:loop>

  <q:return value="Total: {total}" />
</q:component>
