<!-- INVALID: Color without value -->
<q:application id="BadThemeApp" type="ui">
  <ui:theme preset="light">
    <ui:color name="primary" />
  </ui:theme>
  <ui:window>
    <ui:text>Color must have a value</ui:text>
  </ui:window>
</q:application>
