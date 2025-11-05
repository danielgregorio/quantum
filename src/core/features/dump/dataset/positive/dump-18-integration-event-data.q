<!-- Positive: Dump event data -->
<!-- Category: Integration Patterns -->
<q:component name="DumpIntegrationEventData" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="eventData" value='{"type": "click", "target": "button"}' operation="json" />
  <q:dispatch-event name="user-action" data="{eventData}" />
  <q:dump var="{eventData}" label="Event Data" />

  <q:return value="Dumped" />
</q:component>
