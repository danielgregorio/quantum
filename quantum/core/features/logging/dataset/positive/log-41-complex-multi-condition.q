<!-- Positive: Complex multi-condition logging -->
<!-- Category: Complex Scenarios -->
<q:component name="LogComplexMultiCondition" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:invoke name="api" url="https://api.example.com/data" method="GET" />

  <q:log level="critical"
         message="API failure with slow response"
         when="{!api_result.success AND api_result.loadTime > 2000}"
         context="{api_result}" />

  <q:log level="warning"
         message="API slow but successful"
         when="{api_result.success AND api_result.loadTime > 1000}"
         context='{"loadTime": {api_result.loadTime}}' />

  <q:log level="info"
         message="API fast and successful"
         when="{api_result.success AND api_result.loadTime <= 1000}" />

  <q:return value="{api_result.success}" />
</q:component>
