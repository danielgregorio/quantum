<!-- Positive: Logging event dispatch -->
<!-- Category: Integration Patterns -->
<q:component name="LogIntegrationEventDispatch" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="userId" value="123" />
  <q:log level="info" message="Dispatching login event for user {userId}" />

  <q:dispatch-event name="user-login" data='{"userId": {userId}}' />

  <q:log level="debug" message="Event dispatched successfully" />

  <q:return value="Event logged" />
</q:component>
