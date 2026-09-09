<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 10: HUD and Score

  Tests:
  - HUD element fixed on screen
  - Score variable
  - Text display

  Note: HUD stays fixed while camera moves
-->
<q:application id="hud-score" type="game" engine="2d">
  <qg:scene name="main" width="512" height="144" viewport-width="256" viewport-height="144" background="#5C94FC">
    <qg:physics gravity-y="0.8" />
    <qg:camera follow="mario" lerp="0.08" bounds="scene" />

    <!-- Game state -->
    <q:set name="score" value="0" type="number" />
    <q:set name="coins" value="0" type="number" />

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
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,9,9,9,0,0,0,0,0,0,0,0,0,0,0,9,9,9,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9
14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
      </qg:layer>
    </qg:tilemap>

    <!-- Coins -->
    <qg:instance prefab="coin" x="112" y="56" />
    <qg:instance prefab="coin" x="144" y="56" />
    <qg:instance prefab="coin" x="336" y="56" />
    <qg:instance prefab="coin" x="368" y="56" />

    <!-- Mario with coin collection -->
    <qg:sprite id="mario" src="assets/smw/sprites/mario_small.png"
               x="32" y="60" tag="player"
               frame-width="16" frame-height="24"
               body="dynamic" controls="arrows" speed="0.4" jump-force="1.2" friction="0">
      <qg:animation name="idle" frames="0" speed="0.1" loop="true" auto-play="true" />
      <qg:animation name="walk" frames="1-3" speed="0.18" loop="true" />
      <qg:animation name="jump" frames="4" speed="0.1" loop="false" />
      <qg:on-collision with-tag="coin" action="emit:coin-collected" />
      <qg:on-collision with-tag="coin" action="destroy-other" />
    </qg:sprite>

    <!-- HUD with HTML overlay -->
    <qg:hud position="top-left">
      <div style="color: #FFD700; font-family: 'Press Start 2P', monospace; font-size: 8px; text-shadow: 1px 1px #000;">
        COINS: <span id="coin-display">0</span>
      </div>
    </qg:hud>

    <!-- Event handler for coin collection -->
    <qg:event name="coin-collected" handler="onCoinCollected" />

    <q:function name="onCoinCollected">
      coins = coins + 1
      document.getElementById('coin-display').textContent = coins
    </q:function>
  </qg:scene>
</q:application>
