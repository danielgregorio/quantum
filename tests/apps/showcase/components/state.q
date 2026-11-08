<q:component name="State">
  <!-- UI-21: the tags with a state of their own — what is open, which slide, which step, a
       toast that goes — on one page. The parity test's third script (STATE in
       tests/apps/test_ui_parity_script.py) runs on it in every renderer. -->

  <q:action name="pick" method="POST">
    <q:param name="value" required="true" />
    <q:redirect url="/state" flash="Picked: {value}" />
  </q:action>

  <q:set name="welcome" value="{query.welcome}" default="" />

  <ui:window title="State">
    <q:if condition="flash">
      <ui:alert variant="success">{flash}</ui:alert>
    </q:if>

    <ui:modal title="Welcome" open="{welcome == '1'}">
      <ui:text>Read this first</ui:text>
    </ui:modal>

    <ui:toast title="Saved" message="All changes kept" duration="1500" />

    <ui:accordion>
      <ui:section title="First fold"><ui:text>Inside the first</ui:text></ui:section>
      <ui:section title="Second fold"><ui:text>Inside the second</ui:text></ui:section>
    </ui:accordion>

    <ui:tooltip content="A tip for the badge">
      <ui:badge>Hover me</ui:badge>
    </ui:tooltip>

    <ui:dropdown label="Actions">
      <ui:option value="copy" on-click="pick">Copy</ui:option>
      <ui:option value="move" on-click="pick">Move</ui:option>
    </ui:dropdown>

    <ui:carousel>
      <ui:slide><ui:text>Slide one</ui:text></ui:slide>
      <ui:slide><ui:text>Slide two</ui:text></ui:slide>
    </ui:carousel>

    <ui:stepper>
      <ui:step title="Account"><ui:text>Step one body</ui:text></ui:step>
      <ui:step title="Profile"><ui:text>Step two body</ui:text></ui:step>
    </ui:stepper>
  </ui:window>
</q:component>
