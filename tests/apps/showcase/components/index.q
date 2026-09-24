<q:component name="Showcase">
  <!-- The whole Core set of ui:* (UI-7). The same script runs in the browser
       and in the console: tests/apps/test_ui_parity_script.py. -->

  <q:action name="save" method="POST">
    <!-- a pattern without $: a server-only rule (UI-9); the script exercises coming back with an error -->
    <q:param name="name" required="true" minlength="2" pattern="^[A-Z]" />
    <q:param name="active" default="off" />
    <q:param name="notify" default="off" />
    <q:param name="plan" default="none" />
    <q:param name="color" default="none" />
    <q:redirect url="/" flash="Saved: {name}, active={active}, notify={notify}, plan={plan}, color={color}" />
  </q:action>

  <q:action name="remove" method="POST">
    <q:param name="id" type="integer" required="true" />
    <q:redirect url="/" flash="Removed: {id}" />
  </q:action>

  <q:set name="people" type="array" value='[{"id": 1, "name": "Ana", "age": 30}, {"id": 2, "name": "Bia", "age": 25}]' />
  <q:set name="fruits" type="array" value='["açaí", "grape"]' />
  <q:set name="progress" value="40" />

  <ui:window title="Showcase">
    <ui:header title="Showcase header" />
    <q:if condition="flash">
      <ui:alert variant="success" id="notice">{flash}</ui:alert>
    </q:if>

    <ui:hbox gap="md" stack-below="md">
      <ui:vbox gap="sm" grow="true">
        <ui:panel title="Panel">
          <ui:text weight="bold">Bold text</ui:text>
          <ui:badge>Badge</ui:badge>
          <ui:link to="/about">Go to about</ui:link>
          <ui:image src="/logo.png" alt="Logo" />
          <ui:progress value="{progress}" max="100" id="bar" />
        </ui:panel>

        <ui:section title="Section">
          <ui:text>Section text</ui:text>
          <ui:rule />
          <ui:spacer />
        </ui:section>

        <ui:grid columns="1 sm:2">
          <ui:text>Cell A</ui:text>
          <ui:text>Cell B</ui:text>
        </ui:grid>

        <ui:card title="Card">
          <ui:card-header>Card top</ui:card-header>
          <ui:card-body><ui:text>Card body</ui:text></ui:card-body>
          <ui:card-footer><ui:text>Card footer</ui:text></ui:card-footer>
        </ui:card>

        <ui:tabpanel>
          <ui:tab title="First tab"><ui:text>Content of the first</ui:text></ui:tab>
          <ui:tab title="Second tab"><ui:text>Content of the second</ui:text></ui:tab>
        </ui:tabpanel>

        <ui:scrollbox>
          <ui:list source="{fruits}" as="fruit">
            <ui:item><ui:text>Fruit: {fruit}</ui:text></ui:item>
          </ui:list>
        </ui:scrollbox>
      </ui:vbox>

      <ui:vbox gap="sm" grow="true">
        <ui:table source="{people}" as="p">
          <ui:column key="name" label="Name" />
          <ui:column key="age" label="Age" align="right" />
          <ui:column label="Actions">
            <ui:button on-click="remove" with="id={p.id}" variant="danger">Remove {p.name}</ui:button>
          </ui:column>
        </ui:table>

        <ui:form on-submit="save">
          <ui:formitem label="Name">
            <ui:input bind="name" value="Ana" />
          </ui:formitem>
          <ui:checkbox bind="active" label="Active" checked="true" />
          <ui:switch bind="notify" label="Get notifications" />
          <ui:radio bind="plan" options="free,pro" value="free" />
          <ui:select bind="color" options="blue,green" value="green" />
          <ui:button variant="primary">Save</ui:button>
        </ui:form>
      </ui:vbox>
    </ui:hbox>

    <ui:footer>Showcase footer</ui:footer>
  </ui:window>
</q:component>
