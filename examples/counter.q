<?xml version="1.0" encoding="UTF-8"?>
<q:component name="Counter">
  <q:set name="count" value="0" type="number" />

  <html>
    <head>
      <title>Counter Example</title>
    </head>
    <body>
      <h1>Counter: {count}</h1>
      <p>This is a simple counter example.</p>

      <q:set name="count" value="{count + 1}" />
      <p>After increment: {count}</p>

      <q:loop var="i" from="1" to="5">
        <p>Loop iteration: {i}</p>
      </q:loop>
    </body>
  </html>
</q:component>
