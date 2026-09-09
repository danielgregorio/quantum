<q:application id="platformer" type="game" engine="2d">

  <!-- ==================== BEHAVIORS ==================== -->

  <qg:behavior name="Collectible">
    <q:set name="value" value="10" />
    <q:function name="onCollect">
      <q:set name="score" value="{score + self.value}" scope="scene" />
    </q:function>
  </qg:behavior>

  <qg:behavior name="Damageable">
    <q:set name="health" value="3" />
    <q:function name="takeDamage">
      <q:set name="self.health" value="{self.health - 1}" />
    </q:function>
  </qg:behavior>

  <qg:behavior name="Patrol">
    <q:set name="speed" value="2" />
    <q:set name="range" value="100" />
    <qg:state-machine initial="walk-right">
      <qg:state name="walk-right">
        <qg:on event="hit-wall" transition="walk-left" />
        <qg:on event="range-limit" transition="walk-left" />
        <q:function name="update">
          <q:set name="self.x" value="{self.x + self.speed}" />
        </q:function>
      </qg:state>
      <qg:state name="walk-left">
        <qg:on event="hit-wall" transition="walk-right" />
        <qg:on event="range-limit" transition="walk-right" />
        <q:function name="update">
          <q:set name="self.x" value="{self.x - self.speed}" />
        </q:function>
      </qg:state>
    </qg:state-machine>
  </qg:behavior>

  <!-- ==================== PREFABS ==================== -->

  <qg:prefab name="Coin">
    <qg:sprite src="coin.png" body="dynamic" sensor="true" tag="coin">
      <qg:animation name="spin" frames="0-5" speed="0.1" auto-play="true" />
      <qg:use behavior="Collectible" value="10" on-collision="onCollect" />
    </qg:sprite>
  </qg:prefab>

  <qg:prefab name="Gem">
    <qg:sprite src="gem.png" body="dynamic" sensor="true" tag="coin">
      <qg:use behavior="Collectible" value="50" on-collision="onCollect" />
    </qg:sprite>
  </qg:prefab>

  <qg:prefab name="Enemy">
    <qg:sprite src="enemy.png" body="dynamic" tag="enemy">
      <qg:collider shape="box" />
      <qg:animation name="walk" frames="0-7" speed="0.1" auto-play="true" />
      <qg:use behavior="Patrol" speed="2" range="150" />
      <qg:use behavior="Damageable" health="1" />
    </qg:sprite>
  </qg:prefab>

  <!-- ==================== SCENE ==================== -->

  <qg:scene name="level1" width="1280" height="720" background="#87CEEB">
    <qg:physics gravity-y="9.8" bounds="canvas" />
    <q:set name="score" value="0" type="integer" />
    <q:set name="lives" value="3" type="integer" />
    <qg:camera follow="player" lerp="0.1" bounds="scene" />

    <!-- Player -->
    <qg:sprite id="player" src="hero-sheet.png" x="100" y="400"
               frame-width="32" frame-height="32"
               controls="wasd" speed="5" jump-force="12"
               body="dynamic" bounce="0" friction="0.5">
      <qg:animation name="idle" frames="0-3" speed="0.15" auto-play="true" />
      <qg:animation name="walk-right" frames="4-11" speed="0.08" />
      <qg:animation name="walk-left" frames="4-11" speed="0.08" />
      <qg:animation name="jump" frames="12-14" speed="0.1" />
      <qg:use behavior="Damageable" health="5" />
    </qg:sprite>

    <!-- Terrain -->
    <qg:sprite id="ground" src="ground.png" x="640" y="680"
               width="1280" height="40" body="static" tag="solid" />
    <qg:sprite id="platform1" src="platform.png" x="300" y="500"
               width="200" height="20" body="static" tag="solid" />
    <qg:sprite id="platform2" src="platform.png" x="700" y="400"
               width="200" height="20" body="static" tag="solid" />

    <!-- Collectibles via prefabs -->
    <qg:group name="coins">
      <qg:instance prefab="Coin" x="300" y="450" />
      <qg:instance prefab="Coin" x="500" y="350" />
      <qg:instance prefab="Coin" x="700" y="350" />
    </qg:group>
    <qg:instance prefab="Gem" x="1000" y="250" />

    <!-- Enemies via prefabs -->
    <qg:instance prefab="Enemy" id="enemy1" x="400" y="460" />
    <qg:instance prefab="Enemy" id="enemy2" x="800" y="360" speed="3" />

    <!-- Audio -->
    <qg:sound id="bgm" src="music.mp3" volume="0.4" loop="true"
              trigger="scene.start" channel="music" />
    <qg:sound id="jump-sfx" src="jump.wav" trigger="player.jump" channel="sfx" />
    <qg:sound id="collect-sfx" src="coin.wav" channel="sfx" />

    <!-- HUD -->
    <qg:hud position="top-left">
      <text style="font-size:24px; color:white">Score: {score}</text>
    </qg:hud>
    <qg:hud position="top-right">
      <text style="font-size:24px; color:red">Lives: {lives}</text>
    </qg:hud>

  </qg:scene>

</q:application>
