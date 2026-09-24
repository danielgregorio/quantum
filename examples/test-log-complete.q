<!-- Test Log Complete -->
<!-- Demonstrates all q:log patterns for debugging -->
<q:component name="TestLogComplete" xmlns:q="https://quantum.lang/ns">

  <q:set name="user" value="John" />
  <q:set name="count" type="number" value="42" />
  <q:set name="items" type="array" value='["a", "b", "c"]' />

  <!-- Simple log message -->
  <q:log message="Application started" level="info" />

  <!-- Log with variable binding -->
  <q:log message="User {user} logged in with count {count}" level="info" />

  <!-- Log with level -->
  <q:log message="Debug information" level="debug" />
  <q:log message="Info message" level="info" />
  <q:log message="Warning message" level="warning" />
  <q:log message="Error occurred" level="error" />

  <!-- Log with category -->
  <q:log message="Authentication check" category="auth" level="info" />
  <q:log message="Database query" category="database" level="debug" />

  <!-- Log array/object data -->
  <q:log message="Items: {items}" level="debug" />

  <q:return value="Logging complete for user: {user}" />
</q:component>
