<!-- Positive: Inspect aggregated result -->
<!-- Category: Real-World Patterns -->
<q:component name="DumpRealworldInspectAggregatedResult" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="orders" value='[{"total": 100}, {"total": 200}, {"total": 150}]' operation="json" />
  <q:set var="sum" value="0" />
  <q:loop var="order" in="{orders}">
    <q:set var="sum" value="{sum + order.total}" operation="add" />
  </q:loop>
  <q:dump var="{sum}" label="Total Revenue" />

  <q:return value="Dumped" />
</q:component>
