<q:behavior name="PatrolBehavior">
  <!-- Basic Patrol Enemy Behavior - Walks back and forth -->
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

    <!-- Move in patrol direction -->
    Matter.Body.setVelocity(body, {
      x: this.direction * this.speed,
      y: body.velocity.y
    });

    <!-- Flip sprite based on direction -->
    this.owner.sprite.scale.x = this.direction > 0 ? -1 : 1;
  </q:function>

  <q:function name="onWallHit">
    this.direction *= -1;
  </q:function>

  <q:function name="onEdgeDetected">
    this.direction *= -1;
  </q:function>
</q:behavior>
