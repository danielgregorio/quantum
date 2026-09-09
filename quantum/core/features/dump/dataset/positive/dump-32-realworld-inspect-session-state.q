<!-- Positive: Inspect session state -->
<!-- Category: Real-World Patterns -->
<q:component name="DumpRealworldInspectSessionState" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="session" value='{"userId": 123, "role": "admin", "permissions": ["read", "write"]}' operation="json" />
  <q:dump var="{session}" label="Session State" />

  <q:return value="Dumped" />
</q:component>
