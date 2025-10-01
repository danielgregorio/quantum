<!-- Test Databinding with Array Loop -->
<q:component name="TestDatabindingArray" xmlns:q="https://quantum.lang/ns">
  <q:loop type="array" var="fruit" index="idx" items='["apple", "banana", "orange"]'>
    <q:return value="{idx}: {fruit}" />
  </q:loop>
</q:component>