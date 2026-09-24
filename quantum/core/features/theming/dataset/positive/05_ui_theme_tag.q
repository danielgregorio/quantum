<q:application id="ThemeTagApp" type="ui">
  <ui:theme preset="dark" />

  <ui:window title="Theme Tag Example">
    <ui:vbox padding="md">
      <ui:header title="Dashboard" />
      <ui:panel title="Statistics">
        <ui:grid columns="3" gap="md">
          <ui:badge variant="success">Active</ui:badge>
          <ui:badge variant="warning">Pending</ui:badge>
          <ui:badge variant="danger">Errors</ui:badge>
        </ui:grid>
      </ui:panel>
      <ui:footer>Powered by Quantum</ui:footer>
    </ui:vbox>
  </ui:window>
</q:application>
