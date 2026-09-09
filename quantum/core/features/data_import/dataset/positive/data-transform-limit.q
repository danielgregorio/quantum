<!-- Positive: Data import with limit transformation -->
<q:component name="DataLimitTransform" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="topUsers" source="data/users.csv" type="csv">
    <q:column name="id" type="integer" />
    <q:column name="name" type="string" />
    <q:transform>
      <q:limit value="5" />
    </q:transform>
  </q:data>

  <q:return value="{topUsers}" />
</q:component>
