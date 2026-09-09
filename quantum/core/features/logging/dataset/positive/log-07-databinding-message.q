<!-- Positive: Logging with databinding in message -->
<!-- Category: Basic Patterns -->
<q:component name="LogDatabindingMessage" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="userName" value="Alice" />
  <q:log level="info" message="User {userName} logged in" />

  <q:return value="Logged" />
</q:component>
