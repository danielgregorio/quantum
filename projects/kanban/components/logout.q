<q:component name="Logout">
  <q:action name="signOut" method="POST">
    <q:set name="session.authenticated" value="false" type="boolean" />
    <q:set name="session.userId" value="" />
    <q:set name="session.userRole" value="" />
    <q:redirect url="/login" flash="Signed out." />
  </q:action>

  <ui:window title="Sign out">
    <ui:vbox gap="md" padding="lg">
      <ui:text>Sign out of the Kanban?</ui:text>
      <ui:button on-click="signOut" variant="primary">Sign out</ui:button>
      <ui:link to="/">Back to the boards</ui:link>
    </ui:vbox>
  </ui:window>
</q:component>
