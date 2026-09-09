<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 14: Level Complete / Goal

  Tests:
  - Goal flag collision detection
  - Level complete screen
  - Restart mechanism

  Note: Full multi-scene support would require code generator changes.
        This phase demonstrates goal detection using collision system.
-->
<q:application id="level-complete" type="game" engine="2d">
  <qg:scene name="level1" width="256" height="144" background="#5C94FC">
    <qg:physics gravity-y="0.8" />

    <!-- Game state -->
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

    <!-- Coins to collect -->
    <qg:instance prefab="coin" x="80" y="56" />
    <qg:instance prefab="coin" x="128" y="56" />
    <qg:instance prefab="coin" x="176" y="56" />

    <!-- Goal flag (green rectangle) -->
    <qg:sprite id="goal" x="230" y="72" width="8" height="32"
               tag="goal" body="static" sensor="true" color="#00FF00" />

    <!-- Mario -->
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
      <!-- Goal reached -->
      <qg:on-collision with-tag="goal" action="emit:level-complete" />
    </qg:sprite>

    <!-- HUD -->
    <qg:hud position="top-left">
      <div style="color: #FFD700; font-family: monospace; font-size: 10px; text-shadow: 1px 1px #000;">
        COINS: <span id="coin-display">0</span> | Reach the green goal!
      </div>
    </qg:hud>

    <!-- Level Complete overlay -->
    <qg:hud position="center">
      <div id="level-complete-screen" style="display: none; background: rgba(0,128,0,0.9); padding: 20px; text-align: center; color: #fff; font-family: monospace; border-radius: 10px;">
        <div style="font-size: 14px; color: #FFD700; margin-bottom: 10px;">LEVEL COMPLETE!</div>
        <div style="font-size: 10px; margin-bottom: 10px;">Coins: <span id="final-coins">0</span></div>
        <button onclick="location.reload()" style="padding: 5px 15px; cursor: pointer; font-size: 12px;">PLAY AGAIN</button>
      </div>
    </qg:hud>

    <!-- Event handlers -->
    <qg:event name="coin-collected" handler="onCoinCollected" />
    <qg:event name="level-complete" handler="onLevelComplete" />

    <q:function name="onCoinCollected">
      coins = coins + 1
      document.getElementById('coin-display').textContent = coins
    </q:function>

    <q:function name="onLevelComplete">
      document.getElementById('final-coins').textContent = coins
      document.getElementById('level-complete-screen').style.display = 'block'
      <!-- Stop Mario -->
      const marioInfo = _sprites['mario']
      if (marioInfo &amp;&amp; marioInfo.body) {
        Matter.Body.setStatic(marioInfo.body, true)
      }
    </q:function>
  </qg:scene>
</q:application>
