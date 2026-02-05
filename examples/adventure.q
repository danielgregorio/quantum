<q:application id="dungeon-quest" type="terminal">
  <qt:css>
    #room-desc { height: 1fr; border: solid #666; padding: 1 2; }
    #inventory-panel { width: 30; border: solid yellow; }
  </qt:css>

  <qt:screen name="game" title="Dungeon Quest">
    <qt:header title="Dungeon Quest"/>
    <q:set name="current_room" value="entrance"/>
    <q:set name="inventory" type="array" value="[]"/>
    <q:set name="hp" type="number" value="100"/>

    <qt:layout direction="horizontal">
      <qt:panel id="room-desc" title="Room">
        <qt:text id="room-text">You stand at the entrance of a dark dungeon...</qt:text>
      </qt:panel>
      <qt:panel id="inventory-panel" title="Inventory">
        <qt:text id="hp-display">[bold red]HP: {hp}/100[/]</qt:text>
        <qt:tree id="inv-tree" label="Backpack"/>
      </qt:panel>
    </qt:layout>

    <qt:log id="action-log" max-lines="50"/>
    <qt:input id="cmd" placeholder="go north, take key, look..." on-submit="process_command"/>
    <qt:footer/>
    <qt:keybinding key="q" action="quit" description="Quit"/>

    <q:function name="process_command">
      <q:set name="placeholder" value="process_command action"/>
    </q:function>
  </qt:screen>
</q:application>
