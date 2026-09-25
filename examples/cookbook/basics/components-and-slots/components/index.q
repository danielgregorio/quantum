<q:component name="Dashboard">
  <!-- from="_shared": a folder whose name starts with _ is never a page. -->
  <q:import component="Card" from="_shared" />
  <q:set name="open" type="number" value="4" />

  <html>
  <body>
    <Card title="Open tickets">
      <p>{open} waiting for an answer.</p>
    </Card>
    <Card title="Warning" tone="alert">
      <p>The mail server is slow today.</p>
    </Card>
  </body>
  </html>
</q:component>
