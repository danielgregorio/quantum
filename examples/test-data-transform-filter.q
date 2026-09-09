<q:component name="TestDataTransformFilter" type="pure" xmlns:q="https://quantum.lang/ns">
  <!-- Test: Import CSV and filter active users -->
  <q:data name="activeUsers" source="examples/test-data-users.csv" type="csv">
    <q:column name="id" type="integer" />
    <q:column name="name" type="string" />
    <q:column name="age" type="integer" />
    <q:column name="email" type="string" />
    <q:column name="active" type="boolean" />
    <q:transform>
      <q:filter condition="{active} == True" />
    </q:transform>
  </q:data>

  <!-- Loop through active users -->
  <q:loop items="{activeUsers}" var="user">
    Active User: {user.name} (Age: {user.age})
  </q:loop>

  <q:return value="{activeUsers}" />
</q:component>
