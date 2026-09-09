<!-- Positive: Complex performance metrics collection -->
<!-- Category: Complex Scenarios -->
<q:component name="LogComplexPerformanceMetrics" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="users" source="data/large_dataset.csv" type="csv">
    <q:column name="id" type="integer" />
  </q:data>

  <q:set var="processingStart" value="0" />
  <q:set var="processed" value="0" />

  <q:loop var="user" in="{users}">
    <q:set var="processed" value="{processed + 1}" operation="increment" />
  </q:loop>

  <q:log level="info"
         message="Performance metrics: {processed} records in {users_result.loadTime}ms"
         context='{"recordCount": {processed}, "loadTime": {users_result.loadTime}, "throughput": {processed / users_result.loadTime}}' />

  <q:return value="{processed}" />
</q:component>
