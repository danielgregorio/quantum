<!-- Positive: Real-world batch job processing log -->
<!-- Category: Real-World Patterns -->
<q:component name="LogRealWorldBatchProcessing" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="batchStats" value='{"jobId": "BATCH-789", "processed": 5000, "failed": 12, "duration": 45.2}' operation="json" />

  <q:log level="info"
         message="Batch job {batchStats.jobId} completed: {batchStats.processed} processed, {batchStats.failed} failed"
         context="{batchStats}" />

  <q:return value="Batch logged" />
</q:component>
