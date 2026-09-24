<!-- Negative: Limit missing required 'value' attribute -->
<!-- Expected error: Limit requires 'value' attribute -->
<q:component name="DataLimitMissingValue" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="users" source="data/users.csv" type="csv">
    <q:column name="id" type="integer" />
    <q:transform>
      <q:limit />
    </q:transform>
  </q:data>

  <q:return value="Error" />
</q:component>
