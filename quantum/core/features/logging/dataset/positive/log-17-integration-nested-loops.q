<!-- Positive: Logging in nested loops -->
<!-- Category: Integration Patterns -->
<q:component name="LogIntegrationNestedLoops" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="orders" value='[{"id": 1, "items": [10, 20]}, {"id": 2, "items": [30]}]' operation="json" />

  <q:loop var="order" in="{orders}">
    <q:log level="debug" message="Processing order {order.id}" />
    <q:loop var="item" in="{order.items}">
      <q:log level="trace" message="Order {order.id} item: {item}" />
    </q:loop>
  </q:loop>

  <q:return value="Nested loops logged" />
</q:component>
