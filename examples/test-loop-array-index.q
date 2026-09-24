<!-- Test Array Loop with Index -->
<q:component name="TestArrayLoopIndex" xmlns:q="https://quantum.lang/ns">
  <q:loop type="array" var="fruit" index="idx" items='["apple", "banana", "orange"]'>
    <q:return value="Item" />
  </q:loop>
</q:component>