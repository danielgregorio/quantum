<!-- Positive: Complex distributed tracing with correlation IDs -->
<!-- Category: Complex Scenarios -->
<q:component name="LogComplexDistributedTrace" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="correlationId" value="CORR-ABC-123" />
  <q:set var="spanId" value="SPAN-001" />

  <q:log level="trace"
         message="[{correlationId}] Request started"
         context='{"correlationId": {correlationId}, "spanId": {spanId}}' />

  <q:invoke name="userService"
            url="https://api.example.com/users/123"
            method="GET" />
  <q:log level="trace"
         message="[{correlationId}] User service called"
         context='{"correlationId": {correlationId}, "service": "user", "duration": {userService_result.loadTime}}' />

  <q:invoke name="orderService"
            url="https://api.example.com/orders"
            method="GET" />
  <q:log level="trace"
         message="[{correlationId}] Order service called"
         context='{"correlationId": {correlationId}, "service": "order", "duration": {orderService_result.loadTime}}' />

  <q:log level="info"
         message="[{correlationId}] Request completed successfully"
         context='{"correlationId": {correlationId}, "totalDuration": {userService_result.loadTime + orderService_result.loadTime}}' />

  <q:return value="Trace complete" />
</q:component>
