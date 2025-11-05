<q:component name="DebugScopes">
  <!-- Dump the execution context to see what's available -->
  <q:dump var="session" label="Session Scope" />
  <q:dump var="application" label="Application Scope" />
  <q:dump var="request" label="Request Scope" />

  <!-- Try setting a session variable -->
  <q:set name="session.test" value="test123" />

  <!-- Dump again after setting -->
  <q:dump var="session" label="Session After Set" />

  <html>
  <head><title>Debug</title></head>
  <body>
    <h1>Debug Scopes</h1>
    <p>Check server console for dump output</p>
  </body>
  </html>
</q:component>
