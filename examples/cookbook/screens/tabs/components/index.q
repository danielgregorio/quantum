<q:component name="Settings">
  <q:set name="plan" value="Pro" />

  <ui:window title="Settings">
    <ui:vbox padding="lg">
      <!-- One ui:tab per section; the first one is open. -->
      <ui:tabpanel>
        <ui:tab title="Profile">
          <ui:text>Name: Ana Lima</ui:text>
          <ui:text>E-mail: ana@example.com</ui:text>
        </ui:tab>
        <ui:tab title="Plan">
          <ui:text>Current plan: {plan}</ui:text>
          <ui:badge variant="success">active</ui:badge>
        </ui:tab>
        <ui:tab title="Security">
          <ui:text>Two-step sign-in is off.</ui:text>
        </ui:tab>
      </ui:tabpanel>
    </ui:vbox>
  </ui:window>
</q:component>
