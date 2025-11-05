<!-- Positive: Dump empty string -->
<!-- Category: Edge Cases -->
<q:component name="DumpEdgeEmptyString" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="empty" value="" />
  <q:dump var="{empty}" label="Empty String" />

  <q:return value="Dumped" />
</q:component>
