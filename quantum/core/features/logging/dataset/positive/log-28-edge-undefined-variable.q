<!-- Positive: Logging with undefined variable reference -->
<!-- Category: Edge Cases -->
<q:component name="LogEdgeUndefinedVariable" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:log level="warning" message="Variable: {undefinedVar}" />

  <q:return value="Undefined var logged" />
</q:component>
