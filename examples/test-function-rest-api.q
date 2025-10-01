<!-- Test Function as REST API Endpoint -->
<q:component name="TestFunctionRestAPI" type="microservice" xmlns:q="https://quantum.lang/ns">
  <!-- Function exposed as GET /api/hello endpoint -->
  <q:function name="sayHello"
              returnType="string"
              endpoint="/api/hello"
              method="GET"
              produces="application/json">
    <q:param name="name" type="string" source="query" default="World" />
    <q:return value="Hello, {name}!" />
  </q:function>

  <!-- Function exposed as POST /api/users endpoint -->
  <q:function name="createUser"
              returnType="string"
              endpoint="/api/users"
              method="POST"
              consumes="application/json"
              produces="application/json"
              status="201">
    <q:param name="username" type="string" source="body" required="true" />
    <q:param name="email" type="string" source="body" required="true" validate="email" />

    <q:return value="User {username} created with email {email}" />
  </q:function>

  <!-- Test function call (not via REST) -->
  <q:set name="result" value="{sayHello('Alice')}" />
  <q:return value="{result}" />
</q:component>
