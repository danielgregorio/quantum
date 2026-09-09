<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 18: Enemy AI (Simplified)

  Tests:
  - Multiple enemies in a scrolling level
  - Enemies can be defeated
-->
<q:application id="enemy-ai" type="game" engine="2d">
  <qg:scene name="main" width="512" height="144" viewport-width="256" viewport-height="144" background="#5C94FC">
    <qg:physics gravity-y="0.8" />
    <qg:camera follow="mario" lerp="0.08" bounds="scene" />

    <!-- Game state -->
    <q:set name="coins" value="0" type="number" />
    <q:set name="score" value="0" type="number" />

    <!-- Enemy prefab -->
    <qg:prefab name="goomba">
      <qg:sprite src="assets/smw/sprites/goomba_walk.png"
                 frame-width="16" frame-height="16"
                 tag="enemy" body="dynamic" friction="0.5">
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
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9
14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
      </qg:layer>
    </qg:tilemap>

    <!-- Coins scattered across level -->
    <qg:instance prefab="coin" x="80" y="56" />
    <qg:instance prefab="coin" x="160" y="56" />
    <qg:instance prefab="coin" x="240" y="56" />
    <qg:instance prefab="coin" x="320" y="56" />
    <qg:instance prefab="coin" x="400" y="56" />

    <!-- Multiple goombas -->
    <qg:instance prefab="goomba" id="goomba1" x="120" y="80" />
    <qg:instance prefab="goomba" id="goomba2" x="200" y="80" />
    <qg:instance prefab="goomba" id="goomba3" x="280" y="80" />
    <qg:instance prefab="goomba" id="goomba4" x="380" y="80" />

    <!-- Mario -->
    <qg:sprite id="mario" src="assets/smw/sprites/mario_small.png"
               x="32" y="60" tag="player"
               frame-width="16" frame-height="24"
               body="dynamic" controls="arrows" speed="0.4" jump-force="1.2" friction="0">
      <qg:animation name="idle" frames="0" speed="0.1" loop="true" auto-play="true" />
      <qg:animation name="walk" frames="1-3" speed="0.18" loop="true" />
      <qg:animation name="jump" frames="4" speed="0.1" loop="false" />
      <qg:on-collision with-tag="coin" action="emit:coin-collected" />
      <qg:on-collision with-tag="coin" action="destroy-other" />
      <qg:on-collision with-tag="enemy" action="emit:enemy-killed" />
      <qg:on-collision with-tag="enemy" action="destroy-other" />
    </qg:sprite>

    <!-- HUD -->
    <qg:hud position="top-left">
      <div style="color: #FFD700; font-family: monospace; font-size: 10px; text-shadow: 1px 1px #000;">
        COINS: <span id="coin-display">0</span> | SCORE: <span id="score-display">0</span>
      </div>
    </qg:hud>

    <!-- Event handlers -->
    <qg:event name="coin-collected" handler="onCoinCollected" />
    <qg:event name="enemy-killed" handler="onEnemyKilled" />

    <q:function name="onCoinCollected">
      coins = coins + 1
      document.getElementById('coin-display').textContent = coins
    </q:function>

    <q:function name="onEnemyKilled">
      score = score + 100
      document.getElementById('score-display').textContent = score
    </q:function>
  </qg:scene>
</q:application>
