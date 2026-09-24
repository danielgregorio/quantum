<!-- Positive: Dump API response -->
<!-- Category: Integration Patterns -->
<q:component name="DumpIntegrationApiResponse" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:invoke name="api" url="https://api.example.com/data" method="GET" />
  <q:dump var="{api}" label="API Response" />

  <q:return value="Dumped" />
</q:component>
