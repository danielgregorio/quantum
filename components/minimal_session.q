<q:component name="MinimalSession">
  <q:set name="testVar" value="Works!" />
  <q:set name="session.sessionVar" value="Session Works!" />

  <html>
  <body>
    <p>Normal var: {testVar}</p>
    <p>Session var: {session.sessionVar}</p>
  </body>
  </html>
</q:component>
