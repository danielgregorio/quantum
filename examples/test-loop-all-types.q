<!-- Test Loop All Types -->
<!-- Demonstrates all q:loop types -->
<q:component name="TestLoopAllTypes" xmlns:q="https://quantum.lang/ns">

  <q:set name="output" type="array" value="[]" />

  <!-- Range loop: from/to -->
  <q:set name="output" operation="append" value="Range loop:" />
  <q:loop type="range" var="i" from="1" to="3">
    <q:set name="output" operation="append" value="  i = {i}" />
  </q:loop>

  <!-- Range loop with step -->
  <q:set name="output" operation="append" value="Range with step:" />
  <q:loop type="range" var="n" from="0" to="10" step="2">
    <q:set name="output" operation="append" value="  n = {n}" />
  </q:loop>

  <!-- Array loop: iterating over array -->
  <q:set name="output" operation="append" value="Array loop:" />
  <q:loop type="array" var="fruit" items='["apple", "banana", "cherry"]'>
    <q:set name="output" operation="append" value="  fruit = {fruit}" />
  </q:loop>

  <!-- List loop: comma-separated string -->
  <q:set name="output" operation="append" value="List loop:" />
  <q:loop type="list" var="color" items="red,green,blue">
    <q:set name="output" operation="append" value="  color = {color}" />
  </q:loop>

  <!-- List loop with custom delimiter -->
  <q:set name="output" operation="append" value="List with delimiter:" />
  <q:loop type="list" var="item" items="one|two|three" delimiter="|">
    <q:set name="output" operation="append" value="  item = {item}" />
  </q:loop>

  <q:return value="{output}" />
</q:component>
