<q:application id="towers" type="game">

  <!-- Towers: the "Godot 4 Tower Defense Template" (github.com/ape1121, MIT)
       transcribed into the game language, with its map, dinos and turrets
       (assets/LICENSE.md). README.md next to this file maps the original to
       its tags and lists what the language had to grow. Two players can
       build on the same map over the network (qg:multiplayer). -->

  <q:set name="gold" value="100" type="number" />
  <q:set name="base_hp" value="10" type="number" />
  <q:set name="wave" value="0" type="number" />

  <qg:spritesheet name="map" src="assets/map.png" tile="1156x745" />
  <qg:spritesheet name="gatling" src="assets/gatling.png" tile="96" />
  <qg:spritesheet name="explosive" src="assets/explosive.png" tile="32" />
  <qg:spritesheet name="bullet" src="assets/bullet1.png" tile="16" />
  <qg:spritesheet name="red" src="assets/dino1.png" tile="48" />
  <qg:spritesheet name="blue" src="assets/dino2.png" tile="48" />
  <qg:spritesheet name="yellow" src="assets/dino3.png" tile="48" />
  <qg:spritesheet name="green" src="assets/dino4.png" tile="48" />

  <qg:input action="buy-gatling" keys="1" />
  <qg:input action="buy-explosive" keys="2" />
  <qg:multiplayer players="2" delay="3" start="map" />

  <!-- The gatling shoots a bullet at the nearest dino in range every half
       second; upgraded, twice as often. The explosive hurts every dino in
       reach every second. -->
  <qg:prefab name="Bullet" tag="bullet" sheet="bullet" frame="0" hitbox="12x12" ai="fly" speed="200" lifetime="90" rotate="true">
    <qg:animation name="walk" frames="0, 1, 2, 3, 4, 5" fps="12" />
    <qg:on-collision with="dino">
      <qg:damage target="other" amount="10" />
      <qg:destroy target="me" />
    </qg:on-collision>
  </qg:prefab>
  <qg:prefab name="Gatling" tag="tower" sheet="gatling" frame="0" hitbox="48x48" ai="turret" targets="dino"
             range="200" fire-prefab="Bullet" fire-every="30" rotate="true">
    <qg:state name="level1" initial="true" />
    <qg:state name="level2" fire-every="15" />
  </qg:prefab>
  <qg:prefab name="Explosive" tag="tower" sheet="explosive" frame="0" hitbox="32x32" ai="turret" targets="dino"
             range="100" attack="area" damage="5" fire-every="60">
    <qg:state name="level1" initial="true" />
    <qg:state name="level2" fire-every="40" />
  </qg:prefab>

  <!-- Four dinos, as the template has them: health, speed (100 px/s per unit),
       what one costs the base at the end of the road, what it pays when it dies. -->
  <qg:prefab name="RedDino" tag="dino" sheet="red" frame="4" hitbox="26x26" ai="path" speed="100" health="10">
    <qg:animation name="walk" frames="4, 5, 6, 7, 8, 9" fps="10" />
    <qg:on-collision with="base"><q:set name="base_hp" value="{base_hp - 5}" /><qg:destroy target="me" /></qg:on-collision>
    <qg:on-death><q:set name="gold" value="{gold + 10}" /></qg:on-death>
  </qg:prefab>
  <qg:prefab name="BlueDino" tag="dino" sheet="blue" frame="4" hitbox="26x26" ai="path" speed="200" health="5">
    <qg:animation name="walk" frames="4, 5, 6, 7, 8, 9" fps="10" />
    <qg:on-collision with="base"><q:set name="base_hp" value="{base_hp - 5}" /><qg:destroy target="me" /></qg:on-collision>
    <qg:on-death><q:set name="gold" value="{gold + 10}" /></qg:on-death>
  </qg:prefab>
  <qg:prefab name="YellowDino" tag="dino" sheet="yellow" frame="4" hitbox="26x26" ai="path" speed="500" health="10">
    <qg:animation name="walk" frames="4, 5, 6, 7, 8, 9" fps="10" />
    <qg:on-collision with="base"><q:set name="base_hp" value="{base_hp - 1}" /><qg:destroy target="me" /></qg:on-collision>
    <qg:on-death><q:set name="gold" value="{gold + 10}" /></qg:on-death>
  </qg:prefab>
  <qg:prefab name="GreenDino" tag="dino" sheet="green" frame="4" hitbox="26x26" ai="path" speed="1000" health="10">
    <qg:animation name="walk" frames="4, 5, 6, 7, 8, 9" fps="10" />
    <qg:on-collision with="base"><q:set name="base_hp" value="{base_hp - 1}" /><qg:destroy target="me" /></qg:on-collision>
    <qg:on-death><q:set name="gold" value="{gold + 10}" /></qg:on-death>
  </qg:prefab>

  <!-- The title: alone, or two builders on two machines. -->
  <qg:scene name="title" width="1152" height="648" background="#1a1a1a">
    <qg:sprite sheet="map" x="578" y="372" gd:modulate="#ffffff60" />
    <qg:hud position="top-center" size="48"><qg:text value="{'TOWERS'}" /></qg:hud>
    <qg:lobby local="map" local-label="Play alone" size="22" />
  </qg:scene>

  <qg:scene name="map" width="1152" height="648" background="#1a1a1a" seed="11">
    <q:set name="gold" value="100" />
    <q:set name="base_hp" value="10" />
    <q:set name="wave" value="0" />
    <q:set name="to_spawn" value="0" type="number" />
    <q:set name="kinds" value="1" type="number" />
    <q:set name="enemies" value="0" type="number" />
    <q:set name="choice" value="Gatling" />
    <q:set name="status" value="1: Gatling (50)   2: Explosive (70)   click a cell to build, click a tower to upgrade (50)" />

    <qg:sprite sheet="map" x="578" y="372" />
    <qg:path name="road" points="508,645; 522,498; 857,490; 870,210; 733,200; 716,380; 183,390; 186,537; 372,552; 381,86; 570,93; 562,264; -1,265" />
    <qg:zone name="base" tag="base" x="-40" y="235" width="40" height="60" />
    <!-- where the road is, no tower goes -->
    <qg:zone name="road-1" tag="road" x="480" y="470" width="400" height="60" />
    <qg:zone name="road-2" tag="road" x="840" y="180" width="60" height="330" />
    <qg:zone name="road-3" tag="road" x="700" y="170" width="200" height="60" />
    <qg:zone name="road-4" tag="road" x="690" y="170" width="60" height="240" />
    <qg:zone name="road-5" tag="road" x="160" y="360" width="590" height="60" />
    <qg:zone name="road-6" tag="road" x="160" y="360" width="60" height="210" />
    <qg:zone name="road-7" tag="road" x="160" y="520" width="240" height="60" />
    <qg:zone name="road-8" tag="road" x="350" y="60" width="60" height="520" />
    <qg:zone name="road-9" tag="road" x="350" y="60" width="250" height="60" />
    <qg:zone name="road-10" tag="road" x="540" y="60" width="60" height="230" />
    <qg:zone name="road-11" tag="road" x="0" y="235" width="590" height="60" />
    <qg:zone name="road-12" tag="road" x="480" y="480" width="60" height="170" />

    <qg:cursor player="1" grid="48" sheet="explosive" frame="0" gd:modulate="#ffffff80" />
    <qg:cursor player="2" grid="48" sheet="explosive" frame="0" gd:modulate="#80c0ff80" />

    <qg:on-input action="buy-gatling"><q:set name="choice" value="Gatling" /></qg:on-input>
    <qg:on-input action="buy-explosive"><q:set name="choice" value="Explosive" /></qg:on-input>

    <!-- A click: on a tower, its upgrade; on free ground, the chosen tower, if the gold is there. -->
    <qg:on-select>
      <q:if condition="{other != null and other.tag == 'tower' and gold >= 50 and other.state == 'level1'}">
        <q:set name="gold" value="{gold - 50}" />
        <qg:become target="other" state="level2" />
      </q:if>
      <q:if condition="{other == null and thing_at('road', cursor.x, cursor.y) == null}">
        <q:if condition="{choice == 'Gatling' and gold >= 50}">
          <q:set name="gold" value="{gold - 50}" />
          <qg:spawn prefab="Gatling" at="cursor" />
        </q:if>
        <q:if condition="{choice == 'Explosive' and gold >= 70}">
          <q:set name="gold" value="{gold - 70}" />
          <qg:spawn prefab="Explosive" at="cursor" />
        </q:if>
      </q:if>
    </qg:on-select>

    <!-- Waves: ten of them, each 5 + 3 × wave dinos, a new kind every two
         waves; the next starts five seconds after the last dino of this one
         is gone. A dino every 0.2 s while the wave has some to send. -->
    <qg:timer every="300">
      <q:if condition="{to_spawn == 0 and enemies == 0 and base_hp > 0}">
        <q:if condition="{wave >= 10}">
          <qg:goto-scene name="won" />
        <q:else>
          <q:set name="wave" value="{wave + 1}" />
          <q:set name="to_spawn" value="{5 + 3 * wave}" />
          <q:set name="kinds" value="{min(4, 1 + wave // 2)}" />
        </q:else>
        </q:if>
      </q:if>
    </qg:timer>
    <qg:timer every="12">
      <q:if condition="{to_spawn > 0}">
        <q:set name="to_spawn" value="{to_spawn - 1}" />
        <q:set name="kind" value="{int(random(0, kinds))}" />
        <q:if condition="{kind == 0}"><qg:spawn prefab="RedDino" at="path" path="road" /></q:if>
        <q:if condition="{kind == 1}"><qg:spawn prefab="BlueDino" at="path" path="road" /></q:if>
        <q:if condition="{kind == 2}"><qg:spawn prefab="YellowDino" at="path" path="road" /></q:if>
        <q:if condition="{kind >= 3}"><qg:spawn prefab="GreenDino" at="path" path="road" /></q:if>
      </q:if>
    </qg:timer>
    <q:set name="kind" value="0" type="number" />
    <qg:timer every="1">
      <q:set name="enemies" value="{count('dino')}" />
      <q:if condition="{base_hp <= 0}"><qg:goto-scene name="lost" /></q:if>
    </qg:timer>

    <qg:hud position="top-left" size="20">
      <qg:counter bind="gold" label="Gold" />
      <qg:counter bind="base_hp" label="Base" />
      <qg:counter bind="wave" label="Wave" />
      <qg:counter bind="enemies" label="Dinos" />
      <qg:text bind="choice" />
      <qg:text bind="status" />
    </qg:hud>
  </qg:scene>

  <qg:scene name="won" width="1152" height="648" background="#1a3a1a">
    <q:set name="message" value="The base stands. Press space to play again." />
    <qg:hud position="center" size="40"><qg:text bind="message" /><qg:counter bind="gold" label="Gold left" /></qg:hud>
    <qg:on-input action="jump"><qg:goto-scene name="map" /></qg:on-input>
  </qg:scene>
  <qg:scene name="lost" width="1152" height="648" background="#3a1a1a">
    <q:set name="message" value="The base fell. Press space to try again." />
    <qg:hud position="center" size="40"><qg:text bind="message" /><qg:counter bind="wave" label="Reached wave" /></qg:hud>
    <qg:on-input action="jump"><qg:goto-scene name="map" /></qg:on-input>
  </qg:scene>

</q:application>
