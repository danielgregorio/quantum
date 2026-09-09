<?xml version="1.0" encoding="UTF-8"?>
<!--
    State Persistence Demo

    This example demonstrates the state persistence feature for the Quantum UI Engine.
    State can be automatically saved and restored across sessions using:
    - localStorage (persist="local") for browser-permanent storage
    - sessionStorage (persist="session") for browser-tab storage
    - Synchronized storage (persist="sync") for cross-tab/network sync
-->

<q:component name="SettingsApp">
    <!-- Persisted state variables -->
    <q:set name="theme" value="light" persist="local" persistKey="app_theme" />
    <q:set name="fontSize" type="number" value="16" persist="local" />
    <q:set name="language" value="en" persist="local" persistTtl="86400" />

    <!-- Session-only state (cleared on browser close) -->
    <q:set name="cartItems" type="array" value="[]" persist="session" />

    <!-- Synchronized state (shared across tabs) -->
    <q:set name="notificationCount" type="number" value="0" persist="sync" />

    <!-- Non-persisted state (lost on refresh) -->
    <q:set name="tempSelection" value="" />

    <!-- Explicit persistence configuration for multiple variables -->
    <q:persist scope="local" prefix="prefs_" encrypt="true">
        <q:var name="apiToken" />
        <q:var name="refreshToken" />
    </q:persist>

    <ui:window title="Settings Demo">
        <ui:vbox gap="16" padding="24">
            <ui:header title="State Persistence Demo" />

            <ui:panel title="Theme Settings (persisted to localStorage)">
                <ui:form-item label="Theme">
                    <ui:select bind="theme" options="light,dark,auto" />
                </ui:form-item>

                <ui:form-item label="Font Size">
                    <ui:input type="number" bind="fontSize" placeholder="Font size" />
                </ui:form-item>

                <ui:form-item label="Language">
                    <ui:select bind="language" options="en,es,fr,de,pt" />
                </ui:form-item>
            </ui:panel>

            <ui:panel title="Session State (persisted to sessionStorage)">
                <ui:text>Cart items are stored in session storage and cleared when the browser closes.</ui:text>
                <ui:text>Items in cart: {cartItems.length}</ui:text>
            </ui:panel>

            <ui:panel title="Synchronized State (shared across tabs)">
                <ui:text>Notification count is synchronized across all open tabs.</ui:text>
                <ui:text>Notifications: {notificationCount}</ui:text>
                <ui:button on-click="incrementNotifications">Add Notification</ui:button>
            </ui:panel>

            <ui:panel title="Temporary State (not persisted)">
                <ui:text>This selection will be lost on page refresh.</ui:text>
                <ui:input bind="tempSelection" placeholder="Temporary input..." />
            </ui:panel>

            <ui:footer content="Settings will be saved automatically" />
        </ui:vbox>
    </ui:window>

    <q:function name="incrementNotifications">
        <q:set name="notificationCount" operation="increment" />
    </q:function>
</q:component>
