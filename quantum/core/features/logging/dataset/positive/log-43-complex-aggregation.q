<!-- Positive: Complex aggregation with logging -->
<!-- Category: Complex Scenarios -->
<q:component name="LogComplexAggregation" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="orders" value='[{"id": 1, "total": 100}, {"id": 2, "total": 200}, {"id": 3, "total": 150}]' operation="json" />
  <q:set var="grandTotal" value="0" />
  <q:set var="processedCount" value="0" />

  <q:loop var="order" in="{orders}">
    <q:set var="grandTotal" value="{grandTotal + order.total}" operation="add" />
    <q:set var="processedCount" value="{processedCount + 1}" operation="increment" />
    <q:log level="trace" message="Order {order.id}: ${order.total}" />
  </q:loop>

  <q:log level="info"
         message="Processed {processedCount} orders, grand total: ${grandTotal}"
         context='{"count": {processedCount}, "total": {grandTotal}}' />

  <q:return value="{grandTotal}" />
</q:component>
