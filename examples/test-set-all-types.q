<!-- Test Set All Types -->
<!-- Demonstrates all valid q:set types -->
<q:component name="TestSetAllTypes" xmlns:q="https://quantum.lang/ns">

  <!-- String type (default) -->
  <q:set name="name" type="string" value="John Doe" />

  <!-- Number type -->
  <q:set name="age" type="number" value="30" />

  <!-- Decimal type -->
  <q:set name="price" type="decimal" value="19.99" />

  <!-- Boolean type -->
  <q:set name="active" type="boolean" value="true" />
  <q:set name="inactive" type="boolean" value="false" />

  <!-- Date type -->
  <q:set name="birthday" type="date" value="1990-01-15" />

  <!-- DateTime type -->
  <q:set name="createdAt" type="datetime" value="2025-01-15 10:30:00" />

  <!-- Array type -->
  <q:set name="colors" type="array" value='["red", "green", "blue"]' />

  <!-- Object type -->
  <q:set name="config" type="object" value='{"debug": true, "timeout": 30}' />

  <!-- JSON type -->
  <q:set name="data" type="json" value='{"items": [1, 2, 3]}' />

  <!-- Null type -->
  <q:set name="empty" type="null" value="" />

  <q:return value="Name: {name}, Age: {age}, Price: {price}, Active: {active}" />
</q:component>
