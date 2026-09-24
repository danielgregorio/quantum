<!-- Test Databinding Complete -->
<!-- Demonstrates all databinding patterns -->
<q:component name="TestDatabindingComplete" xmlns:q="https://quantum.lang/ns">

  <!-- Simple variable binding -->
  <q:set name="name" value="John" />
  <q:set name="greeting" value="Hello, {name}!" />

  <!-- Arithmetic expressions -->
  <q:set name="a" type="number" value="10" />
  <q:set name="b" type="number" value="5" />
  <q:set name="sum" value="{a + b}" />
  <q:set name="diff" value="{a - b}" />
  <q:set name="product" value="{a * b}" />
  <q:set name="quotient" value="{a / b}" />

  <!-- String concatenation in expressions -->
  <q:set name="firstName" value="John" />
  <q:set name="lastName" value="Doe" />
  <q:set name="fullName" value="{firstName} {lastName}" />

  <!-- Nested property access -->
  <q:set name="user" type="object" value='{"name": "Alice", "address": {"city": "NYC"}}' />
  <q:set name="userCity" value="{user.address.city}" />

  <!-- Array access -->
  <q:set name="colors" type="array" value='["red", "green", "blue"]' />
  <q:set name="firstColor" value="{colors[0]}" />
  <q:set name="lastColor" value="{colors[2]}" />

  <!-- Multiple bindings in one string -->
  <q:set name="summary" value="User: {firstName} {lastName}, City: {userCity}, Color: {firstColor}" />

  <q:return value="{greeting} | Math: {sum}, {diff}, {product}, {quotient} | {summary}" />
</q:component>
