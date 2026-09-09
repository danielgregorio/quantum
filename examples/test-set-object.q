<!-- Test Set Object -->
<q:component name="TestSetObject" xmlns:q="https://quantum.lang/ns">
  <!-- Teste: operações em objects -->
  <q:set name="user" type="object" value="{}" />
  <q:set name="user" operation="merge" value='{"name":"Daniel"}' />
  <q:set name="user" operation="merge" value='{"age":30}' />
  <q:return value="User: {user}" />
</q:component>
