<?xml version="1.0" encoding="UTF-8"?>
<q:application id="MobileDemo" type="ui">
  <ui:window title="Mobile Demo">
    <ui:vbox padding="md" gap="md">
      <ui:text size="xl" weight="bold">Mobile App</ui:text>

      <ui:card>
        <ui:card-body>
          <ui:text>Card content goes here</ui:text>
        </ui:card-body>
      </ui:card>

      <ui:alert variant="info" title="Information">
        This is a mobile app built with Quantum.
      </ui:alert>

      <ui:button variant="primary" on-click="handleClick()">
        Press Me
      </ui:button>

      <ui:text>{message}</ui:text>
    </ui:vbox>
  </ui:window>

  <q:function name="handleClick">
    <q:set name="message" value="Button pressed!" />
  </q:function>

  <q:set name="message" value="" />
</q:application>
