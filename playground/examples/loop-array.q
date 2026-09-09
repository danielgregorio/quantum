<!-- Loop Example (Array) -->
<q:component name="ArrayLoop">
  <q:set name="fruits" type="array" value="Apple,Banana,Cherry,Date,Elderberry" />

  <h2>Fruit List</h2>
  <ul>
    <q:loop type="list" var="fruit" items="{fruits}" index="idx">
      <li>{idx}: {fruit}</li>
    </q:loop>
  </ul>
</q:component>
