<q:application id="AutoSwitchApp" type="ui">
  <ui:theme preset="light" auto-switch="true" />

  <ui:window title="Auto Theme Switch">
    <ui:vbox padding="md" gap="lg">
      <ui:text size="xl">Automatic Theme Switching</ui:text>
      <ui:text>
        This app automatically switches between light and dark mode
        based on your system preference.
      </ui:text>
      <ui:button on-click="__quantumToggleTheme()">Toggle Theme</ui:button>
    </ui:vbox>
  </ui:window>
</q:application>
