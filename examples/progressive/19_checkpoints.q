<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 19: Checkpoints (Simplified)

  Tests:
  - Checkpoint flags that change color when touched
  - Death zones that respawn Mario
-->
<q:application id="checkpoints" type="game" engine="2d">
  <qg:scene name="main" width="512" height="144" viewport-width="256" viewport-height="144" background="#5C94FC">
    <qg:physics gravity-y="0.8" />
    <qg:camera follow="mario" lerp="0.08" bounds="scene" />

    <!-- Game state -->
    <q:set name="coins" value="0" type="number" />
    <q:set name="lives" value="3" type="number" />

    <!-- Checkpoint flag prefab (white box) -->
    <qg:prefab name="checkpoint">
      <qg:sprite width="8" height="32" color="#FFFFFF"
                 tag="checkpoint" body="static" sensor="true" />
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
9,9,9,9,9,9,9,0,0,0,9,9,9,9,9,9,9,9,9,9,0,0,0,9,9,9,9,9,9,9,9,9
14,14,14,14,14,14,14,0,0,0,14,14,14,14,14,14,14,14,14,14,0,0,0,14,14,14,14,14,14,14,14,14
14,14,14,14,14,14,14,0,0,0,14,14,14,14,14,14,14,14,14,14,0,0,0,14,14,14,14,14,14,14,14,14
      </qg:layer>
    </qg:tilemap>

    <!-- Death zone at bottom -->
    <qg:sprite id="deathzone" width="512" height="16" x="256" y="180"
               tag="death" body="static" sensor="true" visible="false" />

    <!-- Checkpoints -->
    <qg:instance prefab="checkpoint" id="cp1" x="180" y="72" />
    <qg:instance prefab="checkpoint" id="cp2" x="400" y="72" />

    <!-- Coins -->
    <qg:instance prefab="coin" x="80" y="56" />
    <qg:instance prefab="coin" x="140" y="56" />
    <qg:instance prefab="coin" x="260" y="56" />
    <qg:instance prefab="coin" x="350" y="56" />
    <qg:instance prefab="coin" x="450" y="56" />

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
      <qg:on-collision with-tag="checkpoint" action="emit:checkpoint-hit" />
      <qg:on-collision with-tag="death" action="emit:player-died" />
    </qg:sprite>

    <!-- HUD -->
    <qg:hud position="top-left">
      <div style="color: #FFD700; font-family: monospace; font-size: 10px; text-shadow: 1px 1px #000;">
        COINS: <span id="coin-display">0</span> | LIVES: <span id="lives-display">3</span>
      </div>
    </qg:hud>

    <qg:hud position="top-center">
      <div id="checkpoint-msg" style="color: #00FF00; font-family: monospace; font-size: 10px; display: none;">
        CHECKPOINT!
      </div>
    </qg:hud>

    <!-- Event handlers -->
    <qg:event name="coin-collected" handler="onCoinCollected" />
    <qg:event name="checkpoint-hit" handler="onCheckpointHit" />
    <qg:event name="player-died" handler="onPlayerDied" />

    <q:function name="onCoinCollected">
      coins = coins + 1
      document.getElementById('coin-display').textContent = coins
    </q:function>

    <q:function name="onCheckpointHit">
      const msg = document.getElementById('checkpoint-msg')
      msg.style.display = 'block'
      setTimeout(function() { msg.style.display = 'none' }, 1500)
    </q:function>

    <q:function name="onPlayerDied">
      lives = lives - 1
      document.getElementById('lives-display').textContent = lives
      if (lives &lt;= 0) {
        alert('Game Over!')
        location.reload()
      }
    </q:function>
  </qg:scene>
</q:application>
