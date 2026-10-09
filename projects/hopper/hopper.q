<q:application id="hopper" type="game">

  <!-- Hopper: the platformer that drives the game language (PLAN_GAMES_2.md).
       One screen so far: a character that walks and jumps on a tilemap, coins,
       a walker to stomp or be hurt by, a pit to fall into, a counter in the
       HUD. Art and sounds: Kenney's Pixel Platformer (CC0), in assets/kenney/. -->

  <qg:tileset name="kenney" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="chars" src="assets/kenney/tilemap-characters_packed.png" tile="24" />

  <qg:sound name="jump" src="assets/kenney/audio/jump.ogg" />
  <qg:sound name="coin" src="assets/kenney/audio/coin.ogg" />
  <qg:sound name="stomp" src="assets/kenney/audio/stomp.ogg" />
  <qg:sound name="hurt" src="assets/kenney/audio/hurt.ogg" />

  <qg:prefab name="Coin" tag="coin" sheet="kenney" frame="151" hitbox="12x12" />

  <qg:prefab name="Walker" tag="enemy" sheet="chars" frame="18" hitbox="18x18"
             ai="patrol" speed="30" direction="left" turns-at="edge">
    <qg:animation name="walk" frames="18,19,20" fps="6" />
  </qg:prefab>

  <qg:scene name="level-1" width="256" height="224" background="#5c94fc" seed="7">
    <q:set name="coins" value="0" type="number" />
    <q:set name="score" value="0" type="number" />
    <q:set name="lives" value="3" type="number" />

    <!-- 16 columns x 13 rows of 18 px = 288 x 234. 0 is empty; 23 is the grass
         top, 25 the dirt below it. A platform at row 6, a pit at columns 13-14. -->
    <qg:tilemap tileset="kenney" collision="true">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,23,23,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
23,23,23,23,23,23,23,23,23,23,23,23,23,0,0,23
25,25,25,25,25,25,25,25,25,25,25,25,25,0,0,25
25,25,25,25,25,25,25,25,25,25,25,25,25,0,0,25
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

      <qg:on-collision with="enemy" side="top">
        <qg:destroy target="other" />
        <qg:bounce target="me" height="32" />
        <qg:play sound="stomp" />
        <q:set name="score" value="{score + 100}" />
      </qg:on-collision>

      <qg:on-collision with="enemy" side="any" cooldown="60">
        <qg:play sound="hurt" />
        <q:set name="lives" value="{lives - 1}" />
        <qg:respawn target="me" />
      </qg:on-collision>

      <qg:on-fall>
        <qg:play sound="hurt" />
        <q:set name="lives" value="{lives - 1}" />
        <qg:respawn target="me" />
      </qg:on-fall>
    </qg:character>

    <qg:instance prefab="Coin" x="120" y="160" />
    <qg:instance prefab="Coin" x="171" y="96" />
    <qg:instance prefab="Walker" x="200" y="160" />

    <qg:camera follow="player" bounds="tilemap" />

    <qg:hud position="top-left">
      <qg:counter bind="score" label="SCORE" />
      <qg:counter bind="coins" label="COINS" />
      <qg:counter bind="lives" label="LIVES" />
    </qg:hud>
  </qg:scene>

</q:application>
