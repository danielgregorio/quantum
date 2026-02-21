<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 20: Full Level

  Complete game with all features:
  - Camera scrolling
  - Coins + HUD
  - Enemies
  - Question blocks
  - Checkpoints (visual)
  - Death zones
  - Goal flag
-->
<q:application id="full-level" type="game" engine="2d">
  <qg:scene name="main" width="768" height="144" viewport-width="256" viewport-height="144" background="#5C94FC">
    <qg:physics gravity-y="0.8" />
    <qg:camera follow="mario" lerp="0.08" bounds="scene" />

    <!-- Game state -->
    <q:set name="coins" value="0" type="number" />
    <q:set name="score" value="0" type="number" />
    <q:set name="lives" value="3" type="number" />

    <!-- Preload used block texture -->
    <qg:sprite id="_preload_used" src="assets/smw/sprites/qblock_used.png"
               x="-100" y="-100" width="16" height="16" visible="false" />

    <!-- Prefabs -->
    <qg:prefab name="coin">
      <qg:sprite src="assets/smw/sprites/coin_animated.png"
                 frame-width="16" frame-height="16"
                 tag="coin" body="static" sensor="true">
        <qg:animation name="spin" frames="0,1,2,3,2,1" speed="0.12" loop="true" auto-play="true" />
      </qg:sprite>
    </qg:prefab>

    <qg:prefab name="goomba">
      <qg:sprite src="assets/smw/sprites/goomba_walk.png"
                 frame-width="16" frame-height="16"
                 tag="enemy" body="dynamic" friction="0">
        <qg:animation name="walk" frames="0-1" speed="0.08" loop="true" auto-play="true" />
      </qg:sprite>
    </qg:prefab>

    <qg:prefab name="qblock">
      <qg:sprite src="assets/smw/sprites/qblock_animated.png"
                 frame-width="16" frame-height="16"
                 tag="qblock" body="static">
        <qg:animation name="shine" frames="0,1,2,3" speed="0.15" loop="true" auto-play="true" />
      </qg:sprite>
    </qg:prefab>

    <qg:prefab name="checkpoint">
      <qg:sprite width="8" height="32" color="#FFFFFF"
                 tag="checkpoint" body="static" sensor="true" />
    </qg:prefab>

    <qg:prefab name="goal">
      <qg:sprite width="8" height="48" color="#00FF00"
                 tag="goal" body="static" sensor="true" />
    </qg:prefab>

    <!-- Terrain -->
    <qg:tilemap id="level" src="assets/smw/sprites/stage1_unique.png"
                tile-width="16" tile-height="16">
      <qg:layer name="terrain" collision="true">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
9,9,9,9,9,9,9,9,9,9,9,0,0,0,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,0,0,0,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9
14,14,14,14,14,14,14,14,14,14,14,0,0,0,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,0,0,0,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
14,14,14,14,14,14,14,14,14,14,14,0,0,0,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,0,0,0,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
      </qg:layer>
    </qg:tilemap>

    <!-- Death zone -->
    <qg:sprite id="deathzone" width="768" height="16" x="384" y="180"
               tag="death" body="static" sensor="true" visible="false" />

    <!-- Question blocks -->
    <qg:instance prefab="qblock" id="qb1" x="96" y="48" />
    <qg:instance prefab="qblock" id="qb2" x="280" y="48" />
    <qg:instance prefab="qblock" id="qb3" x="500" y="48" />

    <!-- Coins -->
    <qg:instance prefab="coin" x="64" y="56" />
    <qg:instance prefab="coin" x="128" y="56" />
    <qg:instance prefab="coin" x="240" y="56" />
    <qg:instance prefab="coin" x="320" y="56" />
    <qg:instance prefab="coin" x="400" y="56" />
    <qg:instance prefab="coin" x="550" y="56" />
    <qg:instance prefab="coin" x="620" y="56" />

    <!-- Enemies -->
    <qg:instance prefab="goomba" id="g1" x="160" y="80" />
    <qg:instance prefab="goomba" id="g2" x="360" y="80" />
    <qg:instance prefab="goomba" id="g3" x="580" y="80" />

    <!-- Checkpoint -->
    <qg:instance prefab="checkpoint" id="cp1" x="430" y="64" />

    <!-- Goal -->
    <qg:instance prefab="goal" id="goal" x="740" y="56" />

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
      <qg:on-collision with-tag="enemy" action="emit:enemy-killed" />
      <qg:on-collision with-tag="enemy" action="destroy-other" />
      <qg:on-collision with-tag="qblock" action="emit:block-hit" />
      <qg:on-collision with-tag="checkpoint" action="emit:checkpoint-hit" />
      <qg:on-collision with-tag="death" action="emit:player-died" />
      <qg:on-collision with-tag="goal" action="emit:level-complete" />
    </qg:sprite>

    <!-- HUD -->
    <qg:hud position="top-left">
      <div style="color: #FFD700; font-family: monospace; font-size: 10px; text-shadow: 1px 1px #000;">
        COINS: <span id="coin-display">0</span> | SCORE: <span id="score-display">0</span> | LIVES: <span id="lives-display">3</span>
      </div>
    </qg:hud>

    <qg:hud position="center">
      <div id="level-complete" style="display: none; background: rgba(0,128,0,0.9); padding: 20px; text-align: center; color: #fff; font-family: monospace; border-radius: 10px;">
        <div style="font-size: 14px; color: #FFD700; margin-bottom: 10px;">LEVEL COMPLETE!</div>
        <div style="font-size: 10px; margin-bottom: 10px;">Final Score: <span id="final-score">0</span></div>
        <button onclick="location.reload()" style="padding: 5px 15px; cursor: pointer;">PLAY AGAIN</button>
      </div>
    </qg:hud>

    <!-- Events -->
    <qg:event name="coin-collected" handler="onCoinCollected" />
    <qg:event name="enemy-killed" handler="onEnemyKilled" />
    <qg:event name="block-hit" handler="onBlockHit" />
    <qg:event name="checkpoint-hit" handler="onCheckpointHit" />
    <qg:event name="player-died" handler="onPlayerDied" />
    <qg:event name="level-complete" handler="onLevelComplete" />

    <q:function name="onCoinCollected">
      coins = coins + 1
      score = score + 10
      document.getElementById('coin-display').textContent = coins
      document.getElementById('score-display').textContent = score
    </q:function>

    <q:function name="onEnemyKilled">
      score = score + 100
      document.getElementById('score-display').textContent = score
    </q:function>

    <q:function name="onBlockHit">
      game.hitBlock(data.other, 'assets/smw/sprites/qblock_used.png', 'assets/smw/sprites/coin_animated.png', 16, 16)
      coins = coins + 1
      score = score + 10
      document.getElementById('coin-display').textContent = coins
      document.getElementById('score-display').textContent = score
    </q:function>

    <q:function name="onCheckpointHit">
      score = score + 500
      document.getElementById('score-display').textContent = score
    </q:function>

    <q:function name="onPlayerDied">
      lives = lives - 1
      document.getElementById('lives-display').textContent = lives
      if (lives &lt;= 0) {
        alert('Game Over!')
        location.reload()
      }
    </q:function>

    <q:function name="onLevelComplete">
      score = score + 1000
      document.getElementById('final-score').textContent = score
      document.getElementById('level-complete').style.display = 'block'
    </q:function>
  </qg:scene>
</q:application>
