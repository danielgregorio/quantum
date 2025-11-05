<!-- Negative: Missing required 'level' attribute -->
<!-- Expected error: Log requires 'level' attribute -->
<q:component name="LogNegMissingLevel" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:log message="This is missing a level" />

  <q:return value="Error" />
</q:component>
