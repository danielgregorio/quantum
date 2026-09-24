<!-- Negative: Filter missing required 'condition' attribute -->
<!-- Expected error: Filter requires 'condition' attribute -->
<q:component name="DataFilterMissingCondition" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="users" source="data/users.csv" type="csv">
    <q:column name="id" type="integer" />
    <q:transform>
      <q:filter />
    </q:transform>
  </q:data>

  <q:return value="Error" />
</q:component>
