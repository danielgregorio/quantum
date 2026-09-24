<!-- Test Function with String Operations -->
<q:component name="TestFunctionStringOps" xmlns:q="https://quantum.lang/ns">
  <!-- Concatenate strings -->
  <q:function name="concat" returnType="string">
    <q:param name="first" type="string" required="true" />
    <q:param name="second" type="string" required="true" />
    <q:param name="separator" type="string" default=" " />

    <q:return value="{first}{separator}{second}" />
  </q:function>

  <!-- Format full name -->
  <q:function name="formatName" returnType="string">
    <q:param name="firstName" type="string" required="true" />
    <q:param name="lastName" type="string" required="true" />

    <q:set name="fullName" value="{concat(firstName, lastName)}" />
    <q:return value="{fullName}" />
  </q:function>

  <!-- Test -->
  <q:set name="name" value="{formatName('John', 'Doe')}" />
  <q:return value="Name: {name}" />
</q:component>
