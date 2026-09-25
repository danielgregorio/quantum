<q:component name="GuestList">
  <q:action name="sign" method="POST">
    <q:param name="name" required="true" minlength="2" maxlength="40" />
    <!-- append to a list that does not exist yet starts one -->
    <q:set name="session.guests" operation="append" value="{name}" />
    <q:redirect url="/" flash="Welcome, {name}!" />
  </q:action>

  <q:set name="guests" type="array" value="{session.guests}" default="[]" />

  <ui:window title="Guest list">
    <ui:vbox gap="md" padding="lg">
      <q:if condition="flash">
        <ui:alert variant="{flashType == 'error' and 'danger' or 'success'}">{flash}</ui:alert>
      </q:if>
      <ui:text>{len(guests)} signed so far.</ui:text>
      <ui:form on-submit="sign">
        <ui:hbox gap="sm">
          <ui:input bind="name" placeholder="Your name" grow="true" />
          <ui:button variant="primary">Sign</ui:button>
        </ui:hbox>
      </ui:form>
      <ui:list>
        <q:loop type="array" var="guest" items="{guests}">
          <ui:item>{guest}</ui:item>
        </q:loop>
      </ui:list>
    </ui:vbox>
  </ui:window>
</q:component>
