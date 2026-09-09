<!-- Negative: Empty level attribute -->
<!-- Expected error: Log level cannot be empty -->
<q:component name="LogNegEmptyLevel" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:log level="" message="Empty level test" />

  <q:return value="Error" />
</q:component>
