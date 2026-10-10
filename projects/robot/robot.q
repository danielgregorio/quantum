<q:application id="robot" type="game">

  <!-- Robot: Godot's "Platformer 2D" demo (godot-demo-projects, 2d/platformer, MIT),
       transcribed. One closed level of slopes, ledges, moving platforms, coins and
       crawling enemies; the robot runs, jumps twice, shoots, and cannot be hurt.
       The demo's art and sounds are in assets/ (assets/LICENSE.md); README.md maps
       the original, piece by piece. -->

  <!-- The demo's keys: jump on Up, W or the joypad's A; shoot on Space, Z, Ctrl or
       the joypad's X; pause on Escape or Start. Left and right keep their defaults. -->
  <qg:input action="jump" keys="Up, W, JoyA" />
  <qg:input action="shoot" keys="Space, Z, Ctrl, JoyX" />
  <qg:input action="pause" keys="Escape, JoyStart" />

  <!-- The tiles are 64 px. Most are full squares; these are not: a grassy top that
       starts 10 px down, two thin ledges, a slope to walk up and jump through. -->
  <qg:tileset name="tiles" src="assets/tiles.png" tile="64">
    <qg:tile frame="0" shape="0,10; 64,10; 64,64; 0,64" />
    <qg:tile frame="1" shape="0,10; 64,10; 64,64; 0,64" />
    <qg:tile frame="2" shape="0,10; 64,10; 64,46; 0,46" />
    <qg:tile frame="3" shape="0,10; 64,10; 64,43; 0,43" />
    <qg:tile frame="18" shape="0,7.25; 58.18,64; 0,64" one-way="true" />
    <qg:tile frame="27" shape="0,10; 64,10; 64,64; 0,64" />
    <qg:tile frame="28" shape="0,10; 64,10; 64,64; 0,64" />
    <qg:tile frame="29" shape="0,10; 64,10; 64,64; 0,64" />
  </qg:tileset>
  <qg:spritesheet name="robot" src="assets/robot.png" tile="64" />
  <qg:spritesheet name="enemy" src="assets/enemy.png" tile="128" />
  <qg:spritesheet name="coin" src="assets/coin.png" tile="32" />
  <qg:spritesheet name="bullet" src="assets/bullet.png" tile="16" />
  <qg:spritesheet name="platform" src="assets/platform.png" tile="256x64" />
  <!-- The demo's ParallaxBackground, composed by scripts/art/robot_sky.py. -->
  <qg:spritesheet name="sky" src="assets/sky.png" tile="2458x480" />
  <qg:spritesheet name="hills" src="assets/hills.png" tile="2048x480" />

  <qg:sound name="jump" src="assets/jump.wav" />
  <qg:sound name="shoot" src="assets/shoot.wav" />
  <qg:sound name="coin" src="assets/coin_pickup.wav" />
  <qg:sound name="explode" src="assets/explode.wav" />

  <qg:prefab name="Coin" tag="coin" sheet="coin" frame="0" hitbox="20x20" scale="0.65">
    <qg:animation name="walk" frames="0,1,2,3,2,1" fps="6" />
  </qg:prefab>

  <!-- Crawls at 22 px/s and turns at walls and before falling off. -->
  <qg:prefab name="Enemy" tag="enemy" sheet="enemy" frame="0" hitbox="50x36" scale="0.8"
             ai="patrol" speed="22" direction="right" turns-at="edge" gravity="2100">
    <qg:animation name="walk" frames="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15" fps="16" />
  </qg:prefab>

  <!-- 850 px/s the way the robot faces, gone after a second or on a wall. -->
  <qg:prefab name="Bullet" tag="bullet" sheet="bullet" frame="0" hitbox="16x16"
             ai="fly" heading="right" speed="850" lifetime="60" walls="stop">
    <qg:on-collision with="enemy">
      <qg:burst at="other" color="#ffd27f" count="24" />
      <qg:play sound="explode" />
      <qg:destroy target="other" />
      <qg:destroy target="me" />
    </qg:on-collision>
  </qg:prefab>

  <!-- 192x27 to stand on, 7.5 px above the picture's middle; jumped through from below. -->
  <qg:prefab name="LiftUp" tag="lift" sheet="platform" frame="0" hitbox="192x27" solid="true" one-way="true"
             shape="-96,-21; 96,-21; 96,6; -96,6" ai="shuttle" dy="-210" period="240" />
  <qg:prefab name="LiftSlow" tag="lift" sheet="platform" frame="0" hitbox="192x27" solid="true" one-way="true"
             shape="-96,-21; 96,-21; 96,6; -96,6" ai="shuttle" dy="-295" period="480" />
  <!-- The tilted platform at the top: the demo's polygon, rotated with the instance. -->
  <qg:prefab name="Ledge" tag="ledge" sheet="platform" frame="0" hitbox="192x27" solid="true"
             shape="-174.04,-0.43; -94.04,-23.61; 91.84,-28.64; 80.29,-5.16; -54.32,0.04; -179.99,26.44" />

  <qg:scene name="level" width="800" height="480" background="#52c9ff">
    <!-- level/background/parallax_background.tscn: a base scale of 0.1 times each layer's -->
    <qg:parallax sheet="sky" scroll="0.02" />
    <qg:parallax sheet="hills" scroll="0.04" />
    <q:set name="coins" value="0" type="number" />

    <!-- 35 x 24 tiles of 64 px; the demo's map, whose top-left cell is (-12, -11), so
         every position here is the demo's plus (768, 704). A negative number is a
         tile flipped left to right. -->
    <qg:tilemap tileset="tiles" collision="true">
-2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2
-10,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,10
-10,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,10
-10,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,10
-10,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,10
-10,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,10
-10,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,10
-10,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,10
-10,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,10
-10,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,10
-10,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,10
-10,1,1,1,1,1,1,1,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-2,-1,1,1,1,1,1,1,10
-10,9,9,9,9,9,9,9,10,0,0,0,0,0,-4,3,3,-3,4,0,0,0,0,0,0,0,-10,-9,9,9,9,9,9,9,10
-10,9,9,9,9,9,9,9,10,0,0,-4,4,0,0,0,0,0,0,0,0,0,0,0,0,0,-10,-9,9,9,9,9,9,9,10
-10,9,9,9,9,9,9,9,10,0,0,0,0,0,0,0,0,0,-4,-3,4,0,0,0,0,0,-10,-9,9,9,9,9,9,9,10
-10,9,9,9,9,9,9,9,18,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-10,-9,9,9,9,9,9,9,10
-10,9,9,9,9,9,9,9,9,10,0,0,0,-4,3,4,0,0,0,0,0,0,0,0,0,0,-10,-9,9,9,9,9,9,9,10
-10,9,9,9,9,9,9,9,-14,10,0,0,0,0,0,0,0,0,-2,28,30,28,2,0,0,0,-10,-9,9,9,9,9,9,9,10
-10,9,9,9,9,9,9,9,9,10,0,0,0,-4,-3,-3,4,0,-16,-7,15,15,16,0,0,0,-10,-9,9,9,9,9,9,9,10
-10,9,9,9,9,9,9,9,9,10,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-10,-9,9,9,9,9,9,9,10
-10,9,9,9,9,9,9,9,-14,10,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,-19,-18,-9,9,9,9,9,9,9,10
-10,9,9,9,9,9,9,9,9,18,30,28,28,30,30,28,28,30,28,30,28,30,28,28,30,-27,-9,-9,9,9,9,9,9,9,10
-10,9,9,9,9,9,9,9,9,9,9,9,14,9,14,9,14,9,9,9,-14,14,9,9,-14,9,-9,-9,9,9,9,9,9,9,10
-10,9,9,9,9,9,9,9,-15,-15,15,15,15,15,15,15,15,14,15,15,15,15,15,15,15,15,-9,-9,9,9,9,9,9,9,10
    </qg:tilemap>

    <qg:instance prefab="LiftUp" x="1568" y="1114" />
    <qg:instance prefab="LiftSlow" x="740" y="1349" />
    <qg:instance prefab="Ledge" x="1379" y="839" gd:rotation="0.355618" />
    <qg:sprite sheet="platform" frame="0" x="1292.2" y="818" gd:rotation="0.109325" gd:z_index="-1" />

    <qg:instance prefab="Coin" x="1468" y="1314" />
    <qg:instance prefab="Coin" x="1498" y="1314" />
    <qg:instance prefab="Coin" x="1528" y="1314" />
    <qg:instance prefab="Coin" x="922" y="747" />
    <qg:instance prefab="Coin" x="952" y="747" />
    <qg:instance prefab="Coin" x="982" y="747" />
    <qg:instance prefab="Coin" x="968" y="1314" />
    <qg:instance prefab="Coin" x="998" y="1314" />
    <qg:instance prefab="Coin" x="1028" y="1314" />
    <qg:instance prefab="Coin" x="1075" y="1298" />
    <qg:instance prefab="Coin" x="1105" y="1288" />
    <qg:instance prefab="Coin" x="1135" y="1298" />
    <qg:instance prefab="Coin" x="1221" y="1036" />
    <qg:instance prefab="Coin" x="1251" y="1026" />
    <qg:instance prefab="Coin" x="1281" y="1036" />
    <qg:instance prefab="Coin" x="890" y="1110" />
    <qg:instance prefab="Coin" x="920" y="1100" />
    <qg:instance prefab="Coin" x="950" y="1110" />
    <qg:instance prefab="Coin" x="1362" y="1036" />
    <qg:instance prefab="Coin" x="1392" y="1026" />
    <qg:instance prefab="Coin" x="1422" y="1036" />

    <qg:instance prefab="Enemy" x="1312" y="1059" />
    <qg:instance prefab="Enemy" x="1260" y="1314" />
    <qg:instance prefab="Enemy" x="1163" y="757" />

    <qg:character id="robot" controller="platformer" sheet="robot" frame="30" scale="0.8"
                  x="858" y="1329" hitbox="34x44"
                  run-speed="300" accel="1800" jump-speed="725" gravity="2100" max-fall="700"
                  coyote-frames="0" air-jumps="1" air-jump-boost="2.5" jump-cut="0.6"
                  jump-sound="jump"
                  fire-action="shoot" fire-prefab="Bullet" fire-every="18" fire-sound="shoot">
      <qg:animation name="idle" frames="30,31,32,33" fps="8" />
      <qg:animation name="walk" frames="0,1,2,3,4,5,6,7,8,9" fps="16" />
      <qg:animation name="jump" frames="45" />
      <qg:animation name="fall" frames="48" />

      <qg:on-collision with="coin">
        <qg:destroy target="other" />
        <qg:play sound="coin" />
        <q:set name="coins" value="{coins + 1}" />
      </qg:on-collision>
    </qg:character>

    <!-- The camera stays inside the level's walls, a little below the robot. -->
    <qg:camera follow="robot" bounds="none" gd:offset="0,39"
               gd:limit_left="53" gd:limit_top="454" gd:limit_right="2193" gd:limit_bottom="1394" />

    <qg:hud position="top-left" size="24">
      <qg:counter bind="coins" label="COINS" />
    </qg:hud>

    <!-- Escape pauses and resumes; while paused, the menu. -->
    <qg:on-input action="pause">
      <q:if condition="{paused()}">
        <qg:resume />
      <q:else>
        <qg:pause />
      </q:else>
      </q:if>
    </qg:on-input>

    <qg:menu if="{paused()}" size="24">
      <qg:button label="Resume">
        <qg:resume />
      </qg:button>
      <qg:button label="Restart">
        <qg:goto-scene name="level" />
      </qg:button>
    </qg:menu>
  </qg:scene>

</q:application>
