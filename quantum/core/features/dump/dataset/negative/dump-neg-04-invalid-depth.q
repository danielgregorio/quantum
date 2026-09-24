<!-- Negative: Invalid depth value -->
<!-- Expected error: Dump depth must be a positive integer -->
<q:component name="DumpNegInvalidDepth" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="data" value="test" />
  <q:dump var="{data}" depth="not-a-number" />

  <q:return value="Error" />
</q:component>
