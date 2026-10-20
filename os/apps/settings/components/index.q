<q:component name="Settings">
  <!-- The machine's settings, read: five tabs, each a service of machine.py.
       On the Hive's screen (hive settings) the page is a window of 49 columns;
       every tab fits its rows. A change goes through the Hive, not through
       this page (os/CLAUDE.md, "Apps"). -->
  <!-- a change is asked of the Hive (hive request), never made here -->
  <q:action name="ask-name" method="POST">
    <q:param name="hostname" required="true" />
    <q:invoke name="asked" service="settings.ask">
      <q:param name="action" value="set-hostname" />
      <q:param name="value" value="{hostname}" />
    </q:invoke>
    <q:redirect url="/?tab=Machine" flash="{asked.message}" />
  </q:action>
  <q:action name="ask-keyboard" method="POST">
    <q:param name="layout" required="true" />
    <q:invoke name="asked" service="settings.ask">
      <q:param name="action" value="set-keyboard" />
      <q:param name="value" value="{layout}" />
    </q:invoke>
    <q:redirect url="/?tab=Keyboard" flash="{asked.message}" />
  </q:action>
  <q:action name="ask-network" method="POST">
    <q:param name="interface" required="true" />
    <q:param name="mode" required="true" />
    <q:param name="address" />
    <q:param name="gateway" />
    <q:param name="dns" />
    <q:invoke name="asked" service="settings.ask">
      <q:param name="action" value="set-network" />
      <q:param name="value" value="{interface}" />
      <q:param name="mode" value="{mode}" />
      <q:param name="address" value="{address}" />
      <q:param name="gateway" value="{gateway}" />
      <q:param name="dns" value="{dns}" />
    </q:invoke>
    <q:redirect url="/?tab=Network" flash="{asked.message}" />
  </q:action>
  <q:action name="ask-level" method="POST">
    <q:param name="level" required="true" />
    <q:invoke name="asked" service="settings.ask">
      <q:param name="action" value="set-screen-level" />
      <q:param name="value" value="{level}" />
    </q:invoke>
    <q:redirect url="/?tab=Screen" flash="{asked.message}" />
  </q:action>

  <q:invoke name="machine" service="settings.machine" />
  <q:invoke name="network" service="settings.network" />
  <q:invoke name="keyboard" service="settings.keyboard" />
  <q:invoke name="screen" service="settings.screen" />
  <q:invoke name="hive" service="settings.hive" />
  <!-- after a request the page comes back on the tab it was asked from (UI-17) -->
  <q:set name="tab" value="{query.tab}" default="Machine" />

  <ui:window title="Settings">
    <ui:tabpanel open="{tab}">
      <ui:tab title="Machine">
        <ui:list source="{machine.rows}" as="r">
          <ui:item><ui:text>{r.field}: {r.value}</ui:text></ui:item>
        </ui:list>
        <ui:form on-submit="ask-name">
          <ui:formitem label="New name">
            <ui:input bind="hostname" value="{machine.name}" />
          </ui:formitem>
          <ui:button variant="primary">Ask the Hive</ui:button>
        </ui:form>
      </ui:tab>
      <ui:tab title="Network">
        <ui:table source="{network.interfaces}" as="i">
          <ui:column key="name" label="Interface" />
          <ui:column key="state" label="State" />
          <ui:column key="address" label="Address" />
          <ui:column key="source" label="Source" />
        </ui:table>
        <ui:text>gateway: {network.gateway}</ui:text>
        <ui:text>DNS: {network.dns}</ui:text>
        <!-- the address asked of the Hive: by DHCP (the rest is ignored) or static; dangerous, so the
             screen asks for Enter twice; a wrong address comes back by itself (network-apply) -->
        <ui:form on-submit="ask-network">
          <ui:formitem label="Interface">
            <ui:select bind="interface" options="{network.names}" value="{network.chosen}" />
          </ui:formitem>
          <ui:formitem label="Source">
            <ui:select bind="mode" options="dhcp,static" value="{network.mode}" />
          </ui:formitem>
          <ui:formitem label="Address/prefix (static)">
            <ui:input bind="address" value="{network.address}" placeholder="10.0.2.20/24" />
          </ui:formitem>
          <ui:formitem label="Gateway">
            <ui:input bind="gateway" value="{network.via}" placeholder="10.0.2.2" />
          </ui:formitem>
          <ui:formitem label="DNS (commas)">
            <ui:input bind="dns" value="{network.servers}" placeholder="10.0.2.3" />
          </ui:formitem>
          <ui:button variant="primary">Ask the Hive</ui:button>
        </ui:form>
      </ui:tab>
      <ui:tab title="Keyboard">
        <ui:list source="{keyboard.rows}" as="r">
          <ui:item><ui:text>{r.field}: {r.value}</ui:text></ui:item>
        </ui:list>
        <ui:form on-submit="ask-keyboard">
          <ui:formitem label="Layout">
            <ui:select bind="layout" options="us,br" value="{keyboard.choice}" />
          </ui:formitem>
          <ui:button variant="primary">Ask the Hive</ui:button>
        </ui:form>
      </ui:tab>
      <ui:tab title="Screen">
        <ui:list source="{screen.rows}" as="r">
          <ui:item><ui:text>{r.field}: {r.value}</ui:text></ui:item>
        </ui:list>
        <ui:form on-submit="ask-level">
          <ui:formitem label="Level">
            <ui:select bind="level" options="auto,plain,effects,fine" value="{screen.choice}" />
          </ui:formitem>
          <ui:button variant="primary">Ask the Hive</ui:button>
        </ui:form>
      </ui:tab>
      <ui:tab title="Hive">
        <ui:table source="{hive.daemons}" as="d">
          <ui:column key="name" label="Daemon" />
          <ui:column key="state" label="State" />
        </ui:table>
        <ui:list source="{hive.rows}" as="r">
          <ui:item><ui:text>{r.field}: {r.value}</ui:text></ui:item>
        </ui:list>
      </ui:tab>
    </ui:tabpanel>
    <q:if condition="flash">
      <ui:alert variant="info">{flash}</ui:alert>
    </q:if>
    <ui:footer>Reading is the page's; a change goes through the Hive. Esc closes.</ui:footer>
  </ui:window>
</q:component>
