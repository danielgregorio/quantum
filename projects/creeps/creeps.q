<q:application id="creeps" type="game">

  <!-- Creeps: Godot's own "Dodge the Creeps" demo (godotengine/godot-demo-projects,
       2d/dodge_the_creeps, MIT — the game of the "Your first 2D game" tutorial)
       transcribed into the game language. README.md next to this file maps each
       piece of the original to its tag and lists what the language had to grow.
       The art, music and font are the demo's (assets/LICENSE.md). -->

  <q:set name="score" value="0" type="number" />

  <qg:spritesheet name="player" src="assets/player.png" tile="112x136" />
  <qg:spritesheet name="creeps" src="assets/creeps.png" tile="100x140" />

  <qg:sound name="music" src="assets/music.ogg" loop="true" />
  <qg:sound name="death" src="assets/gameover.wav" />

  <qg:input action="jump" keys="Space, Enter, JoyA, JoyStart" />

  <!-- Three kinds of creep: each flies straight at a speed of its own, turned to
       face where it goes, and is gone once off the screen. -->
  <qg:prefab name="Flyer" tag="creep" sheet="creeps" frame="0" hitbox="75x56" ai="fly" speed="150..250" rotate="true">
    <qg:animation name="walk" frames="0, 1" fps="3" />
  </qg:prefab>
  <qg:prefab name="Swimmer" tag="creep" sheet="creeps" frame="2" hitbox="75x56" ai="fly" speed="150..250" rotate="true">
    <qg:animation name="walk" frames="2, 3" fps="4" />
  </qg:prefab>
  <qg:prefab name="Walker" tag="creep" sheet="creeps" frame="4" hitbox="75x56" ai="fly" speed="150..250" rotate="true">
    <qg:animation name="walk" frames="4, 5" fps="4" />
  </qg:prefab>

  <qg:scene name="title" width="480" height="720" background="#385f61">
    <q:set name="message" value="Dodge the&#10;Creeps" />
    <q:set name="start" value="Start" />
    <qg:hud position="center" font="fonts/Xolonium-Regular.ttf" size="60">
      <qg:text bind="message" />
      <qg:text bind="start" />
    </qg:hud>
    <qg:on-input action="jump">
      <qg:goto-scene name="play" />
    </qg:on-input>
  </qg:scene>

  <!-- Two seconds of "Get Ready", then a creep every half second from a random
       point on the border, headed in at up to 45° off straight, and a point a
       second. Touching a creep ends the run. -->
  <qg:scene name="play" width="480" height="720" background="#385f61" seed="7">
    <q:set name="score" value="0" />
    <q:set name="message" value="Get Ready" />
    <qg:play sound="music" />
    <qg:hud position="top-center" font="fonts/Xolonium-Regular.ttf" size="60">
      <qg:counter bind="score" />
    </qg:hud>
    <qg:hud position="center" font="fonts/Xolonium-Regular.ttf" size="60">
      <qg:text bind="message" />
    </qg:hud>
    <qg:character id="player" controller="topdown" sheet="player" frame="0" x="240" y="450" hitbox="54x68"
                  speed="400" bounds="scene">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="0, 1" fps="5" />
      <qg:animation name="walk-up" frames="2, 3" fps="5" />
      <qg:on-collision with="creep">
        <qg:stop sound="music" />
        <qg:play sound="death" />
        <qg:goto-scene name="over" />
      </qg:on-collision>
    </qg:character>
    <qg:timer after="120">
      <q:set name="message" value="" />
    </qg:timer>
    <qg:spawner prefab="Flyer, Swimmer, Walker" along="edges" heading="inward" spread="45" from="120" every="30" count="0" />
    <qg:timer every="60" from="120">
      <q:set name="score" value="{score + 1}" />
    </qg:timer>
  </qg:scene>

  <!-- "Game Over" for two seconds, the title for one more, then the start line;
       the score stays on the screen. -->
  <qg:scene name="over" width="480" height="720" background="#385f61">
    <q:set name="message" value="Game Over" />
    <q:set name="start" value="" />
    <q:set name="can_start" value="false" type="boolean" />
    <qg:hud position="top-center" font="fonts/Xolonium-Regular.ttf" size="60">
      <qg:counter bind="score" />
    </qg:hud>
    <qg:hud position="center" font="fonts/Xolonium-Regular.ttf" size="60">
      <qg:text bind="message" />
      <qg:text bind="start" />
    </qg:hud>
    <qg:timer after="120">
      <q:set name="message" value="Dodge the&#10;Creeps" />
    </qg:timer>
    <qg:timer after="180">
      <q:set name="start" value="Start" />
      <q:set name="can_start" value="true" />
    </qg:timer>
    <qg:on-input action="jump">
      <q:if condition="{can_start}">
        <qg:goto-scene name="play" />
      </q:if>
    </qg:on-input>
  </qg:scene>

</q:application>
