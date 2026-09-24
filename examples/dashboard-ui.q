<q:component name="Dashboard">
    <!-- A page in ui:* (UI-1): the page's runtime resolves {cpu}, the table is
         drawn from source= (UI-5) and the form posts to a q:action. Put it in
         an app's components/ and open it with `quantum start`,
         `quantum console` or `quantum desktop` — the same page in each. -->

    <q:action name="saveSettings" method="POST">
        <q:param name="hostname" required="true" />
        <q:param name="port" type="integer" default="8080" />
        <q:param name="debug" default="off" />
        <q:redirect url="/dashboard-ui" flash="Saved: {hostname}:{port}, debug {debug}" />
    </q:action>

    <q:set name="cpu" value="45" type="number" />
    <q:set name="memory" value="72" type="number" />
    <q:set name="processes" type="array" value='[{"pid": 101, "name": "quantum", "cpu": 12.5, "mem": "210 MB"}, {"pid": 202, "name": "sqlite", "cpu": 1.0, "mem": "32 MB"}]' />

    <ui:window title="Server Dashboard">
        <ui:header title="Server Dashboard" />
        <q:if condition="flash">
            <ui:alert variant="success">{flash}</ui:alert>
        </q:if>

        <ui:hbox gap="16" padding="16" stack-below="md">
            <ui:panel title="CPU" grow="true">
                <ui:vbox align="center">
                    <ui:text size="xl" weight="bold">{cpu}%</ui:text>
                    <ui:progress value="{cpu}" max="100" />
                </ui:vbox>
            </ui:panel>

            <ui:panel title="Memory" grow="true">
                <ui:vbox align="center">
                    <ui:text size="xl" weight="bold">{memory}%</ui:text>
                    <ui:progress value="{memory}" max="100" />
                </ui:vbox>
            </ui:panel>
        </ui:hbox>

        <ui:tabpanel>
            <ui:tab title="Processes">
                <ui:table source="{processes}">
                    <ui:column key="pid" label="PID" />
                    <ui:column key="name" label="Name" />
                    <ui:column key="cpu" label="CPU %" align="right" />
                    <ui:column key="mem" label="Memory" align="right" />
                </ui:table>
            </ui:tab>

            <ui:tab title="Settings">
                <ui:form on-submit="saveSettings">
                    <ui:formitem label="Hostname">
                        <ui:input bind="hostname" value="localhost" />
                    </ui:formitem>
                    <ui:formitem label="Port">
                        <ui:input bind="port" type="number" value="8080" />
                    </ui:formitem>
                    <ui:switch bind="debug" label="Enable debug logging" />
                    <ui:button variant="primary">Save</ui:button>
                </ui:form>
            </ui:tab>
        </ui:tabpanel>

        <ui:footer>Quantum Dashboard v1.0</ui:footer>
    </ui:window>
</q:component>
