<!-- Positive: Complex data pipeline with stage logging -->
<!-- Category: Complex Scenarios -->
<q:component name="LogComplexDataPipeline" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:log level="info" message="Pipeline stage 1: Data extraction" />
  <q:data name="rawData" source="data/raw.csv" type="csv">
    <q:column name="value" type="integer" />
  </q:data>
  <q:log level="debug" message="Extracted {rawData_result.recordCount} records" />

  <q:log level="info" message="Pipeline stage 2: Data transformation" />
  <q:data name="transformed" source="{rawData}" type="transform">
    <q:transform>
      <q:filter condition="{value > 100}" />
    </q:transform>
  </q:data>
  <q:log level="debug" message="Filtered to {transformed_result.recordCount} records" />

  <q:log level="info" message="Pipeline stage 3: Data aggregation" />
  <q:set var="total" value="0" />
  <q:loop var="item" in="{transformed}">
    <q:set var="total" value="{total + item.value}" operation="add" />
  </q:loop>
  <q:log level="debug" message="Aggregated total: {total}" />

  <q:log level="info"
         message="Pipeline completed successfully"
         context='{"stages": 3, "finalCount": {transformed_result.recordCount}, "total": {total}}' />

  <q:return value="{total}" />
</q:component>
