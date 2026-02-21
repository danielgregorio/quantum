<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 12: Game Over / Restart

  Tests:
  - Death state (Mario falls in pit)
  - Game Over display
  - Restart mechanism

  Note: Falling below screen triggers death
-->
<q:application id="game-over" type="game" engine="2d">
  <qg:scene name="main" width="256" height="144" background="#5C94FC">
    <qg:physics gravity-y="0.8" />

    <!-- Game state -->
    <q:set name="lives" value="3" type="number" />

    <!-- Death zone (invisible sensor at bottom) -->
    <qg:sprite id="deathzone" width="256" height="16" x="128" y="180"
               tag="death" body="static" sensor="true" visible="false" />

    <qg:tilemap id="level" src="assets/smw/sprites/stage1_unique.png"
                tile-width="16" tile-height="16">
      <qg:layer name="terrain" collision="true">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
9,9,9,9,9,0,0,0,9,9,9,9,9,9,9,9
14,14,14,14,14,0,0,0,14,14,14,14,14,14,14,14
14,14,14,14,14,0,0,0,14,14,14,14,14,14,14,14
      </qg:layer>
    </qg:tilemap>

    <!-- Mario -->
    <qg:sprite id="mario" src="assets/smw/sprites/mario_small.png"
               x="32" y="60" tag="player"
               frame-width="16" frame-height="24"
               body="dynamic" controls="arrows" speed="0.4" jump-force="1.2" friction="0">
      <qg:animation name="idle" frames="0" speed="0.1" loop="true" auto-play="true" />
      <qg:animation name="walk" frames="1-3" speed="0.18" loop="true" />
      <qg:animation name="jump" frames="4" speed="0.1" loop="false" />
      <qg:on-collision with-tag="death" action="emit:player-died" />
    </qg:sprite>

    <!-- HUD -->
    <qg:hud position="top-left">
      <div style="color: #FFD700; font-family: monospace; font-size: 10px; text-shadow: 1px 1px #000;">
        LIVES: <span id="lives-display">3</span>
      </div>
    </qg:hud>

    <qg:hud position="center">
      <div id="game-over-screen" style="display: none; background: rgba(0,0,0,0.8); padding: 20px; text-align: center; color: #fff; font-family: monospace;">
        <div style="font-size: 16px; color: #FF0000; margin-bottom: 10px;">GAME OVER</div>
        <button onclick="location.reload()" style="padding: 5px 10px; cursor: pointer;">RESTART</button>
      </div>
    </qg:hud>

    <!-- Event handler -->
    <qg:event name="player-died" handler="onPlayerDied" />

    <q:function name="onPlayerDied">
      lives = lives - 1
      document.getElementById('lives-display').textContent = lives

      const marioInfo = _sprites['mario']
      if (!marioInfo) return

      if (lives &lt;= 0) {
        <!-- Game Over -->
        document.getElementById('game-over-screen').style.display = 'block'
        <!-- Disable Mario -->
        if (marioInfo.body) {
          Matter.Body.setStatic(marioInfo.body, true)
        }
      } else {
        <!-- Respawn -->
        Matter.Body.setPosition(marioInfo.body, { x: 32, y: 64 })
        Matter.Body.setVelocity(marioInfo.body, { x: 0, y: 0 })
      }
    </q:function>
  </qg:scene>
</q:application>
