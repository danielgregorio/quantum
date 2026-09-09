<q:application id="smw-yoshis-island" type="game" engine="2d">

  <!-- ============================================================
       SUPER MARIO WORLD - YOSHI'S ISLAND 1
       Polished example demonstrating Quantum game engine features:
       - Prefabs for reusable game objects
       - Modular behaviors with state machines
       - Tilemap-based level design
       - Organized asset management
       ============================================================ -->

  <!-- ==================== BEHAVIORS ==================== -->

  <!-- Mario Player Behavior -->
  <qg:behavior name="PlayerBehavior">
    <q:set name="canJump" value="true" type="boolean" />
    <q:set name="isGrounded" value="false" type="boolean" />
    <q:set name="facingRight" value="true" type="boolean" />

    <q:function name="onEnemyCollision">
      var mario = this.owner;
      var enemy = this._other;
      if (!mario.body || !enemy.body) return;

      var marioBottom = mario.body.position.y + 16;
      var enemyTop = enemy.body.position.y - 8;
      var fallingDown = mario.body.velocity.y > 0;

      if (marioBottom &lt; enemyTop + 8 &amp;&amp; fallingDown) {
        // Stomp enemy
        Matter.Body.setVelocity(mario.body, {x: mario.body.velocity.x, y: -8});
        game.play('stomp_sfx');
        game.emit('enemyKilled', { enemy: enemy, points: 100 });
        game.destroy(enemy);
      } else {
        // Take damage
        game.emit('playerHit');
      }
    </q:function>

    <q:function name="onCoinCollision">
      var coin = this._other;
      game.play('coin_sfx');
      game.emit('coinCollected', { points: 200 });
      game.destroy(coin);
    </q:function>

    <q:function name="onPowerupCollision">
      var powerup = this._other;
      game.play('powerup_sfx');
      game.emit('powerupCollected', { type: powerup.powerupType || 'mushroom' });
      game.destroy(powerup);
    </q:function>

    <q:function name="onGoalCollision">
      if (!game.getVar('levelComplete')) {
        game.setVar('levelComplete', true);
        game.play('course_clear_sfx');
        game.emit('levelComplete');
      }
    </q:function>

    <q:function name="onDeathZone">
      game.emit('playerDied');
    </q:function>
  </qg:behavior>

  <!-- Basic Patrol Enemy Behavior -->
  <qg:behavior name="PatrolBehavior">
    <q:set name="direction" value="-1" type="integer" />
    <q:set name="speed" value="1.0" type="float" />
    <q:set name="patrolRange" value="100" type="integer" />
    <q:set name="startX" value="0" type="float" />

    <q:function name="onSpawn">
      this.startX = this.owner.sprite.x;
    </q:function>

    <q:function name="update">
      var body = this.owner.body;
      if (!body) return;

      // Move in patrol direction
      Matter.Body.setVelocity(body, {
        x: this.direction * this.speed,
        y: body.velocity.y
      });

      // Flip sprite based on direction
      this.owner.sprite.scale.x = this.direction > 0 ? -1 : 1;
    </q:function>

    <q:function name="onWallHit">
      this.direction *= -1;
    </q:function>

    <q:function name="onEdgeDetected">
      this.direction *= -1;
    </q:function>
  </qg:behavior>

  <!-- Rex Enemy Behavior (2-hit enemy) -->
  <qg:behavior name="RexBehavior">
    <q:set name="hitCount" value="0" type="integer" />
    <q:set name="isSquashed" value="false" type="boolean" />

    <qg:state-machine initial="walking">
      <qg:state name="walking">
        <qg:on event="stomp" transition="squashed" />
        <q:function name="update">
          var body = this.owner.body;
          if (body) {
            Matter.Body.setVelocity(body, { x: -1, y: body.velocity.y });
          }
        </q:function>
      </qg:state>

      <qg:state name="squashed">
        <qg:on event="stomp" transition="dead" />
        <q:function name="enter">
          this.isSquashed = true;
          this.owner.sprite.height = 16; // Squash sprite
          game.play('stomp_sfx');
        </q:function>
        <q:function name="update">
          var body = this.owner.body;
          if (body) {
            Matter.Body.setVelocity(body, { x: -1.5, y: body.velocity.y });
          }
        </q:function>
      </qg:state>

      <qg:state name="dead">
        <q:function name="enter">
          game.emit('enemyKilled', { points: 200 });
          game.destroy(this.owner);
        </q:function>
      </qg:state>
    </qg:state-machine>
  </qg:behavior>

  <!-- Question Block Behavior -->
  <qg:behavior name="QuestionBlockBehavior">
    <q:set name="active" value="true" type="boolean" />
    <q:set name="contents" value="coin" type="string" />

    <q:function name="onHitFromBelow">
      if (!this.active) return;

      var player = this._other;
      if (!player || !player.body) return;

      // Check if hit from below
      var playerTop = player.body.position.y - 16;
      var blockBottom = this.owner.body.position.y + 8;

      if (playerTop > blockBottom - 8) {
        this.active = false;
        this.owner.sprite.texture = game.getTexture('used_block');

        // Spawn contents
        if (this.contents === 'coin') {
          game.play('coin_sfx');
          game.emit('coinCollected', { points: 200 });
        } else {
          game.spawn('powerupSpawner', this.owner.sprite.x, this.owner.sprite.y - 20);
        }

        // Bounce animation
        game.tween(this.owner.sprite, { y: this.owner.sprite.y - 8 }, 0.1, 'easeOut');
        game.tween(this.owner.sprite, { y: this.owner.sprite.y }, 0.1, 'easeIn', 0.1);
      }
    </q:function>
  </qg:behavior>

  <!-- Piranha Plant Behavior -->
  <qg:behavior name="PiranhaBehavior">
    <q:set name="emergeHeight" value="32" type="integer" />
    <q:set name="hiddenY" value="0" type="float" />

    <qg:state-machine initial="hidden">
      <qg:state name="hidden">
        <qg:on event="emerge" transition="emerging" />
        <q:function name="enter">
          this.hiddenY = this.owner.sprite.y;
        </q:function>
      </qg:state>

      <qg:state name="emerging">
        <qg:on event="fullyOut" transition="visible" />
        <q:function name="update">
          this.owner.sprite.y -= 0.5;
          if (this.owner.sprite.y &lt;= this.hiddenY - this.emergeHeight) {
            this._smEmit('fullyOut');
          }
        </q:function>
      </qg:state>

      <qg:state name="visible">
        <qg:on event="hide" transition="hiding" />
      </qg:state>

      <qg:state name="hiding">
        <qg:on event="fullyHidden" transition="hidden" />
        <q:function name="update">
          this.owner.sprite.y += 0.5;
          if (this.owner.sprite.y >= this.hiddenY) {
            this._smEmit('fullyHidden');
          }
        </q:function>
      </qg:state>
    </qg:state-machine>
  </qg:behavior>

  <!-- ==================== PREFABS ==================== -->

  <!-- Coin Prefab -->
  <qg:prefab name="Coin">
    <qg:sprite src="assets/smw/sprites/objects.png"
               width="16" height="16"
               frame-x="0" frame-y="96"
               body="static" sensor="true" tag="coin">
      <qg:animation name="spin" frames="0-3" speed="0.1" loop="true" auto-play="true" />
    </qg:sprite>
  </qg:prefab>

  <!-- Dragon Coin Prefab -->
  <qg:prefab name="DragonCoin">
    <qg:sprite src="assets/smw/sprites/objects.png"
               width="16" height="32"
               frame-x="0" frame-y="160"
               body="static" sensor="true" tag="dragoncoin">
      <qg:animation name="spin" frames="0-3" speed="0.15" loop="true" auto-play="true" />
    </qg:sprite>
  </qg:prefab>

  <!-- Koopa Green Prefab -->
  <qg:prefab name="KoopaGreen">
    <qg:sprite src="assets/smw/sprites/koopas.png"
               width="16" height="24"
               frame-x="64" frame-y="0"
               body="dynamic" bounce="0" friction="0.3" tag="enemy">
      <qg:animation name="walk" frames="0-1" speed="0.15" loop="true" auto-play="true" />
      <qg:use behavior="PatrolBehavior" speed="1.0"
             on-collision="onWallHit" collision-tag="solid" />
    </qg:sprite>
  </qg:prefab>

  <!-- Koopa Red Prefab (doesn't fall off edges) -->
  <qg:prefab name="KoopaRed">
    <qg:sprite src="assets/smw/sprites/koopas.png"
               width="16" height="24"
               frame-x="0" frame-y="0"
               body="dynamic" bounce="0" friction="0.3" tag="enemy">
      <qg:animation name="walk" frames="0-1" speed="0.15" loop="true" auto-play="true" />
      <qg:use behavior="PatrolBehavior" speed="0.8"
             on-collision="onWallHit" collision-tag="solid" />
      <qg:use behavior="PatrolBehavior"
             on-collision="onEdgeDetected" collision-tag="edge" />
    </qg:sprite>
  </qg:prefab>

  <!-- Rex Prefab -->
  <qg:prefab name="Rex">
    <qg:sprite src="assets/smw/sprites/rex_blargg_dino.png"
               width="16" height="32"
               frame-x="0" frame-y="0"
               body="dynamic" bounce="0" friction="0.3" tag="enemy">
      <qg:animation name="walk" frames="0-1" speed="0.2" loop="true" auto-play="true" />
      <qg:use behavior="RexBehavior" />
    </qg:sprite>
  </qg:prefab>

  <!-- Piranha Plant Prefab -->
  <qg:prefab name="PiranhaPlant">
    <qg:sprite src="assets/smw/sprites/piranha_plants.png"
               width="16" height="32"
               frame-x="0" frame-y="48"
               body="static" sensor="true" tag="enemy">
      <qg:animation name="chomp" frames="0-1" speed="0.3" loop="true" auto-play="true" />
      <qg:use behavior="PiranhaBehavior" emergeHeight="28" />
    </qg:sprite>
  </qg:prefab>

  <!-- Question Block Prefab -->
  <qg:prefab name="QuestionBlock">
    <qg:sprite src="assets/smw/sprites/objects.png"
               width="16" height="16"
               frame-x="0" frame-y="0"
               body="static" tag="qblock">
      <qg:animation name="shine" frames="0-3" speed="0.2" loop="true" auto-play="true" />
      <qg:use behavior="QuestionBlockBehavior" contents="coin" />
    </qg:sprite>
  </qg:prefab>

  <!-- Pipe Prefab -->
  <qg:prefab name="PipeVertical">
    <qg:sprite src="assets/smw/sprites/tileset_ground.png"
               width="32" height="48"
               frame-x="192" frame-y="820"
               body="static" tag="solid" />
  </qg:prefab>

  <!-- Goal Post Prefab -->
  <qg:prefab name="GoalPost">
    <qg:sprite src="assets/smw/sprites/goal_post.png"
               width="16" height="128"
               frame-x="80" frame-y="0"
               body="static" sensor="true" tag="goal">
      <qg:sprite id="goal_tape" src="assets/smw/sprites/goal_post.png"
                 width="64" height="8"
                 frame-x="0" frame-y="48"
                 offset-x="-24" offset-y="-48" />
    </qg:sprite>
  </qg:prefab>

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

    <!-- ==================== TILEMAP ==================== -->

    <qg:tilemap id="level" src="assets/smw/sprites/tileset_yi1_clean.png"
                tile-width="16" tile-height="16">

      <!-- Background Layer (hills, bushes - no collision) -->
      <qg:layer name="background" collision="false">
        <!-- Row format: tile IDs separated by commas -->
        <!-- Using simplified data for demo - in production use level editor -->
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,40,41,42,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,40,41,42,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,40,41,42,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
      </qg:layer>

      <!-- Terrain Layer (ground with collision) -->
      <qg:layer name="terrain" collision="true">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,4
6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6
6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6
6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6
      </qg:layer>
    </qg:tilemap>

    <!-- ==================== PLAYER ==================== -->

    <qg:sprite id="mario" src="assets/smw/sprites/mario.png"
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

    <qg:sound id="bgm" src="assets/smw/sounds/smw_course_clear.wav"
              channel="music" loop="true" trigger="scene.start" volume="0.3" />
    <qg:sound id="jump_sfx" src="assets/smw/sounds/smw_jump.wav"
              channel="sfx" trigger="player.jump" />
    <qg:sound id="coin_sfx" src="assets/smw/sounds/smw_coin.wav" channel="sfx" />
    <qg:sound id="stomp_sfx" src="assets/smw/sounds/smw_stomp.wav" channel="sfx" />
    <qg:sound id="powerup_sfx" src="assets/smw/sounds/smw_power-up.wav" channel="sfx" />
    <qg:sound id="oneup_sfx" src="assets/smw/sounds/smw_1-up.wav" channel="sfx" />
    <qg:sound id="kick_sfx" src="assets/smw/sounds/smw_kick.wav" channel="sfx" />
    <qg:sound id="lost_life_sfx" src="assets/smw/sounds/smw_lost_a_life.wav" channel="sfx" />
    <qg:sound id="course_clear_sfx" src="assets/smw/sounds/smw_course_clear.wav" channel="music" />

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
