<!-- Positive: Real-world API latency monitoring -->
<!-- Category: Real-World Patterns -->
<q:component name="LogRealWorldAPILatency" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:invoke name="api" url="https://api.example.com/data" method="GET" />

  <q:log level="warning"
         message="Slow API response: {api_result.loadTime}ms"
         when="{api_result.loadTime > 1000}"
         context='{"url": "https://api.example.com/data", "duration": {api_result.loadTime}}' />

  <q:return value="{api_result.success}" />
</q:component>
