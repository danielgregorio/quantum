<!-- Test Set Loop Debug -->
<q:component name="TestSetLoopDebug" xmlns:q="https://quantum.lang/ns">
  <q:set name="total" type="number" value="0" scope="component" />

  <q:loop type="range" var="i" from="1" to="3">
    <q:set name="total" operation="add" value="1" scope="component" />
  </q:loop>

  <q:return value="Total: {total}" />
</q:component>
