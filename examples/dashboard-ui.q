<q:application id="dashboard" type="ui">
    <ui:window title="Server Dashboard">
        <ui:header title="Server Dashboard" />

        <q:set name="cpu" value="45" type="number" />
        <q:set name="memory" value="72" type="number" />

        <ui:hbox gap="16" padding="16">
            <ui:panel title="CPU" width="50%">
                <ui:vbox align="center">
                    <ui:text size="xl" weight="bold">{cpu}%</ui:text>
                    <ui:progress value="{cpu}" max="100" />
                </ui:vbox>
            </ui:panel>

            <ui:panel title="Memory" width="50%">
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

            <ui:tab title="Logs">
                <ui:log auto-scroll="true" max-lines="500" />
            </ui:tab>

            <ui:tab title="Settings">
                <ui:form on-submit="saveSettings">
                    <ui:formitem label="Hostname">
                        <ui:input bind="hostname" placeholder="Enter hostname" />
                    </ui:formitem>
                    <ui:formitem label="Port">
                        <ui:input bind="port" type="number" placeholder="8080" />
                    </ui:formitem>
                    <ui:formitem label="Debug Mode">
                        <ui:switch bind="debug" label="Enable debug logging" />
                    </ui:formitem>
                    <ui:hbox gap="8" justify="end">
                        <ui:button variant="secondary">Cancel</ui:button>
                        <ui:button variant="primary">Save</ui:button>
                    </ui:hbox>
                </ui:form>
            </ui:tab>
        </ui:tabpanel>

        <ui:footer>Quantum Dashboard v1.0</ui:footer>
    </ui:window>
</q:application>
