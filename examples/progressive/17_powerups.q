<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 17: Power-ups

  Tests:
  - Question blocks spawn mushrooms when hit
  - Mushroom emerges and walks
  - Collecting mushroom transforms Mario to big
-->
<q:application id="powerups" type="game" engine="2d">
  <qg:scene name="main" width="256" height="144" background="#5C94FC">
    <qg:physics gravity-y="0.8" />

    <!-- Game state -->
    <q:set name="coins" value="0" type="number" />
    <q:set name="isBig" value="0" type="number" />

    <!-- Preload textures (hidden sprites) -->
    <qg:sprite id="_preload_used" src="assets/smw/sprites/qblock_used.png"
               x="-100" y="-100" width="16" height="16" visible="false" />
    <qg:sprite id="_preload_mushroom" src="assets/smw/sprites/mushroom.png"
               x="-100" y="-100" width="16" height="16" visible="false" />
    <qg:sprite id="_preload_big" src="assets/smw/sprites/mario_big.png"
               x="-100" y="-100" width="16" height="32" visible="false" />

    <!-- Question block prefab (solid) -->
    <qg:prefab name="qblock">
      <qg:sprite src="assets/smw/sprites/qblock_animated.png"
                 frame-width="16" frame-height="16"
                 tag="qblock" body="static">
        <qg:animation name="shine" frames="0,1,2,3" speed="0.15" loop="true" auto-play="true" />
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

    <!-- Question block (spawns mushroom) -->
    <qg:instance prefab="qblock" id="qblock1" x="128" y="48" />

    <!-- Regular coins -->
    <qg:instance prefab="coin" x="64" y="56" />
    <qg:instance prefab="coin" x="192" y="56" />

    <!-- Mario (same speed as phase 15) -->
    <qg:sprite id="mario" src="assets/smw/sprites/mario_small.png"
               x="32" y="60" tag="player"
               frame-width="16" frame-height="24"
               body="dynamic" controls="arrows" speed="1" jump-force="3.5" friction="0">
      <qg:animation name="idle" frames="0" speed="0.1" loop="true" auto-play="true" />
      <qg:animation name="walk" frames="1-3" speed="0.18" loop="true" />
      <qg:animation name="jump" frames="4" speed="0.1" loop="false" />
      <qg:on-collision with-tag="coin" action="emit:coin-collected" />
      <qg:on-collision with-tag="coin" action="destroy-other" />
      <qg:on-collision with-tag="qblock" action="emit:block-hit" />
      <qg:on-collision with-tag="powerup" action="emit:powerup-collected" />
      <qg:on-collision with-tag="powerup" action="destroy-other" />
    </qg:sprite>

    <!-- HUD -->
    <qg:hud position="top-left">
      <div style="color: #FFD700; font-family: monospace; font-size: 10px; text-shadow: 1px 1px #000;">
        COINS: <span id="coin-display">0</span> | <span id="size-display">SMALL</span>
      </div>
    </qg:hud>

    <!-- Event handlers -->
    <qg:event name="coin-collected" handler="onCoinCollected" />
    <qg:event name="block-hit" handler="onBlockHit" />
    <qg:event name="powerup-collected" handler="onPowerUpCollected" />

    <q:function name="onCoinCollected">
      coins = coins + 1
      document.getElementById('coin-display').textContent = coins
    </q:function>

    <q:function name="onBlockHit">
      if (!data || !data.other) return
      if (data.other._blockUsed) return
      game.hitBlock(data.other, 'assets/smw/sprites/qblock_used.png', null, 16, 16)
      game.spawnPowerUp(data.other, 'assets/smw/sprites/mushroom.png', 0.5)
    </q:function>

    <q:function name="onPowerUpCollected">
      if (!data || !data.other) return
      if (isBig) return
      isBig = 1
      game.powerUpPlayer('mario', 'assets/smw/sprites/mario_big.png', 16, 32)
      document.getElementById('size-display').textContent = 'BIG!'
      document.getElementById('size-display').style.color = '#00FF00'
    </q:function>
  </qg:scene>
</q:application>
