<q:application id="smw-yoshis-island" type="game" engine="2d">

  <!-- ============================================================
       SUPER MARIO WORLD - YOSHI'S ISLAND 1
       Componentized version using imports for behaviors and prefabs
       ============================================================ -->

  <!-- ==================== IMPORTS ==================== -->

  <!-- Behaviors -->
  <q:import behavior="PlayerBehavior" from="./behaviors" />
  <q:import behavior="PatrolBehavior" from="./behaviors" />
  <q:import behavior="RexBehavior" from="./behaviors" />
  <q:import behavior="QuestionBlockBehavior" from="./behaviors" />
  <q:import behavior="PiranhaBehavior" from="./behaviors" />

  <!-- Prefabs -->
  <q:import prefab="Coin" from="./prefabs" />
  <q:import prefab="DragonCoin" from="./prefabs" />
  <q:import prefab="KoopaGreen" from="./prefabs" />
  <q:import prefab="KoopaRed" from="./prefabs" />
  <q:import prefab="Rex" from="./prefabs" />
  <q:import prefab="QuestionBlock" from="./prefabs" />
  <q:import prefab="GoalPost" from="./prefabs" />

  <!-- ==================== SCENE ==================== -->

  <qg:scene name="yoshis_island_1" width="3200" height="432" background="#5CA0FF">

    <!-- Physics Setup -->
    <qg:physics gravity-y="20" bounds="none" />
    <qg:camera follow="mario" lerp="0.08" bounds="scene" offset-y="-50" />

    <!-- Game State -->
    <q:set name="score" value="0" type="integer" />
    <q:set name="coins" value="0" type="integer" />
    <q:set name="lives" value="5" type="integer" />
    <q:set name="dragonCoins" value="0" type="integer" />
    <q:set name="levelComplete" value="false" type="boolean" />
    <q:set name="gameOver" value="false" type="boolean" />

    <!-- Event Handlers -->
    <q:function name="onCoinCollected">
      coins++;
      score += arguments[0].points || 200;
      if (coins >= 100) {
        coins -= 100;
        lives++;
        game.play('oneup_sfx');
      }
      _updateHUD();
    </q:function>

    <q:function name="onEnemyKilled">
      score += arguments[0].points || 100;
      _updateHUD();
    </q:function>

    <q:function name="onPlayerHit">
      lives--;
      if (lives &lt;= 0) {
        gameOver = true;
        game.play('lost_life_sfx');
      } else {
        game.play('lost_life_sfx');
        game.respawn('mario', 40, 350);
      }
      _updateHUD();
    </q:function>

    <q:function name="onPlayerDied">
      lives--;
      if (lives &lt;= 0) {
        gameOver = true;
      } else {
        game.respawn('mario', 40, 350);
      }
      game.play('lost_life_sfx');
      _updateHUD();
    </q:function>

    <q:function name="onLevelComplete">
      game.stop('bgm');
      game.play('course_clear_sfx');
      score += 1000;
      _updateHUD();
    </q:function>

    <!-- Register Events using qg:event -->
    <qg:event name="coinCollected" handler="onCoinCollected" />
    <qg:event name="enemyKilled" handler="onEnemyKilled" />
    <qg:event name="playerHit" handler="onPlayerHit" />
    <qg:event name="playerDied" handler="onPlayerDied" />
    <qg:event name="levelComplete" handler="onLevelComplete" />

    <!-- ==================== TILEMAP ==================== -->

    <qg:tilemap id="level" src="../assets/smw/sprites/tileset_yi1_clean.png"
                tile-width="16" tile-height="16">

      <!-- Background Layer (hills, bushes - no collision) -->
      <qg:layer name="background" collision="false">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,40,41,42,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,40,41,42,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,40,41,42,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
      </qg:layer>

      <!-- Terrain Layer (ground with collision) -->
      <qg:layer name="terrain" collision="true">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,4
6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6
      </qg:layer>
    </qg:tilemap>

    <!-- ==================== PLAYER ==================== -->

    <qg:sprite id="mario" src="../assets/smw/sprites/mario.png"
               x="40" y="350" width="16" height="32"
               frame-width="16" frame-height="32"
               body="dynamic" controls="arrows" speed="5" jump-force="15"
               bounce="0" friction="0.8" tag="player">
      <qg:animation name="idle" frames="0" speed="0.1" loop="true" auto-play="true" />
      <qg:animation name="walk" frames="1-2" speed="0.12" loop="true" />
      <qg:animation name="run" frames="1-2" speed="0.08" loop="true" />
      <qg:animation name="jump" frames="3" speed="0.1" loop="false" />

      <qg:use behavior="PlayerBehavior"
             on-collision="onEnemyCollision" collision-tag="enemy" />
      <qg:use behavior="PlayerBehavior"
             on-collision="onCoinCollision" collision-tag="coin" />
      <qg:use behavior="PlayerBehavior"
             on-collision="onCoinCollision" collision-tag="dragoncoin" />
      <qg:use behavior="PlayerBehavior"
             on-collision="onPowerupCollision" collision-tag="powerup" />
      <qg:use behavior="PlayerBehavior"
             on-collision="onGoalCollision" collision-tag="goal" />
      <qg:use behavior="PlayerBehavior"
             on-collision="onDeathZone" collision-tag="deathzone" />
    </qg:sprite>

    <!-- ==================== ENEMIES ==================== -->

    <qg:group name="enemies">
      <qg:instance prefab="KoopaGreen" x="320" y="380" />
      <qg:instance prefab="KoopaGreen" x="560" y="380" />
      <qg:instance prefab="KoopaRed" x="800" y="380" />
      <qg:instance prefab="Rex" x="1100" y="370" />
      <qg:instance prefab="KoopaGreen" x="1400" y="380" />
      <qg:instance prefab="Rex" x="1700" y="370" />
    </qg:group>

    <!-- ==================== COLLECTIBLES ==================== -->

    <qg:group name="coins">
      <qg:instance prefab="Coin" x="160" y="360" />
      <qg:instance prefab="Coin" x="176" y="360" />
      <qg:instance prefab="Coin" x="192" y="360" />
      <qg:instance prefab="Coin" x="400" y="340" />
      <qg:instance prefab="Coin" x="416" y="340" />
      <qg:instance prefab="Coin" x="640" y="360" />
      <qg:instance prefab="Coin" x="656" y="360" />
      <qg:instance prefab="Coin" x="672" y="360" />
    </qg:group>

    <qg:group name="dragoncoins">
      <qg:instance prefab="DragonCoin" x="300" y="350" />
      <qg:instance prefab="DragonCoin" x="900" y="320" />
      <qg:instance prefab="DragonCoin" x="1500" y="350" />
      <qg:instance prefab="DragonCoin" x="2000" y="330" />
      <qg:instance prefab="DragonCoin" x="2500" y="350" />
    </qg:group>

    <!-- ==================== QUESTION BLOCKS ==================== -->

    <qg:group name="qblocks">
      <qg:instance prefab="QuestionBlock" x="480" y="320" />
      <qg:instance prefab="QuestionBlock" x="720" y="320" />
      <qg:instance prefab="QuestionBlock" x="1200" y="280" />
    </qg:group>

    <!-- ==================== GOAL ==================== -->

    <qg:instance prefab="GoalPost" x="3100" y="300" />

    <!-- ==================== DEATH ZONE ==================== -->

    <qg:sprite id="deathzone" src=""
               x="1600" y="450" width="3200" height="32"
               body="static" sensor="true" tag="deathzone"
               visible="false" color="#000000" />

    <!-- ==================== SOUNDS ==================== -->

    <qg:sound id="bgm" src="../assets/smw/sounds/smw_course_clear.wav"
              channel="music" loop="true" trigger="scene.start" volume="0.3" />
    <qg:sound id="jump_sfx" src="../assets/smw/sounds/smw_jump.wav"
              channel="sfx" trigger="player.jump" />
    <qg:sound id="coin_sfx" src="../assets/smw/sounds/smw_coin.wav" channel="sfx" />
    <qg:sound id="stomp_sfx" src="../assets/smw/sounds/smw_stomp.wav" channel="sfx" />
    <qg:sound id="powerup_sfx" src="../assets/smw/sounds/smw_power-up.wav" channel="sfx" />
    <qg:sound id="oneup_sfx" src="../assets/smw/sounds/smw_1-up.wav" channel="sfx" />
    <qg:sound id="kick_sfx" src="../assets/smw/sounds/smw_kick.wav" channel="sfx" />
    <qg:sound id="lost_life_sfx" src="../assets/smw/sounds/smw_lost_a_life.wav" channel="sfx" />
    <qg:sound id="course_clear_sfx" src="../assets/smw/sounds/smw_course_clear.wav" channel="music" />

    <!-- ==================== HUD ==================== -->

    <qg:hud position="top-left">
      <div style="padding:8px; font-family:'Press Start 2P', monospace; font-size:12px;">
        <span style="color:#fff;">MARIO</span>
        <br/>
        <span style="color:#fff;">{String(score).padStart(7, '0')}</span>
      </div>
    </qg:hud>

    <qg:hud position="top-center">
      <div style="padding:8px; font-family:'Press Start 2P', monospace; font-size:12px; text-align:center;">
        <span style="color:#ffd700;">x{String(coins).padStart(2, '0')}</span>
      </div>
    </qg:hud>

    <qg:hud position="top-right">
      <div style="padding:8px; font-family:'Press Start 2P', monospace; font-size:12px; text-align:right;">
        <span style="color:#fff;">WORLD</span>
        <br/>
        <span style="color:#fff;">1-1</span>
        <span style="color:#f44;">  x{lives}</span>
      </div>
    </qg:hud>

    <qg:hud position="center">
      <div style="font-family:'Press Start 2P', monospace; font-size:24px; text-align:center;">
        <span style="color:#fff; text-shadow:3px 3px #000;">
          {gameOver ? 'GAME OVER' : (levelComplete ? 'COURSE CLEAR!' : '')}
        </span>
      </div>
    </qg:hud>

    <!-- ==================== CONTROLS ==================== -->

    <q:function name="restart">
      <q:set name="score" value="0" />
      <q:set name="coins" value="0" />
      <q:set name="lives" value="5" />
      <q:set name="dragonCoins" value="0" />
      <q:set name="levelComplete" value="false" />
      <q:set name="gameOver" value="false" />
      game.respawn('mario', 40, 350);
      _updateHUD();
    </q:function>

    <qg:input key="r" action="restart" type="press" />
    <qg:input key="R" action="restart" type="press" />

  </qg:scene>

</q:application>
