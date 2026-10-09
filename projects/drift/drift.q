<q:application id="drift" type="game">

  <!-- Drift: the vertical shooter that drives the game language (PLAN_GAMES_2.md).
       A ship at the bottom of the screen, three waves of drones and tanks that
       come down and shoot, then a boss with two phases; lives, score, and a high
       score kept between runs. Art and sounds: Kenney's Pixel Platformer (CC0),
       pressed into service as spaceships. -->

  <q:set name="score" value="0" type="number" />
  <q:set name="lives" value="3" type="number" />
  <q:set name="high_score" value="0" type="number" saved="true" />

  <qg:tileset name="kenney" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="chars" src="assets/kenney/tilemap-characters_packed.png" tile="24" />

  <qg:sound name="shoot" src="assets/kenney/audio/jump.ogg" />
  <qg:sound name="hit" src="assets/kenney/audio/stomp.ogg" />
  <qg:sound name="boom" src="assets/kenney/audio/block.ogg" />
  <qg:sound name="hurt" src="assets/kenney/audio/hurt.ogg" />
  <qg:sound name="win" src="assets/kenney/audio/win.ogg" />

  <!-- The ship's shot: flies up, gone after 80 ticks or when it leaves the screen. -->
  <qg:prefab name="Shot" tag="shot" sheet="kenney" frame="151" hitbox="18x8"
             ai="fly" heading="up" speed="240" lifetime="80">
    <qg:on-collision with="enemy">
      <qg:damage target="other" amount="1" />
      <qg:destroy target="me" />
    </qg:on-collision>
    <qg:on-collision with="boss">
      <qg:damage target="other" amount="1" />
      <qg:destroy target="me" />
    </qg:on-collision>
  </qg:prefab>

  <qg:prefab name="EnemyShot" tag="enemy-shot" sheet="kenney" frame="128" hitbox="6x6"
             ai="fly" heading="down" speed="120" lifetime="150" />

  <!-- A drone: comes straight down, one hit. -->
  <qg:prefab name="Drone" tag="enemy" sheet="chars" frame="18" hitbox="14x14"
             ai="fly" heading="down" speed="45" lifetime="400" health="1">
    <qg:animation name="walk" frames="18,19,20" fps="6" />
    <qg:on-death>
      <qg:play sound="boom" />
      <qg:burst at="me" color="#ffcc44" count="10" />
      <q:set name="score" value="{score + 100}" />
    </qg:on-death>
  </qg:prefab>

  <!-- A tank: slow, three hits, shoots. -->
  <qg:prefab name="Tank" tag="enemy" sheet="chars" frame="24" hitbox="16x16"
             ai="fly" heading="down" speed="20" lifetime="900" health="3"
             fire-prefab="EnemyShot" fire-every="90">
    <qg:animation name="walk" frames="24,25,26" fps="4" />
    <qg:on-damage>
      <qg:play sound="hit" />
    </qg:on-damage>
    <qg:on-death>
      <qg:play sound="boom" />
      <qg:burst at="me" color="#ff6644" count="16" />
      <q:set name="score" value="{score + 300}" />
    </qg:on-death>
  </qg:prefab>

  <!-- The boss: sways across the top, twenty hits; angry below half. -->
  <qg:prefab name="Boss" tag="boss" sheet="chars" frame="9" hitbox="20x20"
             ai="sway" speed="30" health="12" fire-prefab="EnemyShot" fire-every="90">
    <qg:state name="calm" frame="9" speed="30" fire-every="90" initial="true" />
    <qg:state name="angry" frame="12" speed="70" fire-every="60" />
    <qg:on-damage>
      <qg:play sound="hit" />
      <q:if condition="{me.health <= 6 and me.state == 'calm'}">
        <qg:become target="me" state="angry" />
      </q:if>
    </qg:on-damage>
    <qg:on-death>
      <qg:play sound="win" />
      <qg:burst at="me" color="#ffffff" count="40" />
      <qg:shake at="me" frames="20" strength="4" />
      <q:set name="score" value="{score + 5000}" />
    </qg:on-death>
  </qg:prefab>

  <qg:scene name="play" width="256" height="224" background="#0a0a1e" seed="3">
    <q:set name="message" value="" />
    <q:set name="boss_down" value="false" type="boolean" />

    <q:function name="hurt" params="me">
      <qg:play sound="hurt" />
      <qg:shake at="me" frames="10" strength="3" />
      <q:set name="lives" value="{lives - 1}" />
      <q:if condition="{lives <= 0}">
        <qg:goto-scene name="game-over" />
      </q:if>
    </q:function>

    <qg:character id="ship" controller="ship" sheet="chars" frame="6" x="128" y="196" hitbox="12x12"
                  speed="120" bounds="scene"
                  fire-action="jump" fire-prefab="Shot" fire-every="8" fire-sound="shoot">
      <qg:animation name="idle" frames="6" />
      <qg:on-collision with="enemy" cooldown="90">
        <qg:destroy target="other" />
        <q:call function="hurt" args="me" />
      </qg:on-collision>
      <qg:on-collision with="enemy-shot" cooldown="90">
        <qg:destroy target="other" />
        <q:call function="hurt" args="me" />
      </qg:on-collision>
      <qg:on-collision with="boss" cooldown="90">
        <q:call function="hurt" args="me" />
      </qg:on-collision>
    </qg:character>

    <!-- Three waves, then the boss. x="random" is from the scene's seed. -->
    <qg:spawner prefab="Drone" from="60" every="40" count="8" x="random" y="-12" />
    <qg:spawner prefab="Tank" from="500" every="120" count="3" x="random" y="-12" />
    <qg:spawner prefab="Drone" from="900" every="25" count="12" x="random" y="-12" />
    <qg:spawner prefab="Tank" from="950" every="150" count="2" x="random" y="-12" />
    <qg:spawner prefab="Boss" from="1500" every="1" count="1" x="128" y="40" />
    <qg:timer after="1440">
      <q:set name="message" value="HERE IT COMES" />
    </qg:timer>

    <qg:on-death of="boss">
      <q:set name="boss_down" value="true" />
      <q:set name="message" value="THE DRIFT IS CLEAR" />
      <qg:goto-scene name="victory" />
    </qg:on-death>

    <qg:hud position="top-left">
      <qg:counter bind="score" label="SCORE" />
      <qg:counter bind="lives" label="LIVES" />
      <qg:counter bind="high_score" label="HIGH" />
      <qg:text bind="message" />
    </qg:hud>
  </qg:scene>

  <qg:scene name="victory" width="256" height="224" background="#102040">
    <q:set name="title" value="THE DRIFT IS CLEAR. PRESS JUMP." />
    <q:if condition="{score > high_score}">
      <q:set name="high_score" value="{score}" />
    </q:if>
    <qg:on-input action="jump">
      <q:set name="score" value="0" />
      <q:set name="lives" value="3" />
      <qg:goto-scene name="play" />
    </qg:on-input>
    <qg:hud position="top-center">
      <qg:text bind="title" />
      <qg:counter bind="score" label="SCORE" />
      <qg:counter bind="high_score" label="HIGH" />
    </qg:hud>
  </qg:scene>

  <qg:scene name="game-over" width="256" height="224" background="#000000">
    <q:set name="title" value="LOST IN THE DRIFT. PRESS JUMP." />
    <q:if condition="{score > high_score}">
      <q:set name="high_score" value="{score}" />
    </q:if>
    <qg:on-input action="jump">
      <q:set name="score" value="0" />
      <q:set name="lives" value="3" />
      <qg:goto-scene name="play" />
    </qg:on-input>
    <qg:hud position="top-center">
      <qg:text bind="title" />
      <qg:counter bind="score" label="SCORE" />
      <qg:counter bind="high_score" label="HIGH" />
    </qg:hud>
  </qg:scene>

</q:application>
