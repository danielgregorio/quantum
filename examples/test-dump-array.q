<!-- Test Dump with Array -->
<q:component name="TestDumpArray" xmlns:q="https://quantum.lang/ns">
  <q:param name="items" type="array" default='["item1", "item2", "item3"]' />

  <q:dump var="{items}" label="Items Array" format="text" depth="5" />

  <q:return value="Array dump completed" />
</q:component>
