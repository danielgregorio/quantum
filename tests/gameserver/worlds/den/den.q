<q:application id="den" type="game">

  <!-- The den's game: the client of den.server.q (PLAN_GAME_SERVER.md, Phase 3). The hero's steps are shown at once
       (the world's step has predict="true") and walked back if the world says no; a rat and the hero carry their
       health over them; the HUD's bar is the hero's. -->

  <qg:connect world="den.server.q" />

  <qg:input action="shout" keys="S" />
  <qg:input action="hush" keys="H" />
  <qg:input action="den" keys="D" />

  <qg:tileset name="land" src="den.png" tile="16" />
  <qg:spritesheet name="folk" src="folk.png" tile="16" />
  <qg:spritesheet name="beasts" src="rat.png" tile="16" />

  <qg:prefab name="Hero" sheet="folk" frame="0" hitbox="12x14">
    <qg:label value="{me.name}" dy="-14" size="8" />
    <qg:health-bar value="{me.hp}" max="{me.max_hp}" dy="-9" />
  </qg:prefab>
  <qg:prefab name="Rat" sheet="beasts" frame="0" hitbox="12x10">
    <qg:health-bar value="{me.hp}" max="{me.max_hp}" dy="-8" color="#e04040" />
  </qg:prefab>

  <q:set name="note" value="" />
  <q:set name="refusals" value="0" type="number" />

  <qg:scene name="den" width="320" height="180" world="true">
    <qg:tilemap tileset="land" src="den.tmx" />
    <qg:mirror view="around" />
    <qg:camera follow="me" bounds="tilemap" />

    <qg:on-input action="up"><qg:send command="step" dir="north" /></qg:on-input>
    <qg:on-input action="down"><qg:send command="step" dir="south" /></qg:on-input>
    <qg:on-input action="left"><qg:send command="step" dir="west" /></qg:on-input>
    <qg:on-input action="right"><qg:send command="step" dir="east" /></qg:on-input>
    <qg:on-input action="shout"><qg:send command="shout" /></qg:on-input>
    <qg:on-input action="hush"><qg:send command="hush" /></qg:on-input>
    <qg:on-input action="den"><qg:send command="go" to="square" /></qg:on-input>   <!-- to the rats, around the wall -->

    <qg:on-refused>
      <q:set name="note" value="{reason}" />
      <q:set name="refusals" value="{refusals + 1}" />
    </qg:on-refused>

    <qg:hud position="top-left" size="8">
      <qg:text value="{(me().name + '  ' + str(me().kills) + ' rats') if connected() else 'Coming into the den...'}" />
      <qg:bar value="{me().hp}" max="{me().max_hp}" width="60" height="6" />
      <qg:text value="{note}" color="#ff5555" />
    </qg:hud>
  </qg:scene>
</q:application>
