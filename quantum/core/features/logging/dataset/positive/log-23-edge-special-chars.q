<!-- Positive: Logging with special characters in message -->
<!-- Category: Edge Cases -->
<q:component name="LogEdgeSpecialChars" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:log level="info" message="Special chars: &lt;&gt;&amp;&quot;'@#$%^&amp;*()" />

  <q:return value="Special chars logged" />
</q:component>
