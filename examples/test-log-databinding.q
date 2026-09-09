<!-- Test Logging with Databinding -->
<q:component name="TestLogDatabinding" xmlns:q="https://quantum.lang/ns">
  <q:param name="username" type="string" default="testuser" />
  <q:param name="orderId" type="integer" default="12345" />

  <q:log level="info" message="User {username} placed order #{orderId}" />
  <q:log level="debug" message="Order ID: {orderId}" />

  <q:return value="User: {username}" />
</q:component>
