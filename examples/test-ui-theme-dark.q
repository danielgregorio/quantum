<q:application id="DarkThemeDemo" type="ui" theme="dark">
  <!--
    Dark Theme Demo - demonstrates the theming system using the dark preset.
    The theme="dark" attribute on q:application enables the dark color scheme.
  -->

  <ui:window title="Dark Theme Demo">
    <ui:vbox padding="lg" gap="lg">

      <!-- Header section -->
      <ui:header title="Dark Theme Demonstration" />

      <!-- Main content panel -->
      <ui:panel title="Theme Features">
        <ui:vbox gap="md">
          <ui:text size="lg">
            This application uses the dark theme preset.
            All colors are automatically adjusted for dark mode.
          </ui:text>

          <!-- Button variants -->
          <ui:hbox gap="sm">
            <ui:button variant="primary">Primary</ui:button>
            <ui:button variant="secondary">Secondary</ui:button>
            <ui:button variant="success">Success</ui:button>
            <ui:button variant="danger">Danger</ui:button>
            <ui:button variant="warning">Warning</ui:button>
          </ui:hbox>
        </ui:vbox>
      </ui:panel>

      <!-- Status badges -->
      <ui:panel title="Status Indicators">
        <ui:hbox gap="md">
          <ui:badge variant="success">Active</ui:badge>
          <ui:badge variant="warning">Pending</ui:badge>
          <ui:badge variant="danger">Error</ui:badge>
          <ui:badge variant="info">Info</ui:badge>
        </ui:hbox>
      </ui:panel>

      <!-- Form example -->
      <ui:panel title="Form Elements">
        <ui:form>
          <ui:formitem label="Username">
            <ui:input placeholder="Enter username" />
          </ui:formitem>
          <ui:formitem label="Password">
            <ui:input type="password" placeholder="Enter password" />
          </ui:formitem>
          <ui:formitem label="Remember me">
            <ui:checkbox label="Stay logged in" />
          </ui:formitem>
          <ui:button variant="primary">Submit</ui:button>
        </ui:form>
      </ui:panel>

      <!-- Footer -->
      <ui:footer>
        <ui:text size="sm" color="muted">
          Powered by Quantum UI Engine - Dark Theme
        </ui:text>
      </ui:footer>

    </ui:vbox>
  </ui:window>
</q:application>
