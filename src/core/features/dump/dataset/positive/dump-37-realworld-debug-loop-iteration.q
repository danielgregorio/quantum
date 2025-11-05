<!-- Positive: Debug specific loop iteration -->
<!-- Category: Real-World Patterns -->
<q:component name="DumpRealworldDebugLoopIteration" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="items" value='[{"id": 1, "value": 10}, {"id": 2, "value": 20}]' operation="json" />
  <q:loop var="item" in="{items}">
    <q:dump var="{item}" when="{item.value > 15}" label="High Value Item" />
  </q:loop>

  <q:return value="Dumped" />
</q:component>
