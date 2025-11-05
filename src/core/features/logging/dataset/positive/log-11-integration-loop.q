<!-- Positive: Logging inside loop -->
<!-- Category: Integration Patterns -->
<q:component name="LogIntegrationLoop" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="items" value='[1, 2, 3]' operation="json" />

  <q:loop var="item" in="{items}">
    <q:log level="debug" message="Processing item {item}" />
  </q:loop>

  <q:return value="Loop logged" />
</q:component>
