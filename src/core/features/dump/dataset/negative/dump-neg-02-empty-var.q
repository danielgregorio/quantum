<!-- Negative: Empty var attribute -->
<!-- Expected error: Dump var attribute cannot be empty -->
<q:component name="DumpNegEmptyVar" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="data" value="test" />
  <q:dump var="" />

  <q:return value="Error" />
</q:component>
