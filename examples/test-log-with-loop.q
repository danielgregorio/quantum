<!-- Test Logging Inside Loop -->
<q:component name="TestLogWithLoop" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="3">
    <q:log level="info" message="Processing item {i}" />
    <q:return value="Item {i} processed" />
  </q:loop>
</q:component>
