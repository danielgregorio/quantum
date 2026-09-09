<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 18: Yoshi's Island 1 (Full Level)

  Recreation of the first level from SMW with:
  - Full level image as background (5120x432 pixels)
  - Rex enemies (purple dinosaurs)
  - Camera scrolling
  - Stomp mechanic (2 hits to kill Rex)

  Level: 320 tiles wide (5120 pixels)
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
    <q:set name="time_left" value="300" type="number" />
    <q:set name="yoshi_coins" value="0" type="number" />

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
    <qg:sound id="sfx-powerup" src="assets/smw/sounds/smw_power-up.wav" trigger="powerup-collected" />

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

    <qg:prefab name="rotating_block" breakable="true">
      <qg:sprite src="assets/smw/sprites/rotating_block.png"
                 width="16" height="16"
                 tag="rotating_block" body="static" />
    </qg:prefab>

    <qg:prefab name="coin">
      <qg:sprite src="assets/smw/sprites/coin_animated.png"
                 frame-width="16" frame-height="16"
                 tag="coin" body="static" sensor="true">
        <qg:animation name="spin" frames="0,1,2,3,2,1" speed="0.12" loop="true" auto-play="true" />
      </qg:sprite>
    </qg:prefab>

    <!-- Yoshi coins removed - spritesheet issue -->

    <qg:prefab name="rex">
      <qg:sprite src="assets/smw/sprites/rex_walk.png"
                 frame-width="12" frame-height="24"
                 tag="enemy" body="dynamic" friction="0">
        <qg:animation name="walk" frames="0-1" speed="0.15" loop="true" auto-play="true" />
      </qg:sprite>
    </qg:prefab>

    <qg:prefab name="mushroom">
      <qg:sprite src="assets/smw/sprites/mushroom.png"
                 width="16" height="16"
                 tag="powerup" body="dynamic" bounce="0" friction="0.1">
      </qg:sprite>
    </qg:prefab>

    <!-- Banzai Bill: giant bullet, charge AI (horizontal flight, no gravity) -->
    <qg:prefab name="banzai_bill">
      <qg:sprite src="assets/smw/sprites/banzai_bill.png"
                 width="64" height="64" tag="enemy" body="dynamic"
                 collision-layer="2" collision-mask="1" />
    </qg:prefab>

    <!-- Piranha Plant: emerges from pipes on timer -->
    <qg:prefab name="piranha_plant">
      <qg:sprite src="assets/smw/sprites/piranha_plant.png"
                 frame-width="16" frame-height="16"
                 tag="hazard" body="static" sensor="true"
                 collision-layer="2" collision-mask="1">
        <qg:animation name="chomp" frames="0-1" speed="0.2" loop="true" auto-play="true" />
      </qg:sprite>
    </qg:prefab>

    <!-- Flying Qblock: oscillates horizontally, drops mushroom when hit -->
    <qg:prefab name="flying_qblock" flying="true" content="mushroom" hits="1">
      <qg:sprite src="assets/smw/sprites/qblock_animated.png"
                 frame-width="16" frame-height="16"
                 tag="qblock" body="static">
        <qg:animation name="shine" frames="0,1,2,3" speed="0.15" loop="true" auto-play="true" />
      </qg:sprite>
    </qg:prefab>

    <!-- Enemy behaviors (AI + defeat) -->
    <qg:enemy prefab="rex">
      <qg:ai type="patrol" speed="30" turn-cooldown="0.15" turn-on-edge="true" facing="left" />
      <qg:defeat by="stomp" health="2" bounce="-200">
        <qg:on-hit score="100" effect="squish" speed-multiply="1.5" />
        <qg:on-kill score="200" effect="puff" />
      </qg:defeat>
    </qg:enemy>

    <qg:enemy prefab="banzai_bill">
      <qg:ai type="charge" speed="90" facing="left" />
      <qg:defeat by="stomp" health="1" bounce="-250">
        <qg:on-kill score="400" effect="puff" />
      </qg:defeat>
    </qg:enemy>

    <qg:enemy prefab="piranha_plant">
      <qg:ai type="emerge" speed="1.5" />
      <qg:defeat by="fire" health="1">
        <qg:on-kill score="100" effect="puff" />
      </qg:defeat>
    </qg:enemy>

    <!-- Full level background image -->
    <qg:sprite id="level-bg" src="assets/smw/sprites/yoshi-island-1.png"
               x="2560" y="216" width="5120" height="432" />

    <!-- Main ground collision (full level width) - platform style -->
    <qg:sprite id="ground-main" width="5120" height="16" x="2560" y="392"
               tag="terrain" body="static" visible="false" />

    <!-- Collision data exported from collision editor -->
    <!-- Blocks (solid collision) -->
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

    <!-- SLOPES are handled via custom JavaScript in onGameInit -->
    <!-- No physics bodies - just Y position adjustment based on Mario's X -->

    <!-- Other platforms (non-slope terrain) -->
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

    <!-- Question blocks (matching image positions) -->
    <!-- qb1 contains mushroom power-up -->
    <qg:instance prefab="qblock" id="qb1" x="496" y="256" data-content="mushroom" />
    <qg:instance prefab="qblock" id="qb2" x="592" y="256" />
    <qg:instance prefab="qblock" id="qb3" x="1040" y="256" />
    <qg:instance prefab="qblock" id="qb4" x="3200" y="192" />
    <!-- Pipe-blocking blocks: rotating_block (breakable) instead of qblock -->
    <qg:instance prefab="rotating_block" id="rb16" x="3216" y="192" />
    <qg:instance prefab="rotating_block" id="rb17" x="3232" y="192" />
    <qg:instance prefab="rotating_block" id="rb18" x="3248" y="192" />

    <!-- Coins (matching image - floating coins) -->
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

    <!-- Rex enemies - spawn above ground, will fall and land -->
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

    <!-- Banzai Bills - charge from right side of screen -->
    <qg:instance prefab="banzai_bill" id="bb1" x="2000" y="280" />
    <qg:instance prefab="banzai_bill" id="bb2" x="3400" y="300" />

    <!-- Piranha Plants - emerge from pipes -->
    <qg:instance prefab="piranha_plant" id="pp1" x="3408" y="376" />
    <qg:instance prefab="piranha_plant" id="pp2" x="3648" y="376" />

    <!-- Flying Qblock - oscillates, drops mushroom -->
    <qg:instance prefab="flying_qblock" id="fqb1" x="1200" y="200" data-content="mushroom" />

    <!-- Goal at the end (visible in image around x=4900) -->
    <qg:sprite id="goal" width="16" height="80" x="4950" y="344"
               color="#00FF00" tag="goal" body="static" sensor="true" />

    <!-- Mario - spawn above ground, will fall and land -->
    <qg:sprite id="mario" src="assets/smw/sprites/mario_small.png"
               x="80" y="350" tag="player"
               frame-width="16" frame-height="24"
               body="dynamic" controls="arrows" speed="1.5" jump-force="5.3" friction="0.15"
               spin-jump="true">
      <qg:animation name="idle" frames="0" speed="0.1" loop="true" auto-play="true" />
      <qg:animation name="walk" frames="1-3" speed="0.18" loop="true" />
      <qg:animation name="jump" frames="4" speed="0.1" loop="false" />
      <qg:on-collision with-tag="coin" action="emit:coin-collected" />
      <qg:on-collision with-tag="coin" action="destroy-other" />
      <qg:on-collision with-tag="qblock" action="emit:block-hit" />
      <qg:on-collision with-tag="enemy" action="emit:enemy-collision" />
      <qg:on-collision with-tag="death" action="emit:fell-in-pit" />
      <qg:on-collision with-tag="goal" action="emit:level-complete" />
      <qg:on-collision with-tag="powerup" action="emit:powerup-collected" />
      <qg:on-collision with-tag="powerup" action="destroy-other" />
    </qg:sprite>

    <!-- HUD (Tile-based SNES-style, documented SMW positions from VRAM $5000 mapping)
         VRAM row 2 ($5042) = y=8: MARIO(col2), CoinIcon(col8), TIME(col19)
         VRAM row 3 ($5063) = y=16: ×Lives(col3), DragonCoins(col8-12), Timer(col19), Score(col22-28)
         Item box: tilemap rows 1+4 (cols14-17) = sprite at x=112, y=0
         User custom: coins moved to right-edge=232 y=8 (above score) -->
    <qg:hud sprite-prefix="assets/smw/sprites/hud_">
      <!-- Item Box sprite: cols 14-17, rows 1-4, x=112 y=0 -->
      <qg:tile sprite="item_box.png" x="112" y="0" />

      <!-- Upper row (y=8): MARIO col2, TIME col19, Coins right-aligned above score -->
      <qg:tile sprite="mario_text.png" x="16" y="8" />
      <qg:tile sprite="time_text.png" x="152" y="8" />
      <qg:counter strip="numbers_small.png" align="right" right-edge="232" y="8"
                  icon="coin_icon.png" symbol="x_symbol.png"
                  bind="{coins}" tint="yellow" intelligent="true" extra-life-at="100" />

      <!-- Lower row (y=16): ×Lives col3, DragonCoins col8, Timer col19, Score col22 -->
      <qg:tile sprite="x_symbol.png" x="24" y="16" />
      <qg:counter strip="numbers_small.png" x="32" y="16" bind="{lives}" tint="yellow" intelligent="true" />
      <qg:collection sprite="coin_icon.png" x="64" y="16" spacing="8" max="5" bind="{yoshi_coins}" />
      <qg:counter strip="numbers_small.png" x="152" y="16" digits="3" bind="{time_left}"
                  countdown="true" hurry-at="100" flash="red" tint="yellow" />
      <qg:counter strip="numbers_small.png" align="right" right-edge="232" y="16"
                  bind="{score}" tint="yellow" intelligent="true" />

      <!-- Behaviors -->
      <qg:hud-behavior target="time_left" event="reach" value="100">
        <qg:action type="emit" event="time-hurry" />
      </qg:hud-behavior>
      <qg:hud-behavior target="time_left" event="reach" value="0">
        <qg:action type="emit" event="time-up" />
      </qg:hud-behavior>
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
    <qg:sprite id="deathzone" width="5120" height="16" x="2560" y="480"
               tag="death" body="static" sensor="true" visible="false" />

    <!-- Events -->
    <qg:event name="coin-collected" handler="onCoinCollected" />
    <qg:event name="block-hit" handler="onBlockHit" />
    <qg:event name="enemy-collision" handler="onEnemyCollision" />
    <qg:event name="fell-in-pit" handler="onFellInPit" />
    <qg:event name="death-animation-complete" handler="onDeathAnimationComplete" />
    <qg:event name="level-complete" handler="onLevelComplete" />
    <qg:event name="powerup-collected" handler="onPowerupCollected" />
    <qg:event name="game-init" handler="onGameInit" />

    <q:function name="onGameInit">
      console.log('=== onGameInit CALLED ===')

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

      // ============================================
      // SNES-STYLE SLOPE SYSTEM
      // Adjusts Mario's Y position based on slope data
      // ============================================
      const GROUND_Y = 380  // Base ground level (Mario's feet)
      const MARIO_HEIGHT = 24

      // Define slope zones: { x1, y1, x2, y2 } - line from point 1 to point 2
      // y values are where Mario's FEET should be (body center = y - 12)
      // WAITING FOR CORRECT COORDINATES FROM USER
      const slopes = [
        // User needs to provide X coordinates:
        // - Stand at BASE of diagonal pipe, tell me X
        // - Stand at TOP of diagonal pipe, tell me X
      ]

      // Function to get slope Y at given X position
      function getSlopeY(x) {
        for (const slope of slopes) {
          if (x >= slope.x1 &amp;&amp; x &lt;= slope.x2) {
            // Linear interpolation
            const t = (x - slope.x1) / (slope.x2 - slope.x1)
            return slope.y1 + t * (slope.y2 - slope.y1)
          }
        }
        return null // Not on a slope
      }

      // Slope handling - runs every frame
      console.log('=== Setting up slope ticker ===')
      let _slopeDebugTimer = 0
      app.ticker.add(() => {
        const mario = _sprites['mario']
        if (!mario || !mario.body || isDead) return

        const marioX = mario.body.position.x
        const marioY = mario.body.position.y
        const marioVelY = mario.body.velocity.y

        // Debug output every 60 frames
        _slopeDebugTimer++
        if (_slopeDebugTimer % 60 === 0) {
          console.log('Mario X:', marioX.toFixed(0), 'Y:', marioY.toFixed(0))
        }

        // Check if Mario is on a slope
        const slopeY = getSlopeY(marioX)

        if (slopeY !== null) {
          // Mario is in a slope zone
          const targetY = slopeY - MARIO_HEIGHT / 2  // Body center

          if (_slopeDebugTimer % 30 === 0) {
            console.log('ON SLOPE! Target Y:', targetY.toFixed(0), 'Current Y:', marioY.toFixed(0))
          }

          // Only apply slope if Mario is falling or at/below slope level
          if (marioY >= targetY - 10) {
            // Snap to slope surface
            Matter.Body.setPosition(mario.body, {
              x: marioX,
              y: targetY
            })
            // Cancel downward velocity
            if (marioVelY > 0) {
              Matter.Body.setVelocity(mario.body, {
                x: mario.body.velocity.x,
                y: 0
              })
            }
          }
        }
      })

      // Setup Rex AI - all walk left
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

    <q:function name="onPowerupCollected">
      // Sound effect plays via event trigger
      console.log('POWER UP!')
    </q:function>

    <q:function name="onBlockHit">
      if (!data || !data.other) return
      if (data.other._blockUsed) return

      const block = data.other
      const blockId = block.id

      // Check if this block contains a mushroom (qb1)
      if (blockId === 'qb1') {
        // Mushroom block - show mushroom popping out and give power-up directly
        game.hitBlock(block, 'assets/smw/sprites/qblock_used.png', 'assets/smw/sprites/mushroom.png', 16, 16)
        // Give power-up directly (no physical mushroom for now)
        score = score + 1000
        document.getElementById('score-display').textContent = score
        _gameEvents.emit('powerup-collected', {})
        console.log('MUSHROOM! +1000 points')
      } else {
        // Normal coin block
        game.hitBlock(block, 'assets/smw/sprites/qblock_used.png', 'assets/smw/sprites/coin_animated.png', 16, 16)
        coins = coins + 1
        score = score + 10
        document.getElementById('coin-display').textContent = coins
        document.getElementById('score-display').textContent = score
      }
    </q:function>

    <q:function name="onEnemyCollision">
      if (!data || !data.other) return
      if (isDead) return
      const mario = _sprites['mario']
      const enemy = data.other
      if (!mario || !enemy || !mario.body || !enemy.body) return

      // Rex is 12x24 (squished: 12x12), Mario is 16x24
      // Body positions are at center
      const marioFeet = mario.body.position.y + 12
      const rexHeight = enemy._rexSquished ? 6 : 12
      const rexHead = enemy.body.position.y - rexHeight
      const marioVelY = mario.body.velocity.y

      // GENEROUS stomp detection like in SMW:
      // - Mario just needs to be falling (any downward velocity)
      // - Mario's feet can be up to 8px below Rex's head (forgiving)
      const isAbove = marioFeet &lt; rexHead + 8
      const isFalling = marioVelY > 0

      // Debug stomp detection
      console.log('Collision! MarioFeet:', marioFeet.toFixed(0), 'RexHead:', rexHead.toFixed(0), 'VelY:', marioVelY.toFixed(2), 'isAbove:', isAbove, 'isFalling:', isFalling)

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
        // Stop ALL sounds - suspend entire audio context
        if (typeof _audioCtx !== 'undefined' &amp;&amp; _audioCtx.state === 'running') {
          _audioCtx.suspend()
        }
        game.stopAllSounds()
        // Resume audio context for death sound, then play it
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
      // Stop ALL sounds - suspend entire audio context
      if (typeof _audioCtx !== 'undefined' &amp;&amp; _audioCtx.state === 'running') {
        _audioCtx.suspend()
      }
      game.stopAllSounds()
      // Resume audio context for death sound, then play it
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
      // Wait for death sound to finish (approximately 3.5 seconds)
      // Then do iris-out and respawn
      setTimeout(function() {
        game.irisOut(function() {
          if (lives &lt;= 0) {
            // Game Over
            document.getElementById('gameover-score').textContent = score
            document.getElementById('game-over').style.display = 'block'
          } else {
            // Reload entire level
            sessionStorage.setItem('mario_lives', lives)
            sessionStorage.setItem('mario_score', score)
            location.reload()
          }
        }, 30)
      }, 3000)  // 3 seconds delay for death sound
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
