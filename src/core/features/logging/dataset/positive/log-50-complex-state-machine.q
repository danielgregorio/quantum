<!-- Positive: Complex state machine with transition logging -->
<!-- Category: Complex Scenarios -->
<q:component name="LogComplexStateMachine" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="state" value="pending" />
  <q:set var="event" value="approve" />

  <q:log level="info" message="State machine: {state} -> {event}" />

  <q:if condition="{state == 'pending' AND event == 'approve'}">
    <q:set var="state" value="approved" />
    <q:log level="info"
           message="State transition: pending -> approved"
           context='{"from": "pending", "to": "approved", "event": {event}}' />
  </q:if>

  <q:if condition="{state == 'approved' AND event == 'process'}">
    <q:set var="state" value="processing" />
    <q:log level="info"
           message="State transition: approved -> processing"
           context='{"from": "approved", "to": "processing", "event": {event}}' />
  </q:if>

  <q:if condition="{state == 'processing' AND event == 'complete'}">
    <q:set var="state" value="completed" />
    <q:log level="info"
           message="State transition: processing -> completed"
           context='{"from": "processing", "to": "completed", "event": {event}}' />
  </q:if>

  <q:log level="info" message="Final state: {state}" />

  <q:return value="{state}" />
</q:component>
