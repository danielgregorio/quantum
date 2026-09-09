<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 11: Enemies

  Tests:
  - Enemy sprites with collision
  - Simple stomp detection
  - Lives system
-->
<q:application id="enemies" type="game" engine="2d">
  <qg:scene name="main" width="256" height="144" background="#5C94FC">
    <qg:physics gravity-y="0.8" />

    <!-- Game state -->
    <q:set name="coins" value="0" type="number" />
    <q:set name="lives" value="3" type="number" />

    <!-- Enemy prefab (goomba) -->
    <qg:prefab name="enemy">
      <qg:sprite src="assets/smw/sprites/goomba_walk.png"
                 frame-width="16" frame-height="16"
                 tag="enemy" body="dynamic" friction="0">
        <qg:animation name="walk" frames="0-1" speed="0.08" loop="true" auto-play="true" />
      </qg:sprite>
    </qg:prefab>

    <!-- Coin prefab -->
    <qg:prefab name="coin">
      <qg:sprite src="assets/smw/sprites/coin_animated.png"
                 frame-width="16" frame-height="16"
                 tag="coin" body="static" sensor="true">
        <qg:animation name="spin" frames="0,1,2,3,2,1" speed="0.12" loop="true" auto-play="true" />
      </qg:sprite>
    </qg:prefab>

    <qg:tilemap id="level" src="assets/smw/sprites/stage1_unique.png"
                tile-width="16" tile-height="16">
      <qg:layer name="terrain" collision="true">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9
14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
      </qg:layer>
    </qg:tilemap>

    <!-- Coins -->
    <qg:instance prefab="coin" x="80" y="56" />
    <qg:instance prefab="coin" x="176" y="56" />

    <!-- Enemies -->
    <qg:instance prefab="enemy" id="enemy1" x="128" y="80" />
    <qg:instance prefab="enemy" id="enemy2" x="192" y="80" />

    <!-- Mario with collision handlers -->
    <qg:sprite id="mario" src="assets/smw/sprites/mario_small.png"
               x="32" y="60" tag="player"
               frame-width="16" frame-height="24"
               body="dynamic" controls="arrows" speed="0.4" jump-force="1.2" friction="0">
      <qg:animation name="idle" frames="0" speed="0.1" loop="true" auto-play="true" />
      <qg:animation name="walk" frames="1-3" speed="0.18" loop="true" />
      <qg:animation name="jump" frames="4" speed="0.1" loop="false" />
      <!-- Coin collection -->
      <qg:on-collision with-tag="coin" action="emit:coin-collected" />
      <qg:on-collision with-tag="coin" action="destroy-other" />
      <!-- Enemy: just destroy for now (stomp logic would need more work) -->
      <qg:on-collision with-tag="enemy" action="destroy-other" />
    </qg:sprite>

    <!-- HUD -->
    <qg:hud position="top-left">
      <div style="color: #FFD700; font-family: monospace; font-size: 10px; text-shadow: 1px 1px #000;">
        COINS: <span id="coin-display">0</span> | Stomp enemies!
      </div>
    </qg:hud>

    <!-- Event handlers -->
    <qg:event name="coin-collected" handler="onCoinCollected" />

    <q:function name="onCoinCollected">
      coins = coins + 1
      document.getElementById('coin-display').textContent = coins
    </q:function>
  </qg:scene>
</q:application>
