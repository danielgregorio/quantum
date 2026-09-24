<!-- Positive: Complex retry logic with logging -->
<!-- Category: Complex Scenarios -->
<q:component name="LogComplexRetryLogic" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="maxRetries" value="3" />
  <q:set var="attempt" value="0" />

  <q:loop var="retry" in='[1, 2, 3]'>
    <q:set var="attempt" value="{attempt + 1}" operation="increment" />
    <q:log level="debug" message="Attempt {attempt} of {maxRetries}" />

    <q:invoke name="api" url="https://api.example.com/unreliable" method="GET" />

    <q:log level="warning"
           message="Attempt {attempt} failed, retrying..."
           when="{!api_result.success AND attempt < maxRetries}" />

    <q:log level="error"
           message="All {maxRetries} attempts failed"
           when="{!api_result.success AND attempt == maxRetries}"
           context="{api_result.error}" />

    <q:log level="info"
           message="Succeeded on attempt {attempt}"
           when="{api_result.success}" />
  </q:loop>

  <q:return value="{api_result.success}" />
</q:component>
