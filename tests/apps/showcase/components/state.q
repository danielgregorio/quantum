<q:component name="State">
  <!-- UI-21: the tags with a state of their own — what is open, which slide, which step, a
       toast that goes — on one page. The parity test's third script (STATE in
       tests/apps/test_ui_parity_script.py) runs on it in every renderer. -->

  <q:action name="pick" method="POST">
    <q:param name="value" required="true" />
    <q:redirect url="/state" flash="Picked: {value}" />
  </q:action>

  <q:action name="join" method="POST">
    <q:param name="code" required="true" />
    <q:param name="again" required="true" />
    <q:redirect url="/state" flash="Joined with {code}" />
  </q:action>

  <q:action name="book" method="POST">
    <q:param name="day" type="date" required="true" />
    <q:redirect url="/state" flash="Booked: {day}" />
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

    <!-- the form's own rules, checked by the server when it is sent -->
    <ui:form on-submit="join">
      <ui:validator field="code" pattern="^[A-Z]{3}$" message="Three capital letters" />
      <ui:validator field="again" match="code" message="The codes differ" />
      <ui:input bind="code" />
      <ui:input bind="again" />
      <ui:button>Join</ui:button>
    </ui:form>

    <!-- a calendar is a date field shown as a month: the day picked goes with its form -->
    <ui:form on-submit="book">
      <ui:calendar bind="day" value="2026-11-15" />
      <ui:button>Book</ui:button>
    </ui:form>
  </ui:window>
</q:component>
