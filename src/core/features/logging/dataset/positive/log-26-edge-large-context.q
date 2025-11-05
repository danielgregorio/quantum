<!-- Positive: Logging with very large context object -->
<!-- Category: Edge Cases -->
<q:component name="LogEdgeLargeContext" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="largeData" value='{"items": [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20], "metadata": {"total": 20, "page": 1, "size": 20}}' operation="json" />
  <q:log level="debug" message="Large dataset processed" context="{largeData}" />

  <q:return value="Large context logged" />
</q:component>
