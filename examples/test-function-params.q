<!-- Test Function Parameters (required, default, types) -->
<q:component name="TestFunctionParams" xmlns:q="https://quantum.lang/ns">
  <!-- Function with required and optional parameters -->
  <q:function name="greet" returnType="string">
    <q:param name="name" type="string" required="true" />
    <q:param name="greeting" type="string" default="Hello" />

    <q:return value="{greeting}, {name}!" />
  </q:function>

  <!-- Test with both parameters -->
  <q:set name="message1" value="{greet('Alice', 'Hi')}" />

  <!-- Test with default parameter -->
  <q:set name="message2" value="{greet('Bob')}" />

  <q:return value="{message1} | {message2}" />
</q:component>
