<q:behavior name="RexBehavior">
  <!-- Rex Enemy Behavior (2-hit enemy) -->
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
        this.owner.sprite.height = 16; <!-- Squash sprite -->
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
</q:behavior>
