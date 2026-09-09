<q:component name="TestRequestScope">
  <!-- Test: Request-scoped variables (metadata for current request) -->

  <q:set name="request.processedAt" value="2025-11-05 14:30:00" />

  <!-- Expected: Request variables available for current request only -->
  Request method: {request.method}
  Request path: {request.path}
  Request processed at: {request.processedAt}
  User agent: {request.user_agent}
</q:component>
