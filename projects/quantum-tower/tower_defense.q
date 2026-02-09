<q:application id="tower-defense" type="game" engine="2d">

  <qg:scene name="battlefield" width="800" height="600" background="#2d5a1e">

    <qg:physics gravity-x="0" gravity-y="0" />

    <!-- Game State -->
    <q:set name="gold" value="100" type="number" />
    <q:set name="lives" value="20" type="number" />
    <q:set name="waveNumber" value="0" type="number" />
    <q:set name="towerCost" value="25" type="number" />
    <q:set name="enemiesPerWave" value="5" type="number" />
    <q:set name="waveActive" value="false" type="boolean" />

    <!-- Path waypoints for enemies -->
    <q:set name="pathX" value="[0,200,200,600,600,800]" />
    <q:set name="pathY" value="[300,300,150,150,450,450]" />

    <!-- Path tiles (visual) -->
    <qg:sprite id="path0" src="assets/path.png" x="0"   y="275" width="225" height="50" body="static" />
    <qg:sprite id="path1" src="assets/path.png" x="175" y="150" width="50"  height="175" body="static" />
    <qg:sprite id="path2" src="assets/path.png" x="200" y="125" width="425" height="50"  body="static" />
    <qg:sprite id="path3" src="assets/path.png" x="575" y="150" width="50"  height="325" body="static" />
    <qg:sprite id="path4" src="assets/path.png" x="600" y="425" width="200" height="50"  body="static" />

    <!-- Placement grid (clickable slots for towers) -->
    <qg:sprite id="slot0" src="assets/slot.png" x="100" y="400" width="48" height="48" body="static" tag="slot">
      <qg:clickable action="placeTower" cursor="crosshair" />
    </qg:sprite>
    <qg:sprite id="slot1" src="assets/slot.png" x="300" y="80"  width="48" height="48" body="static" tag="slot">
      <qg:clickable action="placeTower" cursor="crosshair" />
    </qg:sprite>
    <qg:sprite id="slot2" src="assets/slot.png" x="400" y="80"  width="48" height="48" body="static" tag="slot">
      <qg:clickable action="placeTower" cursor="crosshair" />
    </qg:sprite>
    <qg:sprite id="slot3" src="assets/slot.png" x="500" y="200" width="48" height="48" body="static" tag="slot">
      <qg:clickable action="placeTower" cursor="crosshair" />
    </qg:sprite>
    <qg:sprite id="slot4" src="assets/slot.png" x="500" y="500" width="48" height="48" body="static" tag="slot">
      <qg:clickable action="placeTower" cursor="crosshair" />
    </qg:sprite>
    <qg:sprite id="slot5" src="assets/slot.png" x="700" y="350" width="48" height="48" body="static" tag="slot">
      <qg:clickable action="placeTower" cursor="crosshair" />
    </qg:sprite>

    <!-- Behaviors -->
    <qg:behavior name="Enemy">
      <q:set name="hp" value="3" type="number" />
      <q:set name="speed" value="80" type="number" />
      <q:set name="waypointIndex" value="0" type="number" />

      <qg:state-machine initial="walk">
        <qg:state name="walk">
          <q:function name="update">
            var idx = this.owner.waypointIndex;
            var px = game.getVar('pathX');
            var py = game.getVar('pathY');
            if (idx >= px.length) {
              game.addVar('lives', -1);
              game.destroy(this.owner);
              return;
            }
            var tx = px[idx]; var ty = py[idx];
            var dx = tx - this.owner.x;
            var dy = ty - this.owner.y;
            var dist = Math.sqrt(dx*dx + dy*dy);
            if (dist &lt; 5) {
              this.owner.waypointIndex = idx + 1;
            } else {
              game.moveX(this.owner, (dx/dist) * this.owner.speed * game.dt);
              game.moveY(this.owner, (dy/dist) * this.owner.speed * game.dt);
            }
          </q:function>
          <qg:on event="hit" transition="hit" />
        </qg:state>

        <qg:state name="hit">
          <q:function name="enter">
            this.owner.hp -= 1;
            if (this.owner.hp &lt;= 0) {
              this._smEmit('dead');
            } else {
              this._smEmit('recover');
            }
          </q:function>
          <qg:on event="recover" transition="walk" />
          <qg:on event="dead" transition="die" />
        </qg:state>

        <qg:state name="die">
          <q:function name="enter">
            game.addVar('gold', 10);
            game.play('killSound');
            game.destroy(this.owner);
          </q:function>
        </qg:state>
      </qg:state-machine>
    </qg:behavior>

    <qg:behavior name="Tower">
      <q:set name="range" value="120" type="number" />
      <q:set name="fireRate" value="1.0" />
      <q:set name="cooldown" value="0.0" />

      <q:function name="update">
        this.owner.cooldown -= game.dt;
        if (this.owner.cooldown > 0) return;
        var enemies = game.findByTag('enemy');
        for (var i = 0; i &lt; enemies.length; i++) {
          var e = enemies[i];
          var dx = e.x - this.owner.x;
          var dy = e.y - this.owner.y;
          var dist = Math.sqrt(dx*dx + dy*dy);
          if (dist &lt; this.owner.range) {
            game.spawn('bulletSpawner', this.owner.x, this.owner.y);
            var bullets = game.findByTag('bullet');
            var b = bullets[bullets.length - 1];
            if (b) b.targetId = e.id;
            this.owner.cooldown = this.owner.fireRate;
            game.play('shootSound');
            break;
          }
        }
      </q:function>
    </qg:behavior>

    <qg:behavior name="Bullet">
      <q:set name="speed" value="250" type="number" />
      <q:set name="targetId" value="" type="string" />

      <q:function name="update">
        if (!this.owner.targetId) { game.destroy(this.owner); return; }
        var target = game.findById(this.owner.targetId);
        if (!target) { game.destroy(this.owner); return; }
        var arrived = game.moveToward(this.owner, target.id, this.owner.speed);
        if (arrived) {
          target._smEmit('hit');
          game.destroy(this.owner);
        }
      </q:function>
    </qg:behavior>

    <!-- Prefabs -->
    <qg:prefab name="EnemyPrefab">
      <qg:sprite id="enemy" src="assets/enemy.png" width="32" height="32" body="kinematic" tag="enemy">
        <qg:use behavior="Enemy" />
      </qg:sprite>
    </qg:prefab>

    <qg:prefab name="BulletPrefab">
      <qg:sprite id="bullet" src="assets/bullet.png" width="8" height="8" body="dynamic" tag="bullet" sensor="true">
        <qg:use behavior="Bullet" />
      </qg:sprite>
    </qg:prefab>

    <!-- Spawners -->
    <qg:spawn id="enemySpawner"  prefab="EnemyPrefab"  pool-size="30" x="0" y="300" />
    <qg:spawn id="bulletSpawner" prefab="BulletPrefab" pool-size="20" x="0" y="0" />

    <!-- Wave timer -->
    <qg:timer id="waveTimer" interval="8" action="spawnWave" auto-start="true" />

    <!-- Game functions -->
    <q:function name="spawnWave">
      <q:set name="waveNumber" value="{waveNumber + 1}" />
      <q:set name="enemiesPerWave" value="{5 + waveNumber * 2}" />
      var count = game.getVar('enemiesPerWave');
      for (var i = 0; i &lt; count; i++) {
        game.scheduleOnce(i * 0.6, function() {
          game.spawn('enemySpawner');
        });
      }
    </q:function>

    <q:function name="placeTower">
      var cost = game.getVar('towerCost');
      var g = game.getVar('gold');
      if (g &lt; cost) return;
      game.addVar('gold', -cost);
      var slot = game.clickedSprite;
      game.createSprite({
        src: 'assets/tower.png',
        x: slot.x, y: slot.y,
        width: 48, height: 48,
        body: 'static', tag: 'tower'
      });
      var towers = game.findByTag('tower');
      var t = towers[towers.length - 1];
      game.attachBehavior(t, 'Tower');
      game.removeClickable(slot);
      game.play('buildSound');
    </q:function>

    <!-- Sounds -->
    <qg:sound id="shootSound" src="assets/shoot.wav" trigger="manual" />
    <qg:sound id="killSound"  src="assets/kill.wav"  trigger="manual" />
    <qg:sound id="buildSound" src="assets/build.wav" trigger="manual" />

    <!-- HUD -->
    <qg:hud position="top-left">
      <text style="color:#FFD700;font-size:18px;font-weight:bold;">Gold: {gold}</text>
      <text style="color:#FF4444;font-size:18px;margin-left:20px;">Lives: {lives}</text>
      <text style="color:#FFFFFF;font-size:18px;margin-left:20px;">Wave: {waveNumber}</text>
    </qg:hud>

    <qg:hud position="bottom-center">
      <text style="color:#AAAAAA;font-size:14px;">Click green slots to place towers ({towerCost}g)</text>
    </qg:hud>

  </qg:scene>

</q:application>
