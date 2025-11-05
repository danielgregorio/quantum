<!-- Negative: Negative depth value -->
<!-- Expected error: Dump depth must be a positive integer -->
<q:component name="DumpNegNegativeDepth" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="data" value="test" />
  <q:dump var="{data}" depth="-1" />

  <q:return value="Error" />
</q:component>
