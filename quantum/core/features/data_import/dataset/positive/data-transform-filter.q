<!-- Positive: Data import with filter transformation -->
<q:component name="DataFilterTransform" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="activeUsers" source="data/users.csv" type="csv">
    <q:column name="id" type="integer" />
    <q:column name="name" type="string" />
    <q:column name="active" type="boolean" />
    <q:transform>
      <q:filter condition="{active} == True" />
    </q:transform>
  </q:data>

  <q:return value="{activeUsers}" />
</q:component>
