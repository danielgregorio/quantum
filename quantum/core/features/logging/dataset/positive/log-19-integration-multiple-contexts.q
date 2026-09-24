<!-- Positive: Logging with multiple structured contexts -->
<!-- Category: Integration Patterns -->
<q:component name="LogIntegrationMultipleContexts" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="user" value='{"id": 1, "name": "Alice"}' operation="json" />
  <q:set var="request" value='{"method": "POST", "path": "/api/login"}' operation="json" />

  <q:log level="info"
         message="User login attempt"
         context='{"user": {user}, "request": {request}}' />

  <q:return value="Multi-context logged" />
</q:component>
