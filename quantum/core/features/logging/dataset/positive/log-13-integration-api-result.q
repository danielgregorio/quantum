<!-- Positive: Logging API result with when attribute -->
<!-- Category: Integration Patterns -->
<q:component name="LogIntegrationAPIResult" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:invoke name="api" url="https://api.example.com/data" method="GET" />

  <q:log level="error"
         message="API call failed: {api_result.error.message}"
         when="{!api_result.success}"
         context="{api_result}" />

  <q:log level="info"
         message="API call succeeded"
         when="{api_result.success}" />

  <q:return value="{api_result.success}" />
</q:component>
