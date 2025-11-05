<!-- Positive: Real-world error recovery logging -->
<!-- Category: Real-World Patterns -->
<q:component name="LogRealWorldErrorRecovery" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:invoke name="primaryAPI" url="https://api-primary.example.com/data" method="GET" />

  <q:log level="warning"
         message="Primary API failed, attempting fallback"
         when="{!primaryAPI_result.success}"
         context="{primaryAPI_result.error}" />

  <q:invoke name="fallbackAPI"
            url="https://api-fallback.example.com/data"
            method="GET"
            when="{!primaryAPI_result.success}" />

  <q:log level="info"
         message="Fallback API succeeded"
         when="{fallbackAPI_result.success}" />

  <q:return value="Recovery logged" />
</q:component>
