<!-- Positive: Dump multiple API responses for comparison -->
<!-- Category: Complex Scenarios -->
<q:component name="DumpComplexDumpMultiApiResponses" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:invoke name="api1" url="https://api1.example.com/data" method="GET" />
  <q:invoke name="api2" url="https://api2.example.com/data" method="GET" />
  <q:dump var="{api1}" label="API 1 Response" />
  <q:dump var="{api2}" label="API 2 Response" />

  <q:return value="Dumped" />
</q:component>
