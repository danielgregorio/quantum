<!-- Test Set All Operations -->
<!-- Demonstrates all q:set operations in one file -->
<q:component name="TestSetAllOperations" xmlns:q="https://quantum.lang/ns">

  <!-- Basic assign (default operation) -->
  <q:set name="message" value="Hello" />

  <!-- Number operations -->
  <q:set name="counter" type="number" value="10" />
  <q:set name="counter" operation="increment" />
  <q:set name="counter" operation="increment" />
  <q:set name="counter" operation="decrement" />
  <q:set name="counter" operation="add" value="100" />
  <q:set name="counter" operation="multiply" value="2" />

  <!-- Array operations -->
  <q:set name="fruits" type="array" value="[]" />
  <q:set name="fruits" operation="append" value="apple" />
  <q:set name="fruits" operation="append" value="banana" />
  <q:set name="fruits" operation="prepend" value="cherry" />
  <q:set name="fruits" operation="sort" />
  <q:set name="fruits" operation="reverse" />
  <q:set name="fruits" operation="unique" />

  <!-- String operations -->
  <q:set name="text" value="  Hello World  " />
  <q:set name="text" operation="trim" />
  <q:set name="textUpper" value="{text}" />
  <q:set name="textUpper" operation="uppercase" />
  <q:set name="textLower" value="{text}" />
  <q:set name="textLower" operation="lowercase" />

  <!-- Object operations -->
  <q:set name="user" type="object" value="{}" />
  <q:set name="user" operation="merge" value='{"name":"Daniel"}' />
  <q:set name="user" operation="merge" value='{"age":30}' />
  <q:set name="user" operation="setProperty" key="email" value="test@example.com" />

  <q:return value="Counter: {counter}, Fruits: {fruits}, Upper: {textUpper}" />
</q:component>
