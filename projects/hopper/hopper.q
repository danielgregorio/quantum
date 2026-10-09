<q:application id="hopper" type="game">

  <!-- Hopper: the platformer that drives the game language (PLAN_GAMES_2.md).
       This is its first slice: one screen, a character that walks and jumps
       on a tilemap, a coin to collect, a counter in the HUD. Art: Kenney's
       Pixel Platformer (CC0), in assets/kenney/. -->

  <qg:tileset name="kenney" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="chars" src="assets/kenney/tilemap-characters_packed.png" tile="24" />

  <qg:prefab name="Coin" tag="coin" sheet="kenney" frame="151" hitbox="12x12" />

  <qg:scene name="level-1" width="256" height="224" background="#5c94fc" seed="7">
    <q:set name="coins" value="0" type="number" />

    <!-- 16 columns x 13 rows of 18 px = 288 x 234. 0 is empty; 23 is the grass
         top, 25 the dirt below it, 11 a bush. -->
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
23,23,23,23,23,23,23,23,23,23,23,23,23,23,23,23
25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25
25,25,25,25,25,25,25,25,25,25,25,25,25,25,25,25
    </qg:tilemap>

    <qg:character id="player" controller="platformer" sheet="chars" frame="0"
                  x="40" y="160" hitbox="18x22"
                  run-speed="90" jump-height="64" variable-jump="true" coyote-frames="6">
      <qg:on-collision with="coin">
        <qg:destroy target="other" />
        <q:set name="coins" value="{coins + 1}" />
      </qg:on-collision>
    </qg:character>

    <qg:instance prefab="Coin" x="120" y="160" />
    <qg:instance prefab="Coin" x="171" y="96" />

    <qg:camera follow="player" bounds="tilemap" />

    <qg:hud position="top-left">
      <qg:counter bind="coins" label="COINS" />
    </qg:hud>
  </qg:scene>

</q:application>
