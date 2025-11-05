<!-- Negative: Missing required 'source' attribute -->
<!-- Expected error: Data requires 'source' attribute -->
<q:component name="DataMissingSource" type="pure" xmlns:q="https://quantum.lang/ns">
  <q:data name="users" type="csv">
    <q:column name="id" type="integer" />
  </q:data>

  <q:return value="Error" />
</q:component>
