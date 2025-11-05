<!-- Positive: Dump very large array -->
<!-- Category: Edge Cases -->
<q:component name="DumpEdgeVeryLargeArray" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="large" value='[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]' operation="json" />
  <q:dump var="{large}" label="Large Array" />

  <q:return value="Dumped" />
</q:component>
