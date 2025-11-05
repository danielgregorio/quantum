<!-- Test Basic Variable Dump -->
<q:component name="TestDumpBasic" xmlns:q="https://quantum.lang/ns">
  <q:param name="name" type="string" default="John Doe" />
  <q:param name="age" type="integer" default="30" />

  <q:dump var="{name}" label="User Name" />
  <q:dump var="{age}" label="User Age" />

  <q:return value="Name: {name}, Age: {age}" />
</q:component>
