<!-- Test Set All Scopes -->
<!-- Demonstrates all variable scopes: variables, session, application, request -->
<q:component name="TestSetAllScopes" xmlns:q="https://quantum.lang/ns">

  <!-- Local variables (component scope - default) -->
  <q:set name="localVar" value="I am local" />
  <q:set name="counter" type="number" value="1" />

  <!-- Request scope (lasts for single HTTP request) -->
  <q:set name="request.requestId" value="REQ-12345" />
  <q:set name="request.startTime" value="2025-01-15 10:00:00" />

  <!-- Session scope (user-specific, persists across requests) -->
  <q:set name="session.userId" value="user-001" />
  <q:set name="session.username" value="johndoe" />
  <q:set name="session.loginTime" value="2025-01-15 09:00:00" />

  <!-- Application scope (global, shared across all users) -->
  <q:set name="application.appName" value="MyApp" />
  <q:set name="application.version" value="1.0.0" />
  <q:set name="application.startupTime" value="2025-01-15 08:00:00" />

  <q:return value="Local: {localVar}, Request: {request.requestId}, Session: {session.username}, App: {application.appName}" />
</q:component>
