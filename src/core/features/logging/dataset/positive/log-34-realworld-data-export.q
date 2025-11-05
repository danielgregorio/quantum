<!-- Positive: Real-world data export audit log -->
<!-- Category: Real-World Patterns -->
<q:component name="LogRealWorldDataExport" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="exportRequest" value='{"userId": 456, "dataType": "customer_records", "recordCount": 1250, "format": "CSV"}' operation="json" />

  <q:log level="info"
         message="Data export requested by user {exportRequest.userId}"
         context="{exportRequest}" />

  <q:return value="Export logged" />
</q:component>
