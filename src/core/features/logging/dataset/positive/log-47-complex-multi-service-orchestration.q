<!-- Positive: Complex multi-service orchestration logging -->
<!-- Category: Complex Scenarios -->
<q:component name="LogComplexMultiServiceOrchestration" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:log level="info" message="Starting multi-service orchestration" />

  <q:invoke name="inventory" url="https://api.example.com/inventory" method="GET" />
  <q:invoke name="pricing" url="https://api.example.com/pricing" method="GET" />
  <q:invoke name="shipping" url="https://api.example.com/shipping" method="GET" />

  <q:set var="allSuccess" value="{inventory_result.success AND pricing_result.success AND shipping_result.success}" />

  <q:log level="info"
         message="All services responded successfully"
         when="{allSuccess}"
         context='{"inventory": {inventory_result.success}, "pricing": {pricing_result.success}, "shipping": {shipping_result.success}}' />

  <q:log level="error"
         message="One or more services failed"
         when="{!allSuccess}"
         context='{"inventory": {inventory_result}, "pricing": {pricing_result}, "shipping": {shipping_result}}' />

  <q:return value="{allSuccess}" />
</q:component>
