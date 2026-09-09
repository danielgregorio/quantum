<!-- Loop Example (Range) -->
<q:component name="RangeLoop">
  <q:set name="title" value="Counting to 5" />

  <h2>{title}</h2>
  <ul>
    <q:loop type="range" var="i" from="1" to="5">
      <li>Number {i}</li>
    </q:loop>
  </ul>
</q:component>
