<q:component name="Every">
  <!-- Every ui:* tag of a page once (UI_PARITY.md): each renderer says "not drawn" for exactly the
       tags quantum/runtime/ui_parity.py says it does not draw
       (tests/apps/test_ui_parity_script.py, test_every_tag_*). Left out: ui:pager, ui:history and
       ui:stream, which need a database or a model (the main script has them), and ui:validator,
       ui:theme and ui:color, which are not elements of a page. -->

  <q:action name="noop" method="POST">
    <q:redirect url="/every" />
  </q:action>

  <q:set name="nodes" type="array" value='[{"label": "Root", "children": [{"label": "Leaf"}]}]' />

  <ui:window title="Every">
    <ui:header title="Header" />
    <ui:hbox><ui:text>hbox</ui:text></ui:hbox>
    <ui:vbox><ui:text>vbox</ui:text></ui:vbox>
    <ui:grid columns="2"><ui:text>grid</ui:text></ui:grid>
    <ui:panel title="Panel"><ui:text>panel</ui:text></ui:panel>
    <ui:section title="Section"><ui:text>section</ui:text></ui:section>
    <ui:scrollbox><ui:text>scrollbox</ui:text></ui:scrollbox>
    <ui:spacer />
    <ui:rule />
    <ui:card title="Card">
      <ui:card-header>Card header</ui:card-header>
      <ui:card-body><ui:text>Card body</ui:text></ui:card-body>
      <ui:card-footer>Card footer</ui:card-footer>
    </ui:card>
    <ui:tabpanel>
      <ui:tab title="Tab"><ui:text>tab</ui:text></ui:tab>
    </ui:tabpanel>
    <ui:badge>Badge</ui:badge>
    <ui:alert>Alert</ui:alert>
    <ui:link to="/">Link</ui:link>
    <ui:image src="/logo.png" alt="Image" />
    <ui:progress value="10" max="100" />
    <ui:table>
      <ui:column key="a" label="A" />
    </ui:table>
    <ui:list><ui:item><ui:text>item</ui:text></ui:item></ui:list>
    <ui:form on-submit="noop">
      <ui:formitem label="Field"><ui:input bind="a" /></ui:formitem>
      <ui:checkbox bind="b" label="Box" />
      <ui:switch bind="c" label="Switch" />
      <ui:radio bind="d" options="x,y" />
      <ui:select bind="e"><ui:option value="x" label="X" /></ui:select>
      <ui:date-picker bind="f" />
      <ui:button>Send</ui:button>
    </ui:form>
    <ui:footer>Footer</ui:footer>

    <ui:breadcrumb><ui:breadcrumb-item label="Crumb" /></ui:breadcrumb>
    <ui:menu><ui:option value="m" on-click="noop">Option</ui:option></ui:menu>
    <ui:avatar name="Every Tag" />
    <ui:markdown>**Markdown**</ui:markdown>
    <ui:chart labels="a,b" values="1,2" />
    <ui:tree source="{nodes}" />
    <ui:log>a line</ui:log>
    <ui:dividedbox><ui:text>left</ui:text><ui:text>right</ui:text></ui:dividedbox>
    <ui:pagination total="30" />
    <ui:skeleton />
    <ui:loading text="Loading" />
    <ui:animate type="fade"><ui:text>animate</ui:text></ui:animate>

    <ui:accordion><ui:section title="Fold"><ui:text>fold</ui:text></ui:section></ui:accordion>
    <ui:modal title="Modal" open="true"><ui:text>modal</ui:text></ui:modal>
    <ui:tooltip content="Tip"><ui:text>tooltip</ui:text></ui:tooltip>
    <ui:dropdown label="Dropdown"><ui:option value="o">O</ui:option></ui:dropdown>
    <ui:toast message="Toast" />
    <ui:toast-container />
    <ui:carousel><ui:slide><ui:text>slide</ui:text></ui:slide></ui:carousel>
    <ui:stepper><ui:step title="Step"><ui:text>step</ui:text></ui:step></ui:stepper>
    <ui:calendar />
  </ui:window>
</q:component>
