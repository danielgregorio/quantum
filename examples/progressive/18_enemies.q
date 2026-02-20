<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 18: Yoshi's Island 1 (Simplified)

  Recreation of the first level from SMW with:
  - Rex enemies (purple dinosaurs)
  - Camera scrolling
  - Real enemy positions (scaled)
  - Stomp mechanic (2 hits to kill Rex)

  Original level: ~432 tiles wide
  Our version: 96 tiles (1536 pixels) - scaled positions
-->
<q:application id="yoshi-island-1" type="game" engine="2d">
  <qg:scene name="main" width="1536" height="224" viewport-width="256" viewport-height="224" background="#5C94FC">
    <qg:physics gravity-y="1.2" />
    <qg:camera follow="mario" lerp="0.08" bounds="scene" />

    <!-- Game state -->
    <q:set name="coins" value="0" type="number" />
    <q:set name="score" value="0" type="number" />
    <q:set name="lives" value="3" type="number" />
    <q:set name="isDead" value="0" type="number" />

    <!-- Preload textures -->
    <qg:sprite id="_preload_used" src="assets/smw/sprites/qblock_used.png"
               x="-100" y="-100" width="16" height="16" visible="false" />
    <qg:sprite id="_preload_death" src="assets/smw/sprites/mario_death.png"
               x="-100" y="-100" width="16" height="16" visible="false" />

    <!-- Sound Effects -->
    <qg:sound id="sfx-jump" src="assets/smw/sounds/smw_jump.wav" trigger="player.jump" />
    <qg:sound id="sfx-coin" src="assets/smw/sounds/smw_coin.wav" trigger="coin-collected" />
    <qg:sound id="sfx-stomp" src="assets/smw/sounds/smw_stomp.wav" trigger="enemy-stomped" />
    <qg:sound id="sfx-death" src="assets/smw/sounds/smw_lost_a_life.wav" trigger="mario-died" />
    <qg:sound id="sfx-clear" src="assets/smw/sounds/smw_course_clear.wav" trigger="level-complete" />
    <qg:sound id="sfx-block" src="assets/smw/sounds/smw_message_block.wav" trigger="block-hit" />

    <!-- Background Music -->
    <qg:sound id="bgm-level" src="assets/smw/sounds/music/music-map1.wav"
              trigger="scene.start" loop="true" volume="0.5" channel="music" />

    <!-- Prefabs -->
    <qg:prefab name="qblock">
      <qg:sprite src="assets/smw/sprites/qblock_animated.png"
                 frame-width="16" frame-height="16"
                 tag="qblock" body="static">
        <qg:animation name="shine" frames="0,1,2,3" speed="0.15" loop="true" auto-play="true" />
      </qg:sprite>
    </qg:prefab>

    <qg:prefab name="coin">
      <qg:sprite src="assets/smw/sprites/coin_animated.png"
                 frame-width="16" frame-height="16"
                 tag="coin" body="static" sensor="true">
        <qg:animation name="spin" frames="0,1,2,3,2,1" speed="0.12" loop="true" auto-play="true" />
      </qg:sprite>
    </qg:prefab>

    <qg:prefab name="rex">
      <qg:sprite src="assets/smw/sprites/rex_walk.png"
                 frame-width="12" frame-height="24"
                 tag="enemy" body="dynamic" friction="0">
        <qg:animation name="walk" frames="0-1" speed="0.15" loop="true" auto-play="true" />
      </qg:sprite>
    </qg:prefab>

    <!-- Terrain - 96 tiles wide (1536px), 14 tiles tall (224px) - SNES resolution -->
    <!-- Ground at rows 12-13 -->
    <qg:tilemap id="level" src="assets/smw/sprites/stage1_unique.png"
                tile-width="16" tile-height="16">
      <qg:layer name="terrain" collision="true">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9
14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
      </qg:layer>
    </qg:tilemap>

    <!-- Question blocks (y=112, above ground) -->
    <qg:instance prefab="qblock" id="qb1" x="160" y="112" />
    <qg:instance prefab="qblock" id="qb2" x="400" y="112" />
    <qg:instance prefab="qblock" id="qb3" x="700" y="112" />
    <qg:instance prefab="qblock" id="qb4" x="1100" y="112" />

    <!-- Coins (y=120, floating above ground) -->
    <qg:instance prefab="coin" x="128" y="120" />
    <qg:instance prefab="coin" x="240" y="120" />
    <qg:instance prefab="coin" x="500" y="120" />
    <qg:instance prefab="coin" x="800" y="120" />
    <qg:instance prefab="coin" x="1000" y="120" />
    <qg:instance prefab="coin" x="1300" y="120" />

    <!-- Rex enemies on ground (y=152, ground is at 176, Rex is 24px tall) -->
    <qg:instance prefab="rex" id="rex1" x="180" y="152" />
    <qg:instance prefab="rex" id="rex2" x="280" y="152" />
    <qg:instance prefab="rex" id="rex3" x="350" y="152" />
    <qg:instance prefab="rex" id="rex4" x="450" y="152" />
    <qg:instance prefab="rex" id="rex5" x="550" y="152" />
    <qg:instance prefab="rex" id="rex6" x="650" y="152" />
    <qg:instance prefab="rex" id="rex7" x="750" y="152" />
    <qg:instance prefab="rex" id="rex8" x="900" y="152" />
    <qg:instance prefab="rex" id="rex9" x="1050" y="152" />
    <qg:instance prefab="rex" id="rex10" x="1200" y="152" />

    <!-- Goal at the end -->
    <qg:sprite id="goal" width="8" height="48" x="1480" y="152"
               color="#00FF00" tag="goal" body="static" sensor="true" />

    <!-- Mario (on ground at y=152) -->
    <qg:sprite id="mario" src="assets/smw/sprites/mario_small.png"
               x="64" y="152" tag="player"
               frame-width="16" frame-height="24"
               body="dynamic" controls="arrows" speed="2" jump-force="7" friction="0">
      <qg:animation name="idle" frames="0" speed="0.1" loop="true" auto-play="true" />
      <qg:animation name="walk" frames="1-3" speed="0.18" loop="true" />
      <qg:animation name="jump" frames="4" speed="0.1" loop="false" />
      <qg:on-collision with-tag="coin" action="emit:coin-collected" />
      <qg:on-collision with-tag="coin" action="destroy-other" />
      <qg:on-collision with-tag="qblock" action="emit:block-hit" />
      <qg:on-collision with-tag="enemy" action="emit:enemy-collision" />
      <qg:on-collision with-tag="death" action="emit:fell-in-pit" />
      <qg:on-collision with-tag="goal" action="emit:level-complete" />
    </qg:sprite>

    <!-- HUD -->
    <qg:hud position="top-left">
      <div style="color: #FFD700; font-family: monospace; font-size: 14px; text-shadow: 1px 1px #000;">
        MARIO x <span id="lives-display">3</span> | COINS: <span id="coin-display">0</span> | SCORE: <span id="score-display">0</span>
      </div>
    </qg:hud>

    <qg:hud position="center">
      <div id="game-over" style="display: none; background: rgba(0,0,0,0.9); padding: 20px; text-align: center; color: #fff; font-family: monospace; border-radius: 10px;">
        <div style="font-size: 18px; color: #FF4444; margin-bottom: 10px;">GAME OVER</div>
        <div style="font-size: 12px; margin-bottom: 10px;">Final Score: <span id="gameover-score">0</span></div>
        <button onclick="location.reload()" style="padding: 8px 20px; cursor: pointer; font-size: 14px;">TRY AGAIN</button>
      </div>
    </qg:hud>

    <qg:hud position="center">
      <div id="level-complete" style="display: none; background: rgba(0,128,0,0.9); padding: 20px; text-align: center; color: #fff; font-family: monospace; border-radius: 10px;">
        <div style="font-size: 18px; color: #FFD700; margin-bottom: 10px;">COURSE CLEAR!</div>
        <div style="font-size: 12px; margin-bottom: 10px;">Score: <span id="final-score">0</span></div>
        <button onclick="location.reload()" style="padding: 8px 20px; cursor: pointer; font-size: 14px;">PLAY AGAIN</button>
      </div>
    </qg:hud>

    <!-- Death zone at bottom (below visible area) -->
    <qg:sprite id="deathzone" width="1536" height="16" x="768" y="250"
               tag="death" body="static" sensor="true" visible="false" />

    <!-- Events -->
    <qg:event name="coin-collected" handler="onCoinCollected" />
    <qg:event name="block-hit" handler="onBlockHit" />
    <qg:event name="enemy-collision" handler="onEnemyCollision" />
    <qg:event name="fell-in-pit" handler="onFellInPit" />
    <qg:event name="death-animation-complete" handler="onDeathAnimationComplete" />
    <qg:event name="level-complete" handler="onLevelComplete" />
    <qg:event name="game-init" handler="onGameInit" />

    <q:function name="onGameInit">
      // Iris-in effect on level start
      game.irisIn(null, 45)

      // Restore lives and score from sessionStorage (after death respawn)
      const savedLives = sessionStorage.getItem('mario_lives')
      const savedScore = sessionStorage.getItem('mario_score')
      if (savedLives !== null) {
        lives = parseInt(savedLives)
        document.getElementById('lives-display').textContent = lives
        sessionStorage.removeItem('mario_lives')
      }
      if (savedScore !== null) {
        score = parseInt(savedScore)
        document.getElementById('score-display').textContent = score
        sessionStorage.removeItem('mario_score')
      }

      // Setup Rex AI - all walk left
      game.setRexAI('rex1', -0.4)
      game.setRexAI('rex2', -0.4)
      game.setRexAI('rex3', -0.4)
      game.setRexAI('rex4', -0.4)
      game.setRexAI('rex5', -0.4)
      game.setRexAI('rex6', -0.4)
      game.setRexAI('rex7', -0.4)
      game.setRexAI('rex8', -0.4)
      game.setRexAI('rex9', -0.4)
      game.setRexAI('rex10', -0.4)

      // Handle music autoplay - try to play, if blocked wait for interaction
      const tryPlayMusic = () => {
        game.playSound('bgm-level', { loop: true, volume: 0.5 })
      }
      // Browser autoplay requires user gesture - add click handler
      const startMusic = () => {
        tryPlayMusic()
        document.removeEventListener('click', startMusic)
        document.removeEventListener('keydown', startMusic)
      }
      document.addEventListener('click', startMusic, { once: true })
      document.addEventListener('keydown', startMusic, { once: true })
    </q:function>

    <q:function name="onCoinCollected">
      coins = coins + 1
      score = score + 10
      document.getElementById('coin-display').textContent = coins
      document.getElementById('score-display').textContent = score
    </q:function>

    <q:function name="onBlockHit">
      if (!data || !data.other) return
      if (data.other._blockUsed) return
      game.hitBlock(data.other, 'assets/smw/sprites/qblock_used.png', 'assets/smw/sprites/coin_animated.png', 16, 16)
      coins = coins + 1
      score = score + 10
      document.getElementById('coin-display').textContent = coins
      document.getElementById('score-display').textContent = score
    </q:function>

    <q:function name="onEnemyCollision">
      if (!data || !data.other) return
      if (isDead) return
      const mario = _sprites['mario']
      const enemy = data.other
      if (!mario || !enemy || !mario.body || !enemy.body) return

      // Rex is 12x24, Mario is 16x24
      // Body positions are at center
      const marioFeet = mario.body.position.y + 12
      const rexHead = enemy.body.position.y - (enemy._rexSquished ? 6 : 12)
      const marioVelY = mario.body.velocity.y

      // Stomp: Mario's feet must be above Rex's head AND Mario must be falling
      // More strict check: feet must be clearly above head (not just touching)
      const isAbove = marioFeet &lt; rexHead + 4
      const isFalling = marioVelY > 0.5

      if (isAbove &amp;&amp; isFalling) {
        // Stomp! Emit sound event
        _gameEvents.emit('enemy-stomped', { enemy: enemy.id })

        // Check if Rex already squished
        if (enemy._rexSquished) {
          // Second stomp - kill Rex
          game.destroySprite(enemy.id)
          score = score + 200
        } else {
          // First stomp - squish Rex (makes it shorter and faster)
          enemy._rexSquished = true
          enemy.sprite.scale.y = 0.5
          enemy._rexSpeed = (enemy._rexSpeed || 0.4) * 1.5
          score = score + 100
        }
        // Bounce Mario up
        Matter.Body.setVelocity(mario.body, { x: mario.body.velocity.x, y: -6 })
        document.getElementById('score-display').textContent = score
      } else {
        // Side collision - Mario dies!
        isDead = 1
        lives = lives - 1
        document.getElementById('lives-display').textContent = lives
        _gameEvents.emit('mario-died', {})
        game.killPlayer('mario')
      }
    </q:function>

    <q:function name="onFellInPit">
      if (isDead) return
      isDead = 1
      lives = lives - 1
      document.getElementById('lives-display').textContent = lives
      _gameEvents.emit('mario-died', {})
      game.killPlayer('mario')
    </q:function>

    <q:function name="onDeathAnimationComplete">
      // Iris-out effect before transition
      game.irisOut(function() {
        if (lives &lt;= 0) {
          // Game Over
          document.getElementById('gameover-score').textContent = score
          document.getElementById('game-over').style.display = 'block'
        } else {
          // Reload entire level (enemies, blocks, everything back to initial state)
          // Store lives in sessionStorage to preserve across reload
          sessionStorage.setItem('mario_lives', lives)
          sessionStorage.setItem('mario_score', score)
          location.reload()
        }
      }, 30)
    </q:function>

    <q:function name="onLevelComplete">
      // Stop background music
      game.stopSound('bgm-level')
      game.pause()
      score = score + 1000

      // Iris-out effect then show level complete
      game.irisOut(function() {
        document.getElementById('final-score').textContent = score
        document.getElementById('level-complete').style.display = 'block'
      }, 45)
    </q:function>
  </qg:scene>
</q:application>
