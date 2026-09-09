<q:component name="TestDataCSV" type="pure" xmlns:q="https://quantum.lang/ns">
  <!-- Test: Import CSV file with type conversion -->
  <q:data name="users" source="examples/test-data-users.csv" type="csv">
    <q:column name="id" type="integer" />
    <q:column name="name" type="string" />
    <q:column name="age" type="integer" />
    <q:column name="email" type="string" />
    <q:column name="active" type="boolean" />
  </q:data>

  <!-- Loop through users and print -->
  <q:loop items="{users}" var="user">
    User {user.id}: {user.name}, Age: {user.age}, Active: {user.active}
  </q:loop>

  <q:return value="{users}" />
</q:component>
