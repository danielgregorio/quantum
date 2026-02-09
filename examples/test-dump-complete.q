<!-- Test Dump Complete -->
<!-- Demonstrates all q:dump patterns for debugging output -->
<q:component name="TestDumpComplete" xmlns:q="https://quantum.lang/ns">

  <q:set name="simpleVar" value="Hello World" />
  <q:set name="number" type="number" value="42" />
  <q:set name="flag" type="boolean" value="true" />
  <q:set name="items" type="array" value='["apple", "banana", "cherry"]' />
  <q:set name="user" type="object" value='{"name": "John", "age": 30, "active": true}' />

  <!-- Dump single variable -->
  <q:dump var="simpleVar" />

  <!-- Dump with label -->
  <q:dump var="number" label="The magic number" />

  <!-- Dump array -->
  <q:dump var="items" label="Fruit list" />

  <!-- Dump object -->
  <q:dump var="user" label="User object" />

  <!-- Dump with different output formats -->
  <q:dump var="user" format="json" />
  <q:dump var="user" format="text" />
  <q:dump var="user" format="html" />

  <!-- Conditional dump -->
  <q:if condition="flag == true">
    <q:dump var="flag" label="Flag is true" />
  </q:if>

  <q:return value="Dump complete" />
</q:component>
