<q:component name="AdminIndex" require_auth="true" require_role="admin" login_url="/admin/login">
  <!-- /admin: sem sessão, AUTH-4 manda para /admin/login; com sessão, para as aplicações. -->
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
