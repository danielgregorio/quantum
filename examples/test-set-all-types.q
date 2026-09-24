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

  <!-- A date is ISO text (there is no date type; {now()} without type keeps the date, SET-5) -->
  <q:set name="birthday" value="1990-01-15" />
  <q:set name="createdAt" value="2025-01-15 10:30:00" />

  <!-- Array type -->
  <q:set name="colors" type="array" value='["red", "green", "blue"]' />

  <!-- Object type -->
  <q:set name="config" type="object" value='{"debug": true, "timeout": 30}' />

  <!-- JSON type -->
  <q:set name="data" type="json" value='{"items": [1, 2, 3]}' />

  <!-- An empty value (there is no null type) -->
  <q:set name="empty" value="" />

  <q:return value="Name: {name}, Age: {age}, Price: {price}, Active: {active}" />
</q:component>
