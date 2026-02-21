<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 15: Question Blocks

  Tests:
  - Question block with animation
  - Hit detection with visual feedback
  - Block changes to "used" state
  - Coin animation spawns upward
-->
<q:application id="question-blocks" type="game" engine="2d">
  <qg:scene name="main" width="256" height="144" background="#5C94FC">
    <qg:physics gravity-y="0.8" />

    <!-- Game state -->
    <q:set name="coins" value="0" type="number" />

    <!-- Preload used block texture (hidden sprite) -->
    <qg:sprite id="_preload_used" src="assets/smw/sprites/qblock_used.png"
               x="-100" y="-100" width="16" height="16" visible="false" />

    <!-- Question block prefab (solid, not sensor) -->
    <qg:prefab name="qblock">
      <qg:sprite src="assets/smw/sprites/qblock_animated.png"
                 frame-width="16" frame-height="16"
                 tag="qblock" body="static">
        <qg:animation name="shine" frames="0,1,2,3" speed="0.1" loop="true" auto-play="true" />
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

    <!-- Question blocks -->
    <qg:instance prefab="qblock" id="qblock1" x="80" y="56" />
    <qg:instance prefab="qblock" id="qblock2" x="112" y="56" />
    <qg:instance prefab="qblock" id="qblock3" x="144" y="56" />

    <!-- Floating coins -->
    <qg:instance prefab="coin" id="coin1" x="176" y="56" />
    <qg:instance prefab="coin" id="coin2" x="208" y="56" />

    <!-- Mario -->
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
    </qg:sprite>

    <!-- HUD -->
    <qg:hud position="top-left">
      <div style="color: #FFD700; font-family: monospace; font-size: 10px; text-shadow: 1px 1px #000;">
        COINS: <span id="coin-display">0</span> | Jump into ? blocks!
      </div>
    </qg:hud>

    <!-- Event handlers (simplified - no params) -->
    <qg:event name="coin-collected" handler="onCoinCollected" />
    <qg:event name="block-hit" handler="onBlockHit" />

    <q:function name="onCoinCollected">
      coins = coins + 1
      document.getElementById('coin-display').textContent = coins
    </q:function>

    <q:function name="onBlockHit">
      game.hitBlock(data.other, 'assets/smw/sprites/qblock_used.png', 'assets/smw/sprites/coin_animated.png', 16, 16)
      coins = coins + 1
      document.getElementById('coin-display').textContent = coins
    </q:function>
  </qg:scene>
</q:application>
