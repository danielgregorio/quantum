<q:component name="AdminLogout">
  <!-- Sair: só por POST (o botão da barra lateral), para um link não derrubar a sessão. -->
  <q:action name="signOut" method="POST">
    <q:set name="session.authenticated" value="false" type="boolean" />
    <q:set name="session.userName" value="" />
    <q:set name="session.userRole" value="" />
    <q:redirect url="/admin/login" flash="Signed out" />
  </q:action>

  <html lang="en"><body><p>Use the Sign out button.</p></body></html>
</q:component>
