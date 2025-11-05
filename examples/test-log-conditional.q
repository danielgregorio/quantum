<!-- Test Conditional Logging -->
<q:component name="TestLogConditional" xmlns:q="https://quantum.lang/ns">
  <q:param name="debug" type="boolean" default="true" />
  <q:param name="errorOccurred" type="boolean" default="false" />

  <q:log level="debug" message="Debug mode enabled" when="{debug}" />
  <q:log level="error" message="An error occurred in processing" when="{errorOccurred}" />
  <q:log level="info" message="Processing completed" />

  <q:return value="Conditional logging test completed" />
</q:component>
