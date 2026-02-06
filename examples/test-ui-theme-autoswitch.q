<q:application id="AutoSwitchDemo" type="ui">
  <!--
    Auto-Switch Theme Demo - demonstrates automatic light/dark mode switching.
    The auto-switch="true" attribute makes the theme follow system preferences.
  -->

  <!-- Enable auto-switching between light and dark themes -->
  <ui:theme preset="light" auto-switch="true" />

  <ui:window title="Auto Theme Switching">
    <ui:vbox padding="lg" gap="lg">

      <!-- Header -->
      <ui:header title="System Theme Preference" />

      <!-- Info panel -->
      <ui:panel title="How It Works">
        <ui:vbox gap="md">
          <ui:text size="lg">
            This application automatically switches between light and dark themes
            based on your operating system's color scheme preference.
          </ui:text>

          <ui:text>
            Try changing your system's appearance settings to see the theme change!
          </ui:text>
        </ui:vbox>
      </ui:panel>

      <!-- Manual toggle -->
      <ui:panel title="Manual Control">
        <ui:vbox gap="md">
          <ui:text>
            You can also manually toggle the theme using the button below.
            Your preference will be saved in local storage.
          </ui:text>

          <ui:hbox gap="md">
            <ui:button variant="primary" on-click="__quantumToggleTheme()">
              Toggle Theme
            </ui:button>
            <ui:button variant="secondary" on-click="__quantumSetTheme('light')">
              Light Mode
            </ui:button>
            <ui:button variant="secondary" on-click="__quantumSetTheme('dark')">
              Dark Mode
            </ui:button>
          </ui:hbox>
        </ui:vbox>
      </ui:panel>

      <!-- Current theme display -->
      <ui:panel title="Theme API">
        <ui:vbox gap="sm">
          <ui:text weight="bold">Available JavaScript functions:</ui:text>
          <ui:text size="sm" color="muted">__quantumGetTheme() - Get current theme</ui:text>
          <ui:text size="sm" color="muted">__quantumSetTheme(name) - Set theme by name</ui:text>
          <ui:text size="sm" color="muted">__quantumToggleTheme() - Toggle light/dark</ui:text>
        </ui:vbox>
      </ui:panel>

      <!-- Sample content -->
      <ui:panel title="Sample Elements">
        <ui:vbox gap="md">
          <ui:hbox gap="sm">
            <ui:badge variant="success">Active</ui:badge>
            <ui:badge variant="warning">Pending</ui:badge>
            <ui:badge variant="danger">Error</ui:badge>
          </ui:hbox>

          <ui:progress value="75" max="100" />

          <ui:form>
            <ui:formitem label="Email">
              <ui:input type="email" placeholder="user@example.com" />
            </ui:formitem>
          </ui:form>
        </ui:vbox>
      </ui:panel>

      <!-- Footer -->
      <ui:footer>
        <ui:text size="sm" color="muted">
          Quantum UI Engine - Automatic Theme Switching
        </ui:text>
      </ui:footer>

    </ui:vbox>
  </ui:window>
</q:application>
