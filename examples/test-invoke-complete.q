<!-- Test Invoke Complete -->
<!-- Demonstrates all q:invoke patterns for HTTP requests -->
<q:component name="TestInvokeComplete" xmlns:q="https://quantum.lang/ns">

  <!-- Basic GET request -->
  <q:invoke name="basicGet"
            url="https://jsonplaceholder.typicode.com/users/1"
            method="GET" />

  <!-- GET with query parameters -->
  <q:invoke name="withParams"
            url="https://jsonplaceholder.typicode.com/posts"
            method="GET">
    <q:param name="userId" default="1" />
    <q:param name="_limit" default="2" />
  </q:invoke>

  <!-- GET with custom headers -->
  <q:invoke name="withHeaders"
            url="https://jsonplaceholder.typicode.com/todos/1"
            method="GET">
    <q:header name="Accept" value="application/json" />
    <q:header name="X-Custom-Header" value="QuantumTest" />
  </q:invoke>

  <!-- POST request with body -->
  <q:invoke name="postData"
            url="https://jsonplaceholder.typicode.com/posts"
            method="POST">
    <q:header name="Content-Type" value="application/json" />
    <q:body>{"title": "Test Post", "body": "Content", "userId": 1}</q:body>
  </q:invoke>

  <q:return value="User: {basicGet.name} | Posts: {withParams[0].title} | Todo: {withHeaders.title}" />
</q:component>
