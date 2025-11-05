<q:component name="TestActionFlash">
  <!-- Test: Flash messages in actions -->

  <q:action name="saveSettings" method="POST">
    <q:param name="theme" type="string" required="true" />

    <q:set name="session.theme" value="{theme}" />
    <q:flash message="Settings saved successfully!" type="success" />
  </q:action>

  <!-- Expected: Flash message defined -->
  Flash message support enabled
</q:component>
