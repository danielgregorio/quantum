<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 10: Complete Level - Sound + Goal + Polish

  Full Yoshi's Island 1 recreation with all systems:
  - Scene + background + collision map
  - Physics + gravity
  - Controls + animations
  - Camera follow with lerp
  - Coins + question blocks
  - Rex enemies with stomp mechanic
  - Full HUD (lives, coins, score)
  - Death + respawn + game over
  - Sound effects + background music
  - Goal sensor + level complete screen
-->
<q:application id="yoshi-island-1" type="game" engine="2d">
  <qg:scene name="main" width="5120" height="432" viewport-width="256" viewport-height="224" background="#5C94FC">
    <qg:physics gravity-y="1.5" />
    <qg:camera follow="mario" lerp="0.08" bounds="scene" offset-y="-80" />

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

    <!-- Full level background image -->
    <qg:sprite id="level-bg" src="assets/smw/sprites/yoshi-island-1.png"
               x="2560" y="216" width="5120" height="432" />

    <!-- Main ground collision -->
    <qg:sprite id="ground-main" width="5120" height="16" x="2560" y="392"
               tag="terrain" body="static" visible="false" />

    <!-- Collision data -->
    <qg:sprite id="block0" width="16" height="16" x="1912" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block1" width="16" height="16" x="1960" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block2" width="16" height="16" x="2120" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block3" width="32" height="16" x="2240" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block4" width="32" height="16" x="4560" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block5" width="16" height="16" x="4664" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block6" width="32" height="16" x="1824" y="344" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block7" width="16" height="16" x="1912" y="344" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block8" width="16" height="16" x="1960" y="344" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block9" width="32" height="16" x="2112" y="344" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block10" width="32" height="16" x="2240" y="344" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block11" width="32" height="16" x="4560" y="344" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block12" width="32" height="16" x="1824" y="360" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block13" width="16" height="16" x="1912" y="360" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block14" width="16" height="16" x="1960" y="360" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block15" width="32" height="16" x="2112" y="360" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block16" width="32" height="16" x="2240" y="360" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block17" width="32" height="16" x="4560" y="360" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block18" width="32" height="16" x="1824" y="376" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block19" width="16" height="16" x="1912" y="376" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block20" width="16" height="16" x="1960" y="376" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block21" width="32" height="16" x="2112" y="376" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block22" width="32" height="16" x="2240" y="376" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block23" width="32" height="16" x="4560" y="376" tag="terrain" body="static" visible="false" />

    <qg:sprite id="plat2" width="16" height="16" x="216" y="296" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat3" width="32" height="16" x="912" y="296" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat4" width="16" height="16" x="1240" y="296" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat5" width="16" height="16" x="1304" y="296" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat6" width="16" height="16" x="1368" y="296" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat7" width="32" height="16" x="2080" y="296" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat10" width="16" height="16" x="200" y="312" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat11" width="16" height="16" x="888" y="312" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat12" width="16" height="16" x="936" y="312" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat13" width="16" height="16" x="1224" y="312" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat14" width="16" height="16" x="1288" y="312" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat15" width="16" height="16" x="1352" y="312" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat19" width="16" height="16" x="184" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat20" width="16" height="16" x="872" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat21" width="16" height="16" x="1208" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat22" width="16" height="16" x="1272" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat23" width="16" height="16" x="1336" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat27" width="144" height="16" x="4376" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat28" width="16" height="16" x="856" y="344" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat32" width="16" height="16" x="840" y="360" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat35" width="16" height="16" x="824" y="376" tag="terrain" body="static" visible="false" />

    <!-- Question blocks -->
    <qg:instance prefab="qblock" id="qb1" x="496" y="256" />
    <qg:instance prefab="qblock" id="qb2" x="592" y="256" />
    <qg:instance prefab="qblock" id="qb3" x="1040" y="256" />
    <qg:instance prefab="qblock" id="qb4" x="3200" y="192" />
    <qg:instance prefab="qblock" id="qb5" x="3216" y="192" />
    <qg:instance prefab="qblock" id="qb6" x="3232" y="192" />
    <qg:instance prefab="qblock" id="qb7" x="3248" y="192" />

    <!-- Coins -->
    <qg:instance prefab="coin" x="160" y="288" />
    <qg:instance prefab="coin" x="528" y="224" />
    <qg:instance prefab="coin" x="560" y="224" />
    <qg:instance prefab="coin" x="1600" y="288" />
    <qg:instance prefab="coin" x="2656" y="176" />
    <qg:instance prefab="coin" x="2672" y="176" />
    <qg:instance prefab="coin" x="2688" y="176" />
    <qg:instance prefab="coin" x="2704" y="176" />
    <qg:instance prefab="coin" x="2720" y="176" />
    <qg:instance prefab="coin" x="3600" y="272" />
    <qg:instance prefab="coin" x="3616" y="272" />
    <qg:instance prefab="coin" x="4080" y="288" />
    <qg:instance prefab="coin" x="4096" y="288" />
    <qg:instance prefab="coin" x="4112" y="288" />

    <!-- Rex enemies -->
    <qg:instance prefab="rex" id="rex1" x="450" y="350" />
    <qg:instance prefab="rex" id="rex2" x="700" y="350" />
    <qg:instance prefab="rex" id="rex3" x="950" y="350" />
    <qg:instance prefab="rex" id="rex4" x="1300" y="350" />
    <qg:instance prefab="rex" id="rex5" x="1600" y="350" />
    <qg:instance prefab="rex" id="rex6" x="1900" y="350" />
    <qg:instance prefab="rex" id="rex7" x="2200" y="350" />
    <qg:instance prefab="rex" id="rex8" x="2700" y="350" />
    <qg:instance prefab="rex" id="rex9" x="3100" y="350" />
    <qg:instance prefab="rex" id="rex10" x="3500" y="350" />
    <qg:instance prefab="rex" id="rex11" x="3900" y="350" />
    <qg:instance prefab="rex" id="rex12" x="4300" y="350" />

    <!-- Goal at the end -->
    <qg:sprite id="goal" width="16" height="80" x="4950" y="344"
               color="#00FF00" tag="goal" body="static" sensor="true" />

    <!-- Death zone at bottom -->
    <qg:sprite id="deathzone" width="5120" height="16" x="2560" y="480"
               tag="death" body="static" sensor="true" visible="false" />

    <!-- Mario -->
    <qg:sprite id="mario" src="assets/smw/sprites/mario_small.png"
               x="80" y="350" tag="player"
               frame-width="16" frame-height="24"
               body="dynamic" controls="arrows" speed="1.5" jump-force="5.3" friction="0.15">
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

    <!-- Events -->
    <qg:event name="coin-collected" handler="onCoinCollected" />
    <qg:event name="block-hit" handler="onBlockHit" />
    <qg:event name="enemy-collision" handler="onEnemyCollision" />
    <qg:event name="enemy-stomped" handler="onEnemyStomped" />
    <qg:event name="fell-in-pit" handler="onFellInPit" />
    <qg:event name="death-animation-complete" handler="onDeathAnimationComplete" />
    <qg:event name="level-complete" handler="onLevelComplete" />
    <qg:event name="game-init" handler="onGameInit" />

    <q:function name="onGameInit">
      game.irisIn(null, 45)

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

      game.setRexAI('rex1', -0.5)
      game.setRexAI('rex2', -0.5)
      game.setRexAI('rex3', -0.5)
      game.setRexAI('rex4', -0.5)
      game.setRexAI('rex5', -0.5)
      game.setRexAI('rex6', -0.5)
      game.setRexAI('rex7', -0.5)
      game.setRexAI('rex8', -0.5)
      game.setRexAI('rex9', -0.5)
      game.setRexAI('rex10', -0.5)
      game.setRexAI('rex11', -0.5)
      game.setRexAI('rex12', -0.5)

      // Handle music autoplay
      const startMusic = () => {
        game.playSound('bgm-level', { loop: true, volume: 0.5 })
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

    <q:function name="onEnemyStomped">
      // Sound handled by event trigger
    </q:function>

    <q:function name="onBlockHit">
      if (!data || !data.other) return
      if (data.other._blockUsed) return

      const block = data.other
      game.hitBlock(block, 'assets/smw/sprites/qblock_used.png', 'assets/smw/sprites/coin_animated.png', 16, 16)
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

      // Cooldown: skip if this enemy was just stomped (prevents multi-fire killing Mario)
      const now = Date.now()
      if (enemy._lastStompTime &amp;&amp; now - enemy._lastStompTime &lt; 500) return

      const marioBottom = mario.body.position.y + 12
      const enemyTop = enemy.body.position.y - (enemy._rexSquished ? 6 : 12)

      // Stomp: Mario's feet above enemy's head (generous 10px window)
      if (marioBottom &lt; enemyTop + 10) {
        enemy._lastStompTime = now
        _gameEvents.emit('enemy-stomped', { enemy: enemy.id })
        if (enemy._rexSquished) {
          game.destroySprite(enemy.id)
          score = score + 200
        } else {
          enemy._rexSquished = true
          enemy.sprite.scale.y = 0.5
          enemy._rexSpeed = (enemy._rexSpeed || 0.4) * 1.5
          score = score + 100
        }
        Matter.Body.setVelocity(mario.body, { x: mario.body.velocity.x, y: -6 })
        document.getElementById('score-display').textContent = score
      } else {
        isDead = 1
        lives = lives - 1
        document.getElementById('lives-display').textContent = lives
        if (typeof _audioCtx !== 'undefined' &amp;&amp; _audioCtx.state === 'running') {
          _audioCtx.suspend()
        }
        game.stopAllSounds()
        setTimeout(() => {
          if (typeof _audioCtx !== 'undefined') {
            _audioCtx.resume().then(() => {
              _gameEvents.emit('mario-died', {})
            })
          } else {
            _gameEvents.emit('mario-died', {})
          }
        }, 50)
        game.killPlayer('mario')
      }
    </q:function>

    <q:function name="onFellInPit">
      if (isDead) return
      isDead = 1
      lives = lives - 1
      document.getElementById('lives-display').textContent = lives
      if (typeof _audioCtx !== 'undefined' &amp;&amp; _audioCtx.state === 'running') {
        _audioCtx.suspend()
      }
      game.stopAllSounds()
      setTimeout(() => {
        if (typeof _audioCtx !== 'undefined') {
          _audioCtx.resume().then(() => {
            _gameEvents.emit('mario-died', {})
          })
        } else {
          _gameEvents.emit('mario-died', {})
        }
      }, 50)
      game.killPlayer('mario')
    </q:function>

    <q:function name="onDeathAnimationComplete">
      setTimeout(function() {
        game.irisOut(function() {
          if (lives &lt;= 0) {
            document.getElementById('gameover-score').textContent = score
            document.getElementById('game-over').style.display = 'block'
          } else {
            sessionStorage.setItem('mario_lives', lives)
            sessionStorage.setItem('mario_score', score)
            location.reload()
          }
        }, 30)
      }, 3000)
    </q:function>

    <q:function name="onLevelComplete">
      game.stopSound('bgm-level')
      game.pause()
      score = score + 1000

      game.irisOut(function() {
        document.getElementById('final-score').textContent = score
        document.getElementById('level-complete').style.display = 'block'
      }, 45)
    </q:function>

  </qg:scene>
</q:application>
