<q:component name="AdminIndex" require_auth="true" require_role="admin" login_url="/admin/login">
  <!-- /admin: without a session, AUTH-4 sends to /admin/login; with a session, to the applications. -->
  <html lang="en">
  <head>
    <meta http-equiv="refresh" content="0;url=/admin/applications" />
    <title>Quantum Admin</title>
  </head>
  <body>
    <p>Opening <a href="/admin/applications">Applications</a>…</p>
  </body>
  </html>
</q:component>
