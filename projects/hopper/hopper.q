<q:application id="hopper" type="game">

  <!-- Hopper: the platformer that drives the game language (PLAN_GAMES_2.md).
       A world map and three levels. A character that walks and jumps on a
       tilemap, blocks with power-ups in them, coins, walkers to stomp or be
       hurt by, pits, checkpoints, spikes, a flag at the end of each level, a
       game over. Art and sounds: Kenney's Pixel Platformer (CC0), in
       assets/kenney/. -->

  <!-- The game's state: kept across scenes. -->
  <q:set name="lives" value="3" type="number" />
  <q:set name="score" value="0" type="number" />
  <q:set name="cleared" value="[]" type="array" />
  <q:set name="map_at" value="level-1" />
  <!-- the checkpoint reached: its level and where the character starts again there -->
  <q:set name="check_at" value="" />
  <q:set name="check_x" value="0" type="number" />
  <q:set name="check_y" value="0" type="number" />

  <!-- Jump on space, Z, X, up or W; the other actions keep their default keys. -->
  <qg:input action="jump" keys="Space, Z, X, Up, W" />

  <qg:tileset name="kenney" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="chars" src="assets/kenney/tilemap-characters_packed.png" tile="24" />

  <qg:sound name="jump" src="assets/kenney/audio/jump.ogg" />
  <qg:sound name="coin" src="assets/kenney/audio/coin.ogg" />
  <qg:sound name="stomp" src="assets/kenney/audio/stomp.ogg" />
  <qg:sound name="hurt" src="assets/kenney/audio/hurt.ogg" />
  <qg:sound name="block" src="assets/kenney/audio/block.ogg" />
  <qg:sound name="powerup" src="assets/kenney/audio/powerup.ogg" />
  <qg:sound name="win" src="assets/kenney/audio/win.ogg" />

  <qg:prefab name="Coin" tag="coin" sheet="kenney" frame="151" hitbox="12x12" />
  <qg:prefab name="QBlock" tag="qblock" sheet="kenney" frame="10" hitbox="18x18" solid="true" />
  <qg:prefab name="UsedBlock" tag="usedblock" sheet="kenney" frame="11" hitbox="18x18" solid="true" />
  <qg:prefab name="Shroom" tag="shroom" sheet="kenney" frame="128" hitbox="12x12"
             ai="patrol" speed="40" direction="right" turns-at="wall" />
  <qg:prefab name="Spikes" tag="spikes" sheet="kenney" frame="68" hitbox="18x8" />
  <qg:prefab name="Checkpoint" tag="checkpoint" sheet="kenney" frame="111" hitbox="18x18" />
  <qg:prefab name="CheckpointOn" tag="checkpoint-on" sheet="kenney" frame="112" hitbox="18x18" />
  <qg:prefab name="Flag" tag="flag" sheet="kenney" frame="153" hitbox="18x18" />
  <!-- A ledge to jump through from below and stand on; a lift that rises and comes back. -->
  <qg:prefab name="Ledge" tag="ledge" sheet="kenney" frame="23" hitbox="18x6" solid="true" one-way="true" />
  <qg:prefab name="Lift" tag="lift" sheet="kenney" frame="43" hitbox="18x8" solid="true"
             ai="shuttle" dy="-80" period="240" />

  <qg:prefab name="Walker" tag="enemy" sheet="chars" frame="18" hitbox="18x18"
             ai="patrol" speed="30" direction="left" turns-at="edge">
    <qg:animation name="walk" frames="18,19,20" fps="6" />
  </qg:prefab>

  <!-- ===== The world map: the game starts here ===== -->

  <qg:scene name="map" width="256" height="224" background="#3b7d4f">
    <qg:map-node name="level-1" x="48" y="112" sheet="kenney" frame="153" scene="level-1" />
    <qg:map-node name="level-2" x="128" y="80" sheet="kenney" frame="153" scene="level-2" />
    <qg:map-node name="level-3" x="208" y="112" sheet="kenney" frame="153" scene="level-3" />
    <qg:map-path from="level-1" to="level-2" requires="level-1" />
    <qg:map-path from="level-2" to="level-3" requires="level-2" />

    <qg:character id="player" controller="map" sheet="chars" frame="0" at="{map_at}" speed="60"
                  x="0" y="0" hitbox="18x22">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1,2" fps="8" />
    </qg:character>

    <qg:hud position="top-left">
      <qg:counter bind="score" label="SCORE" />
      <qg:counter bind="lives" label="LIVES" />
    </qg:hud>
  </qg:scene>

  <!-- ===== Level 1 ===== -->

  <qg:scene name="level-1" width="256" height="224" background="#5c94fc" seed="7">
    <q:if condition="{check_at == 'level-1'}">
      <qg:put target="player" x="{check_x}" y="{check_y}" />
    </q:if>
    <q:set name="coins" value="0" type="number" />
    <q:set name="message" value="" />
    <q:set name="time" value="99" type="number" />

    <!-- The clock: a second off every 60 ticks; at zero the level is lost. -->
    <qg:timer every="60">
      <q:set name="time" value="{time - 1}" />
      <q:if condition="{time <= 0}">
        <q:set name="lives" value="{lives - 1}" />
        <q:set name="check_at" value="" />
        <qg:goto-scene name="map" />
      </q:if>
    </qg:timer>

    <q:function name="die" params="me">
      <qg:play sound="hurt" />
      <q:set name="lives" value="{lives - 1}" />
      <q:if condition="{lives <= 0}">
        <qg:goto-scene name="game-over" />
      <q:else>
        <qg:goto-scene name="level-1" />   <!-- the level again, enemies and all: from the start or its checkpoint -->
      </q:else>
      </q:if>
    </q:function>

    <!-- 24 columns x 13 rows of 18 px = 432 x 234. 0 is empty; 23 is the grass
         top, 25 the dirt below it. A platform at row 6, a pit at columns 13-14. -->
    <qg:tilemap tileset="kenney" collision="true">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,23,23,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
23,23,23,23,23,23,23,23,23,23,23,23,23,0,0,23,23,23,23,23,23,23,23,23
25,25,25,25,25,25,25,25,25,25,25,25,25,0,0,25,25,25,25,25,25,25,25,25
25,25,25,25,25,25,25,25,25,25,25,25,25,0,0,25,25,25,25,25,25,25,25,25
    </qg:tilemap>

    <qg:character id="player" controller="platformer" sheet="chars" frame="0"
                  x="40" y="160" hitbox="18x22"
                  run-speed="90" jump-height="64" variable-jump="true" coyote-frames="6"
                  jump-sound="jump">
      <qg:state name="small" hitbox="18x22" frame="0" initial="true">
        <qg:animation name="idle" frames="0" />
        <qg:animation name="walk" frames="1,2" fps="8" />
        <qg:animation name="jump" frames="1" />
      </qg:state>
      <qg:state name="big" hitbox="18x22" frame="3">
        <qg:animation name="idle" frames="3" />
        <qg:animation name="walk" frames="4,5" fps="8" />
        <qg:animation name="jump" frames="4" />
      </qg:state>

      <qg:on-collision with="coin">
        <qg:destroy target="other" />
        <qg:play sound="coin" />
        <q:set name="coins" value="{coins + 1}" />
        <q:set name="score" value="{score + 10}" />
      </qg:on-collision>

      <qg:on-collision with="qblock" side="bottom">
        <qg:swap target="other" prefab="UsedBlock" />
        <qg:spawn prefab="Shroom" at="other" dy="-18" />
        <qg:play sound="block" />
      </qg:on-collision>

      <qg:on-collision with="shroom">
        <qg:destroy target="other" />
        <qg:play sound="powerup" />
        <qg:become target="me" state="big" />
        <q:set name="score" value="{score + 50}" />
      </qg:on-collision>

      <qg:on-collision with="enemy" side="top">
        <qg:destroy target="other" />
        <qg:bounce target="me" height="32" />
        <qg:play sound="stomp" />
        <q:set name="score" value="{score + 100}" />
      </qg:on-collision>

      <qg:on-collision with="enemy" side="any" cooldown="60">
        <q:if condition="{me.state == 'big'}">
          <qg:play sound="hurt" />
          <qg:become target="me" state="small" />
        <q:else>
          <q:call function="die" args="me" />
        </q:else>
        </q:if>
      </qg:on-collision>

      <qg:on-collision with="spikes" cooldown="60">
        <q:call function="die" args="me" />
      </qg:on-collision>

      <qg:on-collision with="checkpoint">
        <qg:checkpoint target="me" at="other" />
        <qg:swap target="other" prefab="CheckpointOn" />
        <q:set name="check_at" value="level-1" />
        <q:set name="check_x" value="297" />
        <q:set name="check_y" value="169" />
      </qg:on-collision>

      <qg:on-collision with="flag" cooldown="100000">
        <qg:play sound="win" />
        <q:set name="score" value="{score + 500}" />
        <q:set name="message" value="YOU WIN" />
        <q:set name="cleared" value="{cleared + ['level-1']}" />
        <q:set name="check_at" value="" />
        <qg:goto-scene name="map" />
      </qg:on-collision>

      <qg:on-fall>
        <q:call function="die" args="me" />
      </qg:on-fall>
    </qg:character>

    <qg:instance prefab="QBlock" x="45" y="135" />
    <qg:instance prefab="Coin" x="120" y="160" />
    <qg:instance prefab="Coin" x="171" y="96" />
    <qg:instance prefab="Walker" x="200" y="160" />
    <qg:instance prefab="Checkpoint" x="297" y="171" if="{check_at != 'level-1'}" />
    <qg:instance prefab="CheckpointOn" x="297" y="171" if="{check_at == 'level-1'}" />
    <qg:instance prefab="Spikes" x="351" y="176" />
    <qg:instance prefab="Flag" x="405" y="171" />

    <qg:camera follow="player" bounds="tilemap" gd:position_smoothing_enabled="true" gd:position_smoothing_speed="8" />

    <qg:hud position="top-left">
      <qg:counter bind="score" label="SCORE" />
      <qg:counter bind="coins" label="COINS" />
      <qg:counter bind="lives" label="LIVES" />
      <qg:counter bind="time" label="TIME" />
      <qg:text bind="message" />
    </qg:hud>
  </qg:scene>

  <!-- ===== Level 2: platforms and two walkers ===== -->

  <qg:scene name="level-2" width="256" height="224" background="#4a7cc9" seed="11">
    <q:if condition="{check_at == 'level-2'}">
      <qg:put target="player" x="{check_x}" y="{check_y}" />
    </q:if>
    <q:set name="coins" value="0" type="number" />

    <q:function name="die" params="me">
      <qg:play sound="hurt" />
      <q:set name="lives" value="{lives - 1}" />
      <q:if condition="{lives <= 0}">
        <qg:goto-scene name="game-over" />
      <q:else>
        <qg:goto-scene name="level-2" />   <!-- the level again, enemies and all: from the start or its checkpoint -->
      </q:else>
      </q:if>
    </q:function>

    <!-- The level is drawn in Tiled (levels/level-2.tmx): a decor layer, a ground
         layer with a collision property, and an object layer whose points place
         the coins, the walkers and the flag by their class. -->
    <qg:tilemap tileset="kenney" src="levels/level-2.tmx" />

    <qg:character id="player" controller="platformer" sheet="chars" frame="0"
                  x="40" y="160" hitbox="18x22"
                  run-speed="90" jump-height="64" variable-jump="true" coyote-frames="6"
                  jump-sound="jump">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1,2" fps="8" />
      <qg:animation name="jump" frames="1" />

      <qg:on-collision with="coin">
        <qg:destroy target="other" />
        <qg:play sound="coin" />
        <q:set name="coins" value="{coins + 1}" />
        <q:set name="score" value="{score + 10}" />
      </qg:on-collision>
      <qg:on-collision with="enemy" side="top">
        <qg:destroy target="other" />
        <qg:bounce target="me" height="32" />
        <qg:play sound="stomp" />
        <q:set name="score" value="{score + 100}" />
      </qg:on-collision>
      <qg:on-collision with="enemy" side="any" cooldown="60">
        <q:call function="die" args="me" />
      </qg:on-collision>
      <qg:on-collision with="flag" cooldown="100000">
        <qg:play sound="win" />
        <q:set name="score" value="{score + 500}" />
        <q:set name="cleared" value="{cleared + ['level-2']}" />
        <q:set name="check_at" value="" />
        <qg:goto-scene name="map" />
      </qg:on-collision>
      <qg:on-fall>
        <q:call function="die" args="me" />
      </qg:on-fall>
    </qg:character>


    <qg:camera follow="player" bounds="tilemap" gd:position_smoothing_enabled="true" gd:position_smoothing_speed="8" />
    <qg:hud position="top-left">
      <qg:counter bind="score" label="SCORE" />
      <qg:counter bind="coins" label="COINS" />
      <qg:counter bind="lives" label="LIVES" />
    </qg:hud>
  </qg:scene>

  <!-- ===== Level 3: the spikes gauntlet ===== -->

  <qg:scene name="level-3" width="256" height="224" background="#7a4fa8" seed="13">
    <q:if condition="{check_at == 'level-3'}">
      <qg:put target="player" x="{check_x}" y="{check_y}" />
    </q:if>
    <q:set name="coins" value="0" type="number" />

    <q:function name="die" params="me">
      <qg:play sound="hurt" />
      <q:set name="lives" value="{lives - 1}" />
      <q:if condition="{lives <= 0}">
        <qg:goto-scene name="game-over" />
      <q:else>
        <qg:goto-scene name="level-3" />   <!-- the level again, enemies and all: from the start or its checkpoint -->
      </q:else>
      </q:if>
    </q:function>

    <qg:tilemap tileset="kenney" collision="true">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,23,23,0,0,0,0,23,23,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
23,23,23,23,23,23,23,23,23,23,23,23,23,23,23,23,23,23,23,23,23,23,23,23
25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25
25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25
    </qg:tilemap>

    <qg:character id="player" controller="platformer" sheet="chars" frame="0"
                  x="40" y="160" hitbox="18x22"
                  run-speed="90" jump-height="64" variable-jump="true" coyote-frames="6"
                  jump-sound="jump">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1,2" fps="8" />
      <qg:animation name="jump" frames="1" />

      <qg:on-collision with="coin">
        <qg:destroy target="other" />
        <qg:play sound="coin" />
        <q:set name="coins" value="{coins + 1}" />
        <q:set name="score" value="{score + 10}" />
      </qg:on-collision>
      <qg:on-collision with="spikes" cooldown="60">
        <q:call function="die" args="me" />
      </qg:on-collision>
      <qg:on-collision with="checkpoint">
        <qg:checkpoint target="me" at="other" />
        <qg:swap target="other" prefab="CheckpointOn" />
        <q:set name="check_at" value="level-3" />
        <q:set name="check_x" value="207" />
        <q:set name="check_y" value="169" />
      </qg:on-collision>
      <qg:on-collision with="flag" cooldown="100000">
        <qg:play sound="win" />
        <q:set name="score" value="{score + 1000}" />
        <q:set name="cleared" value="{cleared + ['level-3']}" />
        <q:set name="check_at" value="" />
        <qg:goto-scene name="map" />
      </qg:on-collision>
      <qg:on-fall>
        <q:call function="die" args="me" />
      </qg:on-fall>
    </qg:character>

    <qg:instance prefab="Spikes" x="135" y="176" />
    <qg:instance prefab="Spikes" x="153" y="176" />
    <qg:instance prefab="Coin" x="144" y="96" />
    <qg:instance prefab="Checkpoint" x="207" y="171" if="{check_at != 'level-3'}" />
    <qg:instance prefab="CheckpointOn" x="207" y="171" if="{check_at == 'level-3'}" />
    <qg:instance prefab="Spikes" x="243" y="176" />
    <qg:instance prefab="Spikes" x="261" y="176" />
    <qg:instance prefab="Spikes" x="279" y="176" />
    <qg:instance prefab="Coin" x="252" y="96" />
    <qg:instance prefab="Flag" x="405" y="171" />

    <qg:camera follow="player" bounds="tilemap" gd:position_smoothing_enabled="true" gd:position_smoothing_speed="8" />
    <qg:hud position="top-left">
      <qg:counter bind="score" label="SCORE" />
      <qg:counter bind="coins" label="COINS" />
      <qg:counter bind="lives" label="LIVES" />
    </qg:hud>
  </qg:scene>

  <!-- ===== Game over: jump to start again ===== -->

  <qg:scene name="game-over" width="256" height="224" background="#000000">
    <q:set name="message" value="GAME OVER - PRESS JUMP" />

    <qg:on-input action="jump">
      <q:set name="lives" value="3" />
      <q:set name="score" value="0" />
      <q:set name="cleared" value="[]" />
      <q:set name="map_at" value="level-1" />
      <q:set name="check_at" value="" />
      <qg:goto-scene name="map" />
    </qg:on-input>

    <qg:hud position="top-center">
      <qg:text bind="message" />
    </qg:hud>
  </qg:scene>

</q:application>
