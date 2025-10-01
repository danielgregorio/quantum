<!-- API Example -->
<q:application id="api" type="microservices" xmlns:q="https://quantum.lang/ns">
  <q:route path="/users" method="GET">
    <q:return value='[{"name": "João", "email": "joao@test.com"}]' />
  </q:route>
</q:application>
