<!-- Positive: Logging with when condition that's false (should not log) -->
<!-- Category: Edge Cases -->
<q:component name="LogEdgeWhenFalse" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="shouldLog" value="false" operation="json" />
  <q:log level="info" message="This should not be logged" when="{shouldLog}" />
  <q:log level="info" message="This should be logged" when="{!shouldLog}" />

  <q:return value="Conditional logging tested" />
</q:component>
