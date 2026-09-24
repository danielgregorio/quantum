<q:application id="CustomThemeDemo" type="ui">
  <!--
    Custom Theme Demo - demonstrates creating a custom color theme.
    The ui:theme tag allows defining custom colors on top of a preset.
  -->

  <!-- Define custom "ocean" theme extending light preset -->
  <ui:theme name="ocean" preset="light">
    <ui:color name="primary" value="#0ea5e9" />
    <ui:color name="secondary" value="#06b6d4" />
    <ui:color name="success" value="#14b8a6" />
    <ui:color name="background" value="#f0f9ff" />
    <ui:color name="accent" value="#0284c7" />
    <ui:color name="surface" value="#e0f2fe" />
  </ui:theme>

  <ui:window title="Ocean Theme Demo">
    <ui:vbox padding="lg" gap="lg">

      <!-- Header -->
      <ui:header title="Custom Ocean Theme" />

      <!-- Info panel -->
      <ui:panel title="About This Theme">
        <ui:vbox gap="md">
          <ui:text size="lg" weight="bold" color="primary">
            Ocean Blue Color Palette
          </ui:text>
          <ui:text>
            This custom theme uses ocean-inspired colors: cyan, teal, and sky blue.
            Custom themes extend a base preset (light or dark) and override specific colors.
          </ui:text>
        </ui:vbox>
      </ui:panel>

      <!-- Color showcase -->
      <ui:panel title="Color Palette">
        <ui:grid columns="3" gap="md">
          <ui:vbox align="center" padding="md" background="primary">
            <ui:text color="white">Primary</ui:text>
            <ui:text color="white" size="sm">#0ea5e9</ui:text>
          </ui:vbox>
          <ui:vbox align="center" padding="md" background="secondary">
            <ui:text color="white">Secondary</ui:text>
            <ui:text color="white" size="sm">#06b6d4</ui:text>
          </ui:vbox>
          <ui:vbox align="center" padding="md" background="success">
            <ui:text color="white">Success</ui:text>
            <ui:text color="white" size="sm">#14b8a6</ui:text>
          </ui:vbox>
        </ui:grid>
      </ui:panel>

      <!-- Buttons -->
      <ui:panel title="Interactive Elements">
        <ui:hbox gap="md">
          <ui:button variant="primary">Primary Action</ui:button>
          <ui:button variant="secondary">Secondary</ui:button>
          <ui:button variant="success">Confirm</ui:button>
        </ui:hbox>
      </ui:panel>

      <!-- Footer -->
      <ui:footer>
        <ui:text size="sm" color="muted">
          Custom themes let you brand your application with unique colors.
        </ui:text>
      </ui:footer>

    </ui:vbox>
  </ui:window>
</q:application>
