<q:component name="Settings">
  <q:set name="plan" value="Pro" />
  <!-- ?tab=Plan opens the Plan tab; without it, the first one opens -->
  <q:set name="tab" value="{query.tab}" default="Profile" />

  <!-- after the action, the page comes back on the tab it was sent from -->
  <q:action name="renew" method="POST">
    <q:redirect url="/?tab=Plan" flash="Plan renewed." />
  </q:action>

  <ui:window title="Settings">
    <ui:vbox padding="lg">
      <q:if condition="flash">
        <ui:alert variant="success">{flash}</ui:alert>
      </q:if>
      <!-- One ui:tab per section; open names the one that opens. -->
      <ui:tabpanel open="{tab}">
        <ui:tab title="Profile">
          <ui:text>Name: Ana Lima</ui:text>
          <ui:text>E-mail: ana@example.com</ui:text>
        </ui:tab>
        <ui:tab title="Plan">
          <ui:text>Current plan: {plan}</ui:text>
          <ui:badge variant="success">active</ui:badge>
          <ui:button on-click="renew">Renew</ui:button>
        </ui:tab>
        <ui:tab title="Security">
          <ui:text>Two-step sign-in is off.</ui:text>
        </ui:tab>
      </ui:tabpanel>
    </ui:vbox>
  </ui:window>
</q:component>
