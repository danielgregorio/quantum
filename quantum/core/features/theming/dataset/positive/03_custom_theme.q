<q:application id="CustomThemeApp" type="ui">
  <ui:theme name="ocean" preset="light">
    <ui:color name="primary" value="#0ea5e9" />
    <ui:color name="secondary" value="#06b6d4" />
    <ui:color name="background" value="#f0f9ff" />
    <ui:color name="accent" value="#0284c7" />
  </ui:theme>

  <ui:window title="Ocean Theme">
    <ui:vbox padding="lg" gap="md">
      <ui:text size="2xl" weight="bold" color="primary">Ocean Theme</ui:text>
      <ui:text>Custom color scheme with ocean blue tones.</ui:text>
      <ui:hbox gap="sm">
        <ui:button variant="primary">Primary</ui:button>
        <ui:button variant="secondary">Secondary</ui:button>
      </ui:hbox>
    </ui:vbox>
  </ui:window>
</q:application>
