<q:component name="HelloWorld" xmlns:q="https://quantum.lang/ns">
  <q:set name="greeting" value="Hello" />
  <q:set name="name" value="World" />

  <html>
  <head>
    <title>{greeting} {name}</title>
  </head>
  <body>
    <h1>{greeting}, {name}!</h1>
    <p>This is a simple Quantum component.</p>
    <p><a href="/">Back to Home</a></p>
  </body>
  </html>
</q:component>
