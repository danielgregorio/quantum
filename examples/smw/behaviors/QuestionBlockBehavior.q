<q:behavior name="QuestionBlockBehavior">
  <!-- Question Block Behavior - Activates when hit from below -->
  <q:set name="active" value="true" type="boolean" />
  <q:set name="contents" value="coin" type="string" />

  <q:function name="onHitFromBelow">
    if (!this.active) return;

    var player = this._other;
    if (!player || !player.body) return;

    <!-- Check if hit from below -->
    var playerTop = player.body.position.y - 16;
    var blockBottom = this.owner.body.position.y + 8;

    if (playerTop > blockBottom - 8) {
      this.active = false;
      this.owner.sprite.texture = game.getTexture('used_block');

      <!-- Spawn contents -->
      if (this.contents === 'coin') {
        game.play('coin_sfx');
        game.emit('coinCollected', { points: 200 });
      } else {
        game.spawn('powerupSpawner', this.owner.sprite.x, this.owner.sprite.y - 20);
      }

      <!-- Bounce animation -->
      game.tween(this.owner.sprite, { y: this.owner.sprite.y - 8 }, 0.1, 'easeOut');
      game.tween(this.owner.sprite, { y: this.owner.sprite.y }, 0.1, 'easeIn', 0.1);
    }
  </q:function>
</q:behavior>
