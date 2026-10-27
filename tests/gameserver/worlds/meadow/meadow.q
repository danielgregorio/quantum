<q:application id="meadow" type="game">

  <!-- The meadow's game: the client of meadow.server.q (PLAN_GAME_SERVER.md, Phase 2). It holds no rule of the
       world: it draws what the world says the player sees (qg:mirror), asks what the player does (qg:send), and
       shows what happens (qg:on-event) and what the world refused (qg:on-refused). The map is the file the server
       reads, so only what moves goes over the network. -->

  <qg:connect world="meadow.server.q" />

  <qg:input action="shout" keys="S" />
  <qg:input action="earn" keys="E" />
  <qg:input action="bag" keys="B" />

  <qg:tileset name="land" src="meadow.png" tile="16" />
  <qg:spritesheet name="folk" src="folk.png" tile="16" />

  <!-- a hero of the world, as the server sends it: its name over it -->
  <qg:prefab name="Hero" sheet="folk" frame="0" hitbox="12x14">
    <qg:label value="{me.name}" dy="-12" size="8" />
  </qg:prefab>

  <q:set name="note" value="" />
  <q:set name="heard" value="" />
  <q:set name="refusals" value="0" type="number" />

  <qg:scene name="meadow" width="320" height="180" world="true">
    <qg:tilemap tileset="land" src="meadow.tmx" />
    <qg:mirror view="around" />
    <qg:camera follow="me" bounds="tilemap" />

    <qg:on-input action="up"><qg:send command="step" dir="north" /></qg:on-input>
    <qg:on-input action="down"><qg:send command="step" dir="south" /></qg:on-input>
    <qg:on-input action="left"><qg:send command="step" dir="west" /></qg:on-input>
    <qg:on-input action="right"><qg:send command="step" dir="east" /></qg:on-input>
    <qg:on-input action="shout"><qg:send command="shout" text="hello" /></qg:on-input>
    <qg:on-input action="earn"><qg:send command="earn" /></qg:on-input>
    <qg:on-input action="bag"><qg:open-overlay name="bag" /></qg:on-input>

    <qg:on-event name="shout">
      <q:set name="heard" value="{value}" />
      <q:if condition="{other != null}"><qg:emit text="{'!'}" at="other" color="#ffff55" /></q:if>
    </qg:on-event>
    <qg:on-refused command="step">
      <q:set name="note" value="{reason}" />
      <q:set name="refusals" value="{refusals + 1}" />
    </qg:on-refused>

    <qg:hud position="top-left" size="8">
      <qg:text value="{(me().name + '  ' + str(me().purse) + ' coins') if connected() else 'Coming into the world...'}" />
      <qg:text value="{note}" color="#ff5555" />
      <qg:text value="{heard}" color="#ffff55" />
    </qg:hud>
  </qg:scene>

  <!-- the world goes on under the bag: it never stands still -->
  <qg:overlay name="bag" freeze="false" shade="0.3">
    <qg:hud position="center" size="10"><qg:text value="{'Purse: ' + str(me().purse)}" /></qg:hud>
    <qg:on-input action="bag"><qg:close-overlay /></qg:on-input>
  </qg:overlay>
</q:application>
