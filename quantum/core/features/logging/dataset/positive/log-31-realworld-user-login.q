<!-- Positive: Real-world user login tracking -->
<!-- Category: Real-World Patterns -->
<q:component name="LogRealWorldUserLogin" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="user" value='{"id": 123, "email": "alice@example.com", "ip": "192.168.1.1"}' operation="json" />

  <q:log level="info"
         message="User login: {user.email}"
         context='{"userId": {user.id}, "ip": {user.ip}, "timestamp": "2025-01-15T10:30:00Z"}' />

  <q:return value="Login tracked" />
</q:component>
