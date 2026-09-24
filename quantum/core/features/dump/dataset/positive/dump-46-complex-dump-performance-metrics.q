<!-- Positive: Dump performance metrics with metadata -->
<!-- Category: Complex Scenarios -->
<q:component name="DumpComplexDumpPerformanceMetrics" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="data" source="data/large.csv" type="csv">
    <q:column name="id" type="integer" />
  </q:data>
  <q:dump var="{data_result}" label="Performance Metrics" />

  <q:return value="Dumped" />
</q:component>
