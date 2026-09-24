<q:component name="TestDataTransformLimit" type="pure" xmlns:q="https://quantum.lang/ns">
  <!-- Test: Import CSV and limit to 3 records -->
  <q:data name="limitedUsers" source="examples/test-data-users.csv" type="csv">
    <q:column name="id" type="integer" />
    <q:column name="name" type="string" />
    <q:column name="age" type="integer" />
    <q:transform>
      <q:limit value="3" />
    </q:transform>
  </q:data>

  <!-- Loop through limited users -->
  <q:loop items="{limitedUsers}" var="user">
    User: {user.name} (ID: {user.id})
  </q:loop>

  <q:return value="{limitedUsers}" />
</q:component>
