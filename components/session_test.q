<q:component name="SessionTest">
  <!-- Test 1: Set a simple session variable -->
  <q:set name="session.testVar" value="Hello" />

  <!-- Test 2: Set application variable -->
  <q:set name="application.appVar" value="World" />

  <html>
  <head>
    <title>Session Test</title>
  </head>
  <body>
    <h1>Session Test</h1>
    <p>session.testVar = {session.testVar}</p>
    <p>application.appVar = {application.appVar}</p>
    <p>request.method = {request.method}</p>
    <p>request.path = {request.path}</p>
  </body>
  </html>
</q:component>
