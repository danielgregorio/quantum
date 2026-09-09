<q:behavior name="PlayerBehavior">
  <!-- Mario Player Behavior - Handles all player-related collisions and state -->
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
      <!-- Stomp enemy -->
      Matter.Body.setVelocity(mario.body, {x: mario.body.velocity.x, y: -8});
      game.play('stomp_sfx');
      game.emit('enemyKilled', { enemy: enemy, points: 100 });
      game.destroy(enemy);
    } else {
      <!-- Take damage -->
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
</q:behavior>
