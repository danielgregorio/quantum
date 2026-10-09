<q:application id="keep" type="game">

  <!-- Keep: the top-down adventure that drives the game language (PLAN_GAMES_2.md).
       Six rooms of a keep, seen from above. A character that walks in eight
       directions and swings a sword; slimes that wander and bats that chase;
       hearts; a key and a locked door; a switch that opens a gate in another
       room; a chest at the end. Art and sounds: Kenney's Pixel Platformer (CC0),
       pressed into service for walls and floors. -->

  <!-- The game's state, kept across rooms. -->
  <q:set name="hearts" value="3" type="number" />
  <q:set name="keys" value="0" type="number" />
  <q:set name="taken" value="[]" type="array" />      <!-- things picked up, by name -->
  <q:set name="opened" value="[]" type="array" />     <!-- doors and gates opened, by name -->
  <q:set name="message" value="" />

  <qg:tileset name="kenney" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="chars" src="assets/kenney/tilemap-characters_packed.png" tile="24" />

  <qg:sound name="hit" src="assets/kenney/audio/stomp.ogg" />
  <qg:sound name="hurt" src="assets/kenney/audio/hurt.ogg" />
  <qg:sound name="pick" src="assets/kenney/audio/coin.ogg" />
  <qg:sound name="open" src="assets/kenney/audio/block.ogg" />
  <qg:sound name="win" src="assets/kenney/audio/win.ogg" />

  <qg:prefab name="Key" tag="key" sheet="kenney" frame="27" hitbox="12x12" />
  <qg:prefab name="Heart" tag="heart" sheet="kenney" frame="44" hitbox="12x12" />
  <qg:prefab name="Door" tag="door" sheet="kenney" frame="9" hitbox="18x18" solid="true" />
  <qg:prefab name="Gate" tag="gate" sheet="kenney" frame="21" hitbox="18x18" solid="true" />
  <qg:prefab name="Switch" tag="switch" sheet="kenney" frame="111" hitbox="14x14" />
  <qg:prefab name="SwitchOn" tag="switch-on" sheet="kenney" frame="112" hitbox="14x14" />
  <qg:prefab name="Sign" tag="sign" sheet="kenney" frame="86" hitbox="18x18" solid="true" />
  <qg:prefab name="Chest" tag="chest" sheet="kenney" frame="8" hitbox="16x16" />

  <qg:prefab name="Slime" tag="enemy" sheet="chars" frame="18" hitbox="14x14"
             ai="wander" speed="25">
    <qg:animation name="walk" frames="18,19,20" fps="6" />
  </qg:prefab>
  <qg:prefab name="Bat" tag="enemy" sheet="chars" frame="24" hitbox="14x14"
             ai="chase" speed="40" sight="90">
    <qg:animation name="walk" frames="24,25,26" fps="10" />
  </qg:prefab>

  <!-- ===== Room 1: the entrance. East to room 2. ===== -->

  <qg:scene name="room-1" width="256" height="224" background="#2b2b3a" seed="1">
    <q:function name="hurt" params="me">
      <qg:play sound="hurt" />
      <q:set name="hearts" value="{hearts - 1}" />
      <q:if condition="{hearts <= 0}">
        <qg:goto-scene name="game-over" />
      </q:if>
    </q:function>

    <qg:tilemap tileset="kenney" collision="true">
25,25,25,25,25,25,25,25,25,25,25,25,25,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,0
25,0,0,0,0,0,0,0,0,0,0,0,0,0
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,25,25,25,25,25,25,25,25,25,25,25,25,25
    </qg:tilemap>

    <qg:character id="player" controller="topdown" sheet="chars" frame="0"
                  x="60" y="108" hitbox="14x14" speed="70"
                  attack-action="jump" attack-reach="16" attack-frames="12" attack-sound="hit">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1,2" fps="8" />
      <qg:on-collision with="sign">
        <q:set name="message" value="THE KEY IS NORTH. THE SWITCH IS SOUTH." />
      </qg:on-collision>
      <qg:on-collision with="enemy" cooldown="60">
        <q:call function="hurt" args="me" />
      </qg:on-collision>
      <qg:on-hit with="enemy">
        <qg:destroy target="other" />
      </qg:on-hit>
    </qg:character>

    <qg:instance prefab="Sign" x="99" y="63" />
    <qg:instance prefab="Slime" name="slime-1" x="180" y="150" if="{'slime-1' not in taken}" />

    <qg:exit name="east" x="252" y="99" width="8" height="36" to="room-2" at="west" />

    <qg:hud position="top-left">
      <qg:counter bind="hearts" label="HEARTS" />
      <qg:counter bind="keys" label="KEYS" />
      <qg:text bind="message" />
    </qg:hud>
  </qg:scene>

  <!-- ===== Room 2: the crossing. West to 1, north to 3, south to 4, east (locked) to 5. ===== -->

  <qg:scene name="room-2" width="256" height="224" background="#2b2b3a" seed="2">
    <q:function name="hurt" params="me">
      <qg:play sound="hurt" />
      <q:set name="hearts" value="{hearts - 1}" />
      <q:if condition="{hearts <= 0}">
        <qg:goto-scene name="game-over" />
      </q:if>
    </q:function>

    <qg:tilemap tileset="kenney" collision="true">
25,25,25,25,25,25,0,0,25,25,25,25,25,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,25,25,25,25,25,0,0,25,25,25,25,25,25
    </qg:tilemap>

    <qg:character id="player" controller="topdown" sheet="chars" frame="0"
                  x="126" y="108" hitbox="14x14" speed="70"
                  attack-action="jump" attack-reach="16" attack-frames="12" attack-sound="hit">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1,2" fps="8" />
      <qg:on-collision with="enemy" cooldown="60">
        <q:call function="hurt" args="me" />
      </qg:on-collision>
      <qg:on-hit with="enemy">
        <qg:destroy target="other" />
      </qg:on-hit>
      <qg:on-collision with="door">
        <q:if condition="{keys > 0}">
          <q:set name="keys" value="{keys - 1}" />
          <q:set name="opened" value="{opened + [other.name]}" />
          <qg:play sound="open" />
          <qg:destroy target="other" />
        <q:else>
          <q:set name="message" value="LOCKED. FIND THE KEY." />
        </q:else>
        </q:if>
      </qg:on-collision>
    </qg:character>

    <qg:instance prefab="Bat" name="bat-1" x="190" y="60" if="{'bat-1' not in taken}" />
    <qg:instance prefab="Door" name="door-1" x="225" y="108" if="{'door-1' not in opened}" />

    <qg:exit name="west" x="-4" y="99" width="8" height="36" to="room-1" at="east" />
    <qg:exit name="north" x="117" y="-4" width="36" height="8" to="room-3" at="south" />
    <qg:exit name="south" x="117" y="220" width="36" height="8" to="room-4" at="north" />
    <qg:exit name="east" x="252" y="99" width="8" height="36" to="room-5" at="west" />

    <qg:hud position="top-left">
      <qg:counter bind="hearts" label="HEARTS" />
      <qg:counter bind="keys" label="KEYS" />
      <qg:text bind="message" />
    </qg:hud>
  </qg:scene>

  <!-- ===== Room 3: the key, guarded. South to 2. ===== -->

  <qg:scene name="room-3" width="256" height="224" background="#2b2b3a" seed="3">
    <q:function name="hurt" params="me">
      <qg:play sound="hurt" />
      <q:set name="hearts" value="{hearts - 1}" />
      <q:if condition="{hearts <= 0}">
        <qg:goto-scene name="game-over" />
      </q:if>
    </q:function>

    <qg:tilemap tileset="kenney" collision="true">
25,25,25,25,25,25,25,25,25,25,25,25,25,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,25,25,0,0,25,25,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,25,25,0,0,25,25,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,25,25,25,25,25,0,0,25,25,25,25,25,25
    </qg:tilemap>

    <qg:character id="player" controller="topdown" sheet="chars" frame="0"
                  x="126" y="190" hitbox="14x14" speed="70"
                  attack-action="jump" attack-reach="16" attack-frames="12" attack-sound="hit">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1,2" fps="8" />
      <qg:on-collision with="enemy" cooldown="60">
        <q:call function="hurt" args="me" />
      </qg:on-collision>
      <qg:on-hit with="enemy">
        <qg:destroy target="other" />
      </qg:on-hit>
      <qg:on-collision with="key">
        <qg:play sound="pick" />
        <q:set name="keys" value="{keys + 1}" />
        <q:set name="taken" value="{taken + [other.name]}" />
        <qg:destroy target="other" />
      </qg:on-collision>
      <qg:on-collision with="heart">
        <qg:play sound="pick" />
        <q:set name="hearts" value="{hearts + 1}" />
        <q:set name="taken" value="{taken + [other.name]}" />
        <qg:destroy target="other" />
      </qg:on-collision>
    </qg:character>

    <qg:instance prefab="Key" name="key-1" x="126" y="99" if="{'key-1' not in taken}" />
    <qg:instance prefab="Heart" name="heart-1" x="45" y="45" if="{'heart-1' not in taken}" />
    <qg:instance prefab="Slime" name="slime-3" x="190" y="99" if="{'slime-3' not in taken}" />

    <qg:exit name="south" x="117" y="220" width="36" height="8" to="room-2" at="north" />

    <qg:hud position="top-left">
      <qg:counter bind="hearts" label="HEARTS" />
      <qg:counter bind="keys" label="KEYS" />
      <qg:text bind="message" />
    </qg:hud>
  </qg:scene>

  <!-- ===== Room 4: the switch. North to 2. ===== -->

  <qg:scene name="room-4" width="256" height="224" background="#2b2b3a" seed="4">
    <q:function name="hurt" params="me">
      <qg:play sound="hurt" />
      <q:set name="hearts" value="{hearts - 1}" />
      <q:if condition="{hearts <= 0}">
        <qg:goto-scene name="game-over" />
      </q:if>
    </q:function>

    <qg:tilemap tileset="kenney" collision="true">
25,25,25,25,25,25,0,0,25,25,25,25,25,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,25,25,25,25,25,25,25,25,25,25,25,25,25
    </qg:tilemap>

    <qg:character id="player" controller="topdown" sheet="chars" frame="0"
                  x="126" y="36" hitbox="14x14" speed="70"
                  attack-action="jump" attack-reach="16" attack-frames="12" attack-sound="hit">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1,2" fps="8" />
      <qg:on-collision with="enemy" cooldown="60">
        <q:call function="hurt" args="me" />
      </qg:on-collision>
      <qg:on-hit with="enemy">
        <qg:destroy target="other" />
      </qg:on-hit>
      <qg:on-hit with="switch">
        <qg:play sound="open" />
        <q:set name="opened" value="{opened + ['gate-1']}" />
        <q:set name="message" value="SOMETHING OPENED FAR AWAY." />
        <qg:swap target="other" prefab="SwitchOn" />
      </qg:on-hit>
    </qg:character>

    <qg:instance prefab="Switch" x="126" y="171" if="{'gate-1' not in opened}" />
    <qg:instance prefab="SwitchOn" x="126" y="171" if="{'gate-1' in opened}" />
    <qg:instance prefab="Bat" name="bat-2" x="60" y="150" if="{'bat-2' not in taken}" />

    <qg:exit name="north" x="117" y="-4" width="36" height="8" to="room-2" at="south" />

    <qg:hud position="top-left">
      <qg:counter bind="hearts" label="HEARTS" />
      <qg:counter bind="keys" label="KEYS" />
      <qg:text bind="message" />
    </qg:hud>
  </qg:scene>

  <!-- ===== Room 5: behind the locked door; the gate the switch opens. West to 2, east to 6. ===== -->

  <qg:scene name="room-5" width="256" height="224" background="#2b2b3a" seed="5">
    <q:function name="hurt" params="me">
      <qg:play sound="hurt" />
      <q:set name="hearts" value="{hearts - 1}" />
      <q:if condition="{hearts <= 0}">
        <qg:goto-scene name="game-over" />
      </q:if>
    </q:function>

    <qg:tilemap tileset="kenney" collision="true">
25,25,25,25,25,25,25,25,25,25,25,25,25,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,25,25,25,25,25
0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0
25,0,0,0,0,0,0,0,0,25,25,25,25,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,25,25,25,25,25,25,25,25,25,25,25,25,25
    </qg:tilemap>

    <qg:character id="player" controller="topdown" sheet="chars" frame="0"
                  x="36" y="108" hitbox="14x14" speed="70"
                  attack-action="jump" attack-reach="16" attack-frames="12" attack-sound="hit">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1,2" fps="8" />
      <qg:on-collision with="enemy" cooldown="60">
        <q:call function="hurt" args="me" />
      </qg:on-collision>
      <qg:on-hit with="enemy">
        <qg:destroy target="other" />
      </qg:on-hit>
      <qg:on-collision with="gate">
        <q:set name="message" value="A GATE. A SWITCH MUST OPEN IT." />
      </qg:on-collision>
    </qg:character>

    <!-- The gate stands in the corridor until the switch in room 4 is thrown. -->
    <qg:instance prefab="Gate" name="gate-1" x="171" y="99" if="{'gate-1' not in opened}" />
    <qg:instance prefab="Gate" name="gate-1b" x="171" y="117" if="{'gate-1' not in opened}" />
    <qg:instance prefab="Slime" name="slime-4" x="90" y="60" if="{'slime-4' not in taken}" />

    <qg:exit name="west" x="-4" y="99" width="8" height="36" to="room-2" at="east" />
    <qg:exit name="east" x="252" y="99" width="8" height="36" to="room-6" at="west" />

    <qg:hud position="top-left">
      <qg:counter bind="hearts" label="HEARTS" />
      <qg:counter bind="keys" label="KEYS" />
      <qg:text bind="message" />
    </qg:hud>
  </qg:scene>

  <!-- ===== Room 6: the chest. ===== -->

  <qg:scene name="room-6" width="256" height="224" background="#2b2b3a" seed="6">
    <qg:tilemap tileset="kenney" collision="true">
25,25,25,25,25,25,25,25,25,25,25,25,25,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
0,0,0,0,0,0,0,0,0,0,0,0,0,25
0,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,0,0,0,0,0,0,0,0,0,0,0,0,25
25,25,25,25,25,25,25,25,25,25,25,25,25,25
    </qg:tilemap>

    <qg:character id="player" controller="topdown" sheet="chars" frame="0"
                  x="36" y="108" hitbox="14x14" speed="70"
                  attack-action="jump" attack-reach="16" attack-frames="12" attack-sound="hit">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1,2" fps="8" />
      <qg:on-collision with="chest">
        <qg:play sound="win" />
        <q:set name="message" value="THE TREASURE OF THE KEEP IS YOURS." />
        <qg:goto-scene name="the-end" />
      </qg:on-collision>
    </qg:character>

    <qg:instance prefab="Chest" x="190" y="108" />

    <qg:exit name="west" x="-4" y="99" width="8" height="36" to="room-5" at="east" />

    <qg:hud position="top-left">
      <qg:counter bind="hearts" label="HEARTS" />
      <qg:counter bind="keys" label="KEYS" />
      <qg:text bind="message" />
    </qg:hud>
  </qg:scene>

  <!-- ===== The end, and the game over ===== -->

  <qg:scene name="the-end" width="256" height="224" background="#102030">
    <qg:hud position="top-center">
      <qg:text bind="message" />
    </qg:hud>
  </qg:scene>

  <qg:scene name="game-over" width="256" height="224" background="#000000">
    <q:set name="title" value="YOU FELL. PRESS JUMP." />
    <qg:on-input action="jump">
      <q:set name="hearts" value="3" />
      <q:set name="keys" value="0" />
      <q:set name="taken" value="[]" />
      <q:set name="opened" value="[]" />
      <q:set name="message" value="" />
      <qg:goto-scene name="room-1" />
    </qg:on-input>
    <qg:hud position="top-center">
      <qg:text bind="title" />
    </qg:hud>
  </qg:scene>

</q:application>
