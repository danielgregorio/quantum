<q:application id="fighter" type="game" engine="2d">

  <!-- ==================== FIGHTER BEHAVIOR ==================== -->

  <qg:behavior name="Fighter">
    <q:set name="health" value="100" type="integer" />
    <q:set name="maxHealth" value="100" type="integer" />
    <q:set name="facing" value="1" type="integer" />
    <q:set name="attackPower" value="10" type="integer" />
    <q:set name="blocking" value="false" type="boolean" />
    <q:set name="hitStun" value="0" type="integer" />

    <q:function name="onHit">
      <q:if condition="{self.blocking}">
        game.camera.shake(2, 0.1);
        game.play('block_sfx');
      </q:if>
      <q:if condition="{!self.blocking}">
        <q:set name="self.health" value="{self.health - info.attackPower}" />
        game.camera.shake(5, 0.3);
        game.play('hit_sfx');
        this._smEmit('hit');
        <q:if condition="{self.health &lt;= 0}">
          game.play('ko_sfx');
          <q:set name="self.health" value="0" />
        </q:if>
      </q:if>
    </q:function>

    <qg:state-machine initial="idle">

      <!-- IDLE STATE -->
      <qg:state name="idle">
        <qg:on event="move" transition="walk" />
        <qg:on event="jump" transition="jump" />
        <qg:on event="punch" transition="attack_punch" />
        <qg:on event="kick" transition="attack_kick" />
        <qg:on event="block" transition="block" />
        <qg:on event="hit" transition="hit" />
        <q:function name="enter">
          self.blocking = false;
        </q:function>
      </qg:state>

      <!-- WALK STATE -->
      <qg:state name="walk">
        <qg:on event="stop" transition="idle" />
        <qg:on event="jump" transition="jump" />
        <qg:on event="punch" transition="attack_punch" />
        <qg:on event="kick" transition="attack_kick" />
        <qg:on event="block" transition="block" />
        <qg:on event="hit" transition="hit" />
        <q:function name="update">
          game.moveX(this.owner, self.facing * self.speed);
        </q:function>
      </qg:state>

      <!-- JUMP STATE -->
      <qg:state name="jump">
        <qg:on event="land" transition="idle" />
        <qg:on event="punch" transition="attack_punch" />
        <qg:on event="kick" transition="attack_kick" />
        <qg:on event="hit" transition="hit" />
        <q:function name="enter">
          self.vy = -self.jumpForce;
        </q:function>
      </qg:state>

      <!-- PUNCH ATTACK STATE -->
      <qg:state name="attack_punch">
        <qg:on event="done" transition="idle" />
        <qg:on event="hit" transition="hit" />
        <q:function name="enter">
          self.attackPower = 10;
          game.play('punch_sfx');
        </q:function>
      </qg:state>

      <!-- KICK ATTACK STATE -->
      <qg:state name="attack_kick">
        <qg:on event="done" transition="idle" />
        <qg:on event="hit" transition="hit" />
        <q:function name="enter">
          self.attackPower = 15;
          game.play('kick_sfx');
        </q:function>
      </qg:state>

      <!-- BLOCK STATE -->
      <qg:state name="block">
        <qg:on event="release" transition="idle" />
        <qg:on event="hit" transition="hit" />
        <q:function name="enter">
          self.blocking = true;
        </q:function>
        <q:function name="exit">
          self.blocking = false;
        </q:function>
      </qg:state>

      <!-- HIT / STUN STATE -->
      <qg:state name="hit">
        <qg:on event="recover" transition="idle" />
        <q:function name="enter">
          self.hitStun = 20;
        </q:function>
        <q:function name="update">
          self.hitStun--;
          <q:if condition="{self.hitStun &lt;= 0}">
            this._smEmit('recover');
          </q:if>
        </q:function>
      </qg:state>

    </qg:state-machine>
  </qg:behavior>

  <!-- ==================== SCENE ==================== -->

  <qg:scene name="arena" width="800" height="600" background="#1a1a2e">
    <qg:physics gravity-y="9.8" bounds="canvas" />
    <qg:camera follow="none" lerp="0.1" />

    <!-- Arena Floor -->
    <qg:sprite id="floor" src="arena-floor.png" x="400" y="570"
               width="800" height="60" body="static" tag="solid" />

    <!-- Arena Walls -->
    <qg:sprite id="wall-left" src="wall.png" x="0" y="300"
               width="20" height="600" body="static" tag="wall" />
    <qg:sprite id="wall-right" src="wall.png" x="800" y="300"
               width="20" height="600" body="static" tag="wall" />

    <!-- ==================== PLAYER 1 (WASD) ==================== -->

    <qg:sprite id="player1" src="fighter1-sheet.png" x="200" y="440"
               width="64" height="64" frame-width="64" frame-height="64"
               body="dynamic" controls="wasd" speed="4" jump-force="12"
               tag="player1" bounce="0" friction="0.3">
      <qg:animation name="idle" frames="0-3" speed="0.15" auto-play="true" />
      <qg:animation name="walk" frames="4-9" speed="0.1" />
      <qg:animation name="jump" frames="10-12" speed="0.1" />
      <qg:animation name="punch" frames="13-16" speed="0.06" />
      <qg:animation name="kick" frames="17-21" speed="0.06" />
      <qg:animation name="block" frames="22-23" speed="0.15" />
      <qg:animation name="hit" frames="24-26" speed="0.1" />
      <qg:use behavior="Fighter" health="100" on-collision="onHit" collision-tag="attack-p2" />
    </qg:sprite>

    <!-- Player 1 Inputs -->
    <qg:input key="j" action="punch" type="press" target="player1" />
    <qg:input key="k" action="kick" type="press" target="player1" />
    <qg:input key="l" action="block" type="press" target="player1" />
    <qg:input key="l" action="release" type="release" target="player1" />

    <!-- ==================== PLAYER 2 (ARROWS) ==================== -->

    <qg:sprite id="player2" src="fighter2-sheet.png" x="600" y="440"
               width="64" height="64" frame-width="64" frame-height="64"
               body="dynamic" controls="arrows" speed="4" jump-force="12"
               tag="player2" bounce="0" friction="0.3">
      <qg:animation name="idle" frames="0-3" speed="0.15" auto-play="true" />
      <qg:animation name="walk" frames="4-9" speed="0.1" />
      <qg:animation name="jump" frames="10-12" speed="0.1" />
      <qg:animation name="punch" frames="13-16" speed="0.06" />
      <qg:animation name="kick" frames="17-21" speed="0.06" />
      <qg:animation name="block" frames="22-23" speed="0.15" />
      <qg:animation name="hit" frames="24-26" speed="0.1" />
      <qg:use behavior="Fighter" health="100" on-collision="onHit" collision-tag="attack-p1" />
    </qg:sprite>

    <!-- Player 2 Inputs -->
    <qg:input key="numpad1" action="punch" type="press" target="player2" />
    <qg:input key="numpad2" action="kick" type="press" target="player2" />
    <qg:input key="numpad3" action="block" type="press" target="player2" />
    <qg:input key="numpad3" action="release" type="release" target="player2" />

    <!-- ==================== ATTACK HITBOXES ==================== -->

    <qg:sprite id="hitbox-p1" src="none" x="0" y="0"
               width="30" height="20" body="dynamic" sensor="true"
               tag="attack-p1" parent="player1" offset-x="40" offset-y="0" />

    <qg:sprite id="hitbox-p2" src="none" x="0" y="0"
               width="30" height="20" body="dynamic" sensor="true"
               tag="attack-p2" parent="player2" offset-x="-40" offset-y="0" />

    <!-- ==================== AUDIO ==================== -->

    <qg:sound id="punch_sfx" src="sounds/punch.wav" channel="sfx" />
    <qg:sound id="kick_sfx" src="sounds/kick.wav" channel="sfx" />
    <qg:sound id="hit_sfx" src="sounds/hit.wav" channel="sfx" />
    <qg:sound id="ko_sfx" src="sounds/ko.wav" channel="sfx" />
    <qg:sound id="block_sfx" src="sounds/block.wav" channel="sfx" />
    <qg:sound id="bgm" src="sounds/fight-music.mp3" volume="0.5" loop="true"
              trigger="scene.start" channel="music" />

    <!-- ==================== HUD ==================== -->

    <qg:hud position="top-left">
      <div style="padding:10px; color:white; font-family:monospace;">
        <div style="font-size:18px; font-weight:bold; margin-bottom:4px;">P1</div>
        <div style="width:200px; height:20px; background:#333; border:2px solid #fff; border-radius:4px;">
          <div style="width:{player1.health}%; height:100%; background:linear-gradient(#4caf50,#2e7d32); border-radius:2px; transition:width 0.2s;"></div>
        </div>
        <div style="font-size:12px; margin-top:2px;">{player1.health} / 100</div>
      </div>
    </qg:hud>

    <qg:hud position="top-right">
      <div style="padding:10px; color:white; font-family:monospace; text-align:right;">
        <div style="font-size:18px; font-weight:bold; margin-bottom:4px;">P2</div>
        <div style="width:200px; height:20px; background:#333; border:2px solid #fff; border-radius:4px;">
          <div style="width:{player2.health}%; height:100%; background:linear-gradient(#f44336,#c62828); border-radius:2px; transition:width 0.2s;"></div>
        </div>
        <div style="font-size:12px; margin-top:2px;">{player2.health} / 100</div>
      </div>
    </qg:hud>

  </qg:scene>

</q:application>
