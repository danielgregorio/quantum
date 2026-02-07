<?xml version="1.0" encoding="UTF-8"?>
<!--
    Quantum UI - Theme Presets Demo

    Demonstrates all available theme presets:
    - light (default)
    - dark
    - high-contrast (accessibility)
    - sepia (reading/paper)
    - nord (popular dark theme)
    - dracula (popular dark theme)
-->
<q:application id="ThemePresetsDemo" type="ui" theme="dark" auto-switch="true">

    <ui:window title="Theme Presets Gallery">
        <ui:vbox padding="lg" gap="lg">

            <!-- Header -->
            <ui:text size="2xl" weight="bold">Quantum Theme Presets</ui:text>
            <ui:text color="muted">
                Use the buttons below to switch between themes, or enable auto-switch
                to follow your system preference.
            </ui:text>

            <!-- Theme Switcher -->
            <ui:hbox gap="sm">
                <ui:button variant="primary" on-click="setTheme('light')">Light</ui:button>
                <ui:button variant="secondary" on-click="setTheme('dark')">Dark</ui:button>
                <ui:button variant="secondary" on-click="setTheme('high-contrast')">High Contrast</ui:button>
                <ui:button variant="secondary" on-click="setTheme('sepia')">Sepia</ui:button>
                <ui:button variant="secondary" on-click="setTheme('nord')">Nord</ui:button>
                <ui:button variant="secondary" on-click="setTheme('dracula')">Dracula</ui:button>
            </ui:hbox>

            <ui:rule />

            <!-- Color Palette Display -->
            <ui:panel title="Color Palette">
                <ui:grid columns="4" gap="md">
                    <ui:badge variant="primary">Primary</ui:badge>
                    <ui:badge variant="secondary">Secondary</ui:badge>
                    <ui:badge variant="success">Success</ui:badge>
                    <ui:badge variant="danger">Danger</ui:badge>
                    <ui:badge variant="warning">Warning</ui:badge>
                    <ui:badge variant="info">Info</ui:badge>
                    <ui:badge variant="light">Light</ui:badge>
                    <ui:badge variant="dark">Dark</ui:badge>
                </ui:grid>
            </ui:panel>

            <!-- Components Preview -->
            <ui:hbox gap="lg">
                <!-- Buttons -->
                <ui:panel title="Buttons" width="1/2">
                    <ui:vbox gap="sm">
                        <ui:button variant="primary">Primary Button</ui:button>
                        <ui:button variant="secondary">Secondary Button</ui:button>
                        <ui:button variant="danger">Danger Button</ui:button>
                        <ui:button variant="success">Success Button</ui:button>
                        <ui:button disabled="true">Disabled Button</ui:button>
                    </ui:vbox>
                </ui:panel>

                <!-- Form Elements -->
                <ui:panel title="Form Elements" width="1/2">
                    <ui:form>
                        <ui:formitem label="Text Input">
                            <ui:input placeholder="Enter text..." />
                        </ui:formitem>
                        <ui:formitem label="Select">
                            <ui:select>
                                <ui:option value="1">Option 1</ui:option>
                                <ui:option value="2">Option 2</ui:option>
                                <ui:option value="3">Option 3</ui:option>
                            </ui:select>
                        </ui:formitem>
                        <ui:formitem label="Checkbox">
                            <ui:checkbox label="Enable feature" />
                        </ui:formitem>
                        <ui:formitem label="Switch">
                            <ui:switch label="Dark mode" />
                        </ui:formitem>
                    </ui:form>
                </ui:panel>
            </ui:hbox>

            <!-- Cards -->
            <ui:hbox gap="md">
                <ui:card width="1/3">
                    <ui:card-header>
                        <ui:text weight="bold">Info Card</ui:text>
                    </ui:card-header>
                    <ui:card-body>
                        <ui:text>This is a sample card component demonstrating the current theme colors.</ui:text>
                    </ui:card-body>
                    <ui:card-footer>
                        <ui:button variant="primary" size="sm">Learn More</ui:button>
                    </ui:card-footer>
                </ui:card>

                <ui:card width="1/3" variant="elevated">
                    <ui:card-header>
                        <ui:text weight="bold">Elevated Card</ui:text>
                    </ui:card-header>
                    <ui:card-body>
                        <ui:progress value="65" max="100" />
                        <ui:text size="sm" color="muted">65% Complete</ui:text>
                    </ui:card-body>
                </ui:card>

                <ui:card width="1/3" variant="outlined">
                    <ui:card-header>
                        <ui:text weight="bold">Outlined Card</ui:text>
                    </ui:card-header>
                    <ui:card-body>
                        <ui:hbox gap="sm">
                            <ui:avatar initials="JD" />
                            <ui:vbox>
                                <ui:text weight="bold">John Doe</ui:text>
                                <ui:text size="sm" color="muted">Developer</ui:text>
                            </ui:vbox>
                        </ui:hbox>
                    </ui:card-body>
                </ui:card>
            </ui:hbox>

            <!-- Alerts -->
            <ui:vbox gap="sm">
                <ui:alert variant="info" title="Information">
                    This is an informational alert message.
                </ui:alert>
                <ui:alert variant="success" title="Success">
                    Operation completed successfully!
                </ui:alert>
                <ui:alert variant="warning" title="Warning">
                    Please review your settings before proceeding.
                </ui:alert>
                <ui:alert variant="danger" title="Error">
                    An error occurred while processing your request.
                </ui:alert>
            </ui:vbox>

            <!-- Table -->
            <ui:panel title="Data Table">
                <ui:table>
                    <ui:column field="name" header="Name" />
                    <ui:column field="role" header="Role" />
                    <ui:column field="status" header="Status" />
                </ui:table>
            </ui:panel>

        </ui:vbox>
    </ui:window>

    <!-- Theme switching function -->
    <q:function name="setTheme">
        <q:param name="theme" type="string" />
        <q:script>
            window.__quantumSetTheme(theme);
        </q:script>
    </q:function>

</q:application>
