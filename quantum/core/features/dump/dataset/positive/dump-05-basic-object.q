<!-- Positive: Dump basic object -->
<!-- Category: Basic Patterns -->
<q:component name="DumpBasicObject" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:set var="user" value='{"id": 1, "name": "Alice", "email": "alice@example.com"}' operation="json" />
  <q:dump var="{user}" />

  <q:return value="Dumped" />
</q:component>
