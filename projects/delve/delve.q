<q:application id="delve" type="game">

  <!-- Delve: a dungeon crawl for one delver, or two over the network.
       Three crypts, down and down: a wall a lever opens (qg:set-tile), and
       the skeletons behind it that find their way through as soon as it does
       (ai="pathfind"); crushers that slide to and fro (qg:tween); a vault
       two levers keep shut, and its treasure. Torches burn and gems sparkle
       (qg:particles). A skeleton archer, made of parts, keeps its distance and
       shoots. The hearts and the gems are what the delvers carry
       (qg:item), shown by the HUD's inventory. Each crypt entered is saved (Continue, alone); the
       game speaks English, Portuguese and Spanish. The art is drawn for it by
       scripts/art/delve.py and the music written by scripts/art/delve_music.py
       (CC0); the sounds are Kenney's (CC0). -->

  <!-- The delve's state, kept from crypt to crypt; the first crypt starts it anew. -->
  <q:set name="message" value="" />
  <!-- a hurt, the same in every crypt: a function of the game -->
  <q:function name="hurt" params="me">
    <qg:play sound="hurt" vary="0.1" />
    <qg:shake at="me" frames="8" strength="2" />
    <qg:take item="heart" />
    <q:if condition="{held('heart') <= 0}">
      <qg:goto-scene name="fallen" fade="0.6" />
    </q:if>
  </q:function>

  <!-- Two players, each on their own machine: the delve starts in crypt-1 once both are there. -->
  <qg:multiplayer players="2" start="crypt-1" />

  <!-- 1 is the floor and 12 the rubble of a wall broken open (walked on); 2 the wall, 3 a wall with a torch. -->
  <qg:tileset name="crypt" src="assets/crypt.png" tile="18">
    <qg:tile frame="0" shape="none" />
    <qg:tile frame="11" shape="none" />
  </qg:tileset>
  <qg:spritesheet name="delvers" src="assets/delvers.png" tile="24" />

  <qg:sound name="hit" src="assets/kenney/audio/stomp.ogg" />
  <qg:sound name="hurt" src="assets/kenney/audio/hurt.ogg" />
  <qg:sound name="pick" src="assets/kenney/audio/coin.ogg" />
  <qg:sound name="heal" src="assets/kenney/audio/powerup.ogg" />
  <qg:sound name="open" src="assets/kenney/audio/block.ogg" />
  <qg:sound name="win" src="assets/kenney/audio/win.ogg" />
  <qg:sound name="twang" src="assets/kenney/audio/jump.ogg" />
  <qg:sound name="torchlight" src="assets/torchlight.ogg" loop="true" />
  <qg:sound name="crypt" src="assets/crypt.ogg" loop="true" />

  <!-- effects: only seen, the game's state never depends on them -->
  <qg:particles name="torch" preset="fire" amount="20" size="3" lifetime="0.7" speed="30" />
  <qg:particles name="sparkle" preset="stars" color="#a8f0ff" />
  <qg:particles name="glow" preset="sparks" color="#ff8098" amount="12" />
  <qg:particles name="slain" preset="smoke" color="#c8c0b0" />
  <qg:particles name="rumble" preset="dust" color="#8a8098" amount="30" speed="60" size="3" />
  <qg:particles name="treasure" preset="confetti" />
  <qg:particles name="dust" preset="snow" color="#6a6478" amount="16" speed="8" size="1" />

  <!-- What the delvers carry, kept from crypt to crypt and in a save: hearts (five at most; one
       less at each wound, and none is the fall) and gems. A heart picked up at five stays where it is. -->
  <qg:item name="heart" label="HEARTS" sheet="crypt" frame="6" start="5" max="5" sound="heal" particles="glow" />
  <qg:item name="gem" label="GEMS" sheet="crypt" frame="5" sound="pick" particles="sparkle" />

  <qg:prefab name="Gem" tag="gem" sheet="crypt" frame="5" hitbox="10x12" gives="gem" />
  <qg:prefab name="Heart" tag="heart" sheet="crypt" frame="6" hitbox="12x12" gives="heart" />
  <qg:prefab name="Lever" tag="lever" sheet="crypt" frame="3" hitbox="14x14" />
  <qg:prefab name="LeverOn" tag="lever-on" sheet="crypt" frame="4" hitbox="14x14" />
  <qg:prefab name="Stairs" tag="stairs" sheet="crypt" frame="8" hitbox="10x10" />
  <qg:prefab name="Slab" tag="slab" sheet="crypt" frame="9" hitbox="16x16" />
  <qg:prefab name="Chest" tag="chest" sheet="crypt" frame="7" hitbox="16x16" />

  <qg:prefab name="Skeleton" tag="enemy" sheet="delvers" frame="20" hitbox="12x14"
             ai="pathfind" speed="30" sight="400">
    <qg:animation name="walk" frames="20,21,20,22" fps="6" />
  </qg:prefab>
  <!-- a slain skeleton falls to a heap of bones, once, and the heap goes up in smoke -->
  <qg:prefab name="Fallen" tag="fallen" sheet="delvers" frame="26" hitbox="8x8">
    <qg:animation name="walk" frames="26,27,28,28,28" fps="8" loop="false" />
    <qg:on-animation-end name="walk">
      <qg:emit particles="slain" at="me" />
      <qg:destroy target="me" />
    </qg:on-animation-end>
  </qg:prefab>
  <!-- a bat flutters about until it sees a delver, then dives at it -->
  <qg:prefab name="Bat" tag="enemy" sheet="delvers" frame="23" hitbox="14x12"
             ai="behavior" speed="42" sight="110">
    <qg:animation name="walk" frames="23,24,25,24" fps="10" />
    <qg:behavior>
      <qg:seek way="straight" />
      <qg:wander speed="16" />
    </qg:behavior>
  </qg:prefab>
  <!-- an enemy made of parts: it keeps its distance from the nearest delver it sees, shoots
       at one within range, and wanders while it sees none -->
  <qg:prefab name="Archer" tag="enemy" sheet="delvers" frame="29" hitbox="12x14"
             ai="behavior" speed="26" sight="150">
    <qg:animation name="walk" frames="29,30,29,31" fps="6" />
    <qg:behavior>
      <qg:keep-distance min="54" max="90" />
      <qg:shoot prefab="Arrow" every="90" range="130" sound="twang" />
      <qg:wander speed="12" />
    </qg:behavior>
  </qg:prefab>
  <qg:prefab name="Arrow" tag="arrow" sheet="delvers" frame="32" hitbox="6x4"
             ai="fly" speed="100" walls="stop" rotate="true" lifetime="180" />

  <!-- the game in Portuguese and Spanish (a web page's ?lang=pt, the command line's q-lang, or the system's language) -->
  <qg:language lang="pt" name="Português">
    <qg:phrase text="HEARTS" as="CORAÇÕES" />
    <qg:phrase text="GEMS" as="GEMAS" />
    <qg:phrase text="Play alone" as="Jogar sozinho" />
    <qg:phrase text="Play together" as="Jogar junto" />
    <qg:phrase text="Continue" as="Continuar" />
    <qg:phrase text="Language" as="Idioma" />
    <qg:phrase text="Try again" as="Tentar de novo" />
    <qg:phrase text="To the title" as="Voltar ao início" />
    <qg:phrase text="DOWN TO THE VAULT, ALONE OR WITH A FRIEND" as="ATÉ O COFRE, SOZINHO OU COM UM AMIGO" />
    <qg:phrase text="TWO DELVERS, TWO MACHINES. ESCAPE: BACK." as="DOIS EXPLORADORES, DUAS MÁQUINAS. ESC: VOLTAR." />
    <qg:phrase text="A SEALED WALL. A LEVER MUST OPEN IT." as="UMA PAREDE SELADA. UMA ALAVANCA DEVE ABRI-LA." />
    <qg:phrase text="THE WALL OPENS. THE DEAD WAKE." as="A PAREDE SE ABRE. OS MORTOS DESPERTAM." />
    <qg:phrase text="THE CRUSHERS. MIND THEIR TIME." as="OS ESMAGADORES. ATENÇÃO AO TEMPO DELES." />
    <qg:phrase text="THE VAULT. TWO LEVERS HOLD IT SHUT." as="O COFRE. DUAS ALAVANCAS O MANTÊM FECHADO." />
    <qg:phrase text="ONE MORE LEVER." as="FALTA UMA ALAVANCA." />
    <qg:phrase text="THE VAULT IS OPEN." as="O COFRE ESTÁ ABERTO." />
    <qg:phrase text="THE VAULT IS YOURS." as="O COFRE É SEU." />
    <qg:phrase text="THE CRYPT KEEPS YOU." as="A CRIPTA FICA COM VOCÊ." />
  </qg:language>
  <qg:language lang="es" name="Español">
    <qg:phrase text="HEARTS" as="CORAZONES" />
    <qg:phrase text="GEMS" as="GEMAS" />
    <qg:phrase text="Play alone" as="Jugar solo" />
    <qg:phrase text="Play together" as="Jugar juntos" />
    <qg:phrase text="Continue" as="Continuar" />
    <qg:phrase text="Language" as="Idioma" />
    <qg:phrase text="Try again" as="Intentar de nuevo" />
    <qg:phrase text="To the title" as="Volver al inicio" />
    <qg:phrase text="DOWN TO THE VAULT, ALONE OR WITH A FRIEND" as="HASTA LA BÓVEDA, SOLO O CON UN AMIGO" />
    <qg:phrase text="TWO DELVERS, TWO MACHINES. ESCAPE: BACK." as="DOS EXPLORADORES, DOS MÁQUINAS. ESC: VOLVER." />
    <qg:phrase text="A SEALED WALL. A LEVER MUST OPEN IT." as="UN MURO SELLADO. UNA PALANCA DEBE ABRIRLO." />
    <qg:phrase text="THE WALL OPENS. THE DEAD WAKE." as="EL MURO SE ABRE. LOS MUERTOS DESPIERTAN." />
    <qg:phrase text="THE CRUSHERS. MIND THEIR TIME." as="LOS APLASTADORES. CUIDA SU RITMO." />
    <qg:phrase text="THE VAULT. TWO LEVERS HOLD IT SHUT." as="LA BÓVEDA. DOS PALANCAS LA MANTIENEN CERRADA." />
    <qg:phrase text="ONE MORE LEVER." as="FALTA UNA PALANCA." />
    <qg:phrase text="THE VAULT IS OPEN." as="LA BÓVEDA ESTÁ ABIERTA." />
    <qg:phrase text="THE VAULT IS YOURS." as="LA BÓVEDA ES TUYA." />
    <qg:phrase text="THE CRYPT KEEPS YOU." as="LA CRIPTA SE QUEDA CONTIGO." />
  </qg:language>

  <!-- ===== The title: alone, together, or the saved delve ===== -->

  <qg:scene name="title" width="256" height="224" background="#16141e">
    <qg:music sound="torchlight" />
    <qg:sprite sheet="delvers" frame="0" x="34" y="150" gd:scale="2,2" />
    <qg:sprite sheet="delvers" frame="10" x="222" y="150" gd:scale="2,2" gd:flip_h="true" />
    <qg:emitter particles="torch" x="34" y="100" />
    <qg:emitter particles="torch" x="222" y="100" />
    <qg:emitter particles="dust" x="128" y="0" width="256" />
    <qg:hud position="top-center" size="32"><qg:text value="{'DELVE'}" /></qg:hud>
    <qg:hud position="bottom-center" size="10"><qg:text value="{tr('DOWN TO THE VAULT, ALONE OR WITH A FRIEND')}" /></qg:hud>
    <qg:menu position="center">
      <qg:button label="Play alone"><qg:goto-scene name="crypt-1" fade="0.4" /></qg:button>
      <qg:button label="Play together"><qg:goto-scene name="together" /></qg:button>
      <qg:button label="Continue" if="{has_save()}"><qg:continue /></qg:button>
      <qg:button label="{tr('Language') + ': ' + language()}"><qg:next-language /></qg:button>
    </qg:menu>
  </qg:scene>

  <!-- Two machines: one hosts, the other joins its address; the delve starts in crypt-1. -->
  <qg:scene name="together" width="256" height="224" background="#16141e">
    <qg:music sound="torchlight" />
    <qg:hud position="top-center" size="10"><qg:text value="{tr('TWO DELVERS, TWO MACHINES. ESCAPE: BACK.')}" /></qg:hud>
    <qg:lobby local="crypt-1" local-label="Play alone" size="12" />
    <qg:on-input action="cancel">
      <qg:leave />
      <qg:goto-scene name="title" />
    </qg:on-input>
  </qg:scene>

  <!-- ===== Crypt 1: a sealed wall, and what waits behind it. Down the stairs to crypt 2. ===== -->

  <qg:scene name="crypt-1" width="256" height="224" background="#100e16" seed="1" save="true">
    <qg:music sound="crypt" />
    <!-- the delve starts here anew: five hearts, no gems, every gem back in its place -->
    <q:function name="anew" params=""><qg:reset-items /></q:function>
    <q:call function="anew" />
    <q:set name="message" value="A SEALED WALL. A LEVER MUST OPEN IT." />
    <q:set name="leaving" value="false" type="boolean" />

    <q:function name="slay" params="foe">
      <qg:play sound="hit" vary="0.15" />
      <qg:swap target="foe" prefab="Fallen" />
    </q:function>
    <q:function name="pull" params="lever">
      <qg:play sound="open" pitch="0.75" />
      <qg:swap target="lever" prefab="LeverOn" />
      <qg:set-tile col="8" row="5" tile="12" />
      <qg:set-tile col="8" row="6" tile="12" />
      <qg:emit particles="rumble" at="lever" dx="72" dy="-63" />
      <q:set name="message" value="THE WALL OPENS. THE DEAD WAKE." />
    </q:function>
    <q:function name="down" params="">
      <q:if condition="{not leaving}">
        <q:set name="leaving" value="true" />
        <qg:goto-scene name="crypt-2" fade="0.5" />
      </q:if>
    </q:function>

    <qg:tilemap tileset="crypt" collision="true">
2,2,2,2,2,2,2,2,2,2,2,2,2,2
2,1,1,1,1,1,1,1,2,1,1,1,1,2
2,1,1,1,1,1,1,1,3,1,1,1,1,2
3,1,1,1,1,1,1,1,2,1,1,1,1,3
2,1,1,1,1,1,1,1,2,1,1,1,1,2
2,1,1,1,1,1,1,1,2,1,1,1,1,2
2,1,1,1,1,1,1,1,2,1,1,1,1,2
2,1,1,1,1,1,1,1,2,1,1,1,1,2
3,1,1,1,1,1,1,1,2,1,1,1,1,3
2,1,1,1,1,1,1,1,2,1,1,1,1,2
2,1,1,1,1,1,1,1,2,1,1,1,1,2
2,2,2,2,2,2,2,2,2,2,2,2,2,2
    </qg:tilemap>
    <qg:emitter particles="torch" x="9" y="57" />
    <qg:emitter particles="torch" x="9" y="147" />
    <qg:emitter particles="torch" x="243" y="57" />
    <qg:emitter particles="torch" x="243" y="147" />
    <qg:emitter particles="torch" x="153" y="39" />

    <qg:character id="p1" controller="topdown" player="1" sheet="delvers" frame="0"
                  x="45" y="99" hitbox="12x14" speed="70"
                  attack-action="jump" attack-reach="16" attack-frames="12" attack-sound="hit">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1,2" fps="8" />
      <qg:animation name="walk-up" frames="3,4" fps="8" />
      <qg:animation name="walk-down" frames="5,6" fps="8" />
      <qg:animation name="attack" frames="7" />
      <qg:animation name="attack-up" frames="8" />
      <qg:animation name="attack-down" frames="9" />
      <qg:on-collision with="enemy" cooldown="60"><q:call function="hurt" args="me" /></qg:on-collision>
      <qg:on-collision with="lever"><q:call function="pull" args="other" /></qg:on-collision>
      <qg:on-collision with="stairs"><q:call function="down" /></qg:on-collision>
      <qg:on-hit with="enemy"><q:call function="slay" args="other" /></qg:on-hit>
    </qg:character>
    <qg:character id="p2" controller="topdown" player="2" sheet="delvers" frame="10"
                  x="45" y="135" hitbox="12x14" speed="70" if="{net_status() != 'offline'}"
                  attack-action="jump" attack-reach="16" attack-frames="12" attack-sound="hit">
      <qg:animation name="idle" frames="10" />
      <qg:animation name="walk" frames="11,12" fps="8" />
      <qg:animation name="walk-up" frames="13,14" fps="8" />
      <qg:animation name="walk-down" frames="15,16" fps="8" />
      <qg:animation name="attack" frames="17" />
      <qg:animation name="attack-up" frames="18" />
      <qg:animation name="attack-down" frames="19" />
      <qg:on-collision with="enemy" cooldown="60"><q:call function="hurt" args="me" /></qg:on-collision>
      <qg:on-collision with="lever"><q:call function="pull" args="other" /></qg:on-collision>
      <qg:on-collision with="stairs"><q:call function="down" /></qg:on-collision>
      <qg:on-hit with="enemy"><q:call function="slay" args="other" /></qg:on-hit>
    </qg:character>

    <qg:instance prefab="Lever" name="lever" x="81" y="171" />
    <qg:instance prefab="Gem" name="gem-1" x="99" y="45" />
    <qg:instance prefab="Gem" name="gem-2" x="117" y="153" />
    <qg:instance prefab="Gem" name="gem-3" x="225" y="45" />
    <qg:instance prefab="Skeleton" name="skeleton-1" x="190" y="72" />
    <qg:instance prefab="Skeleton" name="skeleton-2" x="190" y="144" />
    <qg:instance prefab="Stairs" name="stairs" x="225" y="171" />

    <qg:hud position="top-left" size="10">
      <qg:inventory />
      <qg:text bind="message" />
    </qg:hud>
  </qg:scene>

  <!-- ===== Crypt 2: three crushers slide across the way. Down the stairs to crypt 3. ===== -->

  <qg:scene name="crypt-2" width="256" height="224" background="#100e16" seed="2" save="true">
    <qg:music sound="crypt" />
    <q:set name="message" value="THE CRUSHERS. MIND THEIR TIME." />
    <q:set name="leaving" value="false" type="boolean" />

    <q:function name="slay" params="foe">
      <qg:play sound="hit" vary="0.15" />
      <qg:emit particles="slain" at="foe" />
      <qg:destroy target="foe" />
    </q:function>
    <q:function name="down" params="">
      <q:if condition="{not leaving}">
        <q:set name="leaving" value="true" />
        <qg:goto-scene name="crypt-3" fade="0.5" />
      </q:if>
    </q:function>

    <qg:tilemap tileset="crypt" collision="true">
2,2,2,2,2,2,2,2,2,2,2,2,2,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
3,1,1,1,1,1,1,1,1,1,1,1,1,3
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
3,1,1,1,1,1,1,1,1,1,1,1,1,3
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,2,2,2,2,2,2,2,2,2,2,2,2,2
    </qg:tilemap>
    <qg:emitter particles="torch" x="9" y="57" />
    <qg:emitter particles="torch" x="9" y="147" />
    <qg:emitter particles="torch" x="243" y="57" />
    <qg:emitter particles="torch" x="243" y="147" />

    <qg:character id="p1" controller="topdown" player="1" sheet="delvers" frame="0"
                  x="27" y="99" hitbox="12x14" speed="70"
                  attack-action="jump" attack-reach="16" attack-frames="12" attack-sound="hit">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1,2" fps="8" />
      <qg:animation name="walk-up" frames="3,4" fps="8" />
      <qg:animation name="walk-down" frames="5,6" fps="8" />
      <qg:animation name="attack" frames="7" />
      <qg:animation name="attack-up" frames="8" />
      <qg:animation name="attack-down" frames="9" />
      <qg:on-collision with="enemy" cooldown="60"><q:call function="hurt" args="me" /></qg:on-collision>
      <qg:on-collision with="slab" cooldown="60"><q:call function="hurt" args="me" /></qg:on-collision>
      <qg:on-collision with="stairs"><q:call function="down" /></qg:on-collision>
      <qg:on-hit with="enemy"><q:call function="slay" args="other" /></qg:on-hit>
    </qg:character>
    <qg:character id="p2" controller="topdown" player="2" sheet="delvers" frame="10"
                  x="27" y="135" hitbox="12x14" speed="70" if="{net_status() != 'offline'}"
                  attack-action="jump" attack-reach="16" attack-frames="12" attack-sound="hit">
      <qg:animation name="idle" frames="10" />
      <qg:animation name="walk" frames="11,12" fps="8" />
      <qg:animation name="walk-up" frames="13,14" fps="8" />
      <qg:animation name="walk-down" frames="15,16" fps="8" />
      <qg:animation name="attack" frames="17" />
      <qg:animation name="attack-up" frames="18" />
      <qg:animation name="attack-down" frames="19" />
      <qg:on-collision with="enemy" cooldown="60"><q:call function="hurt" args="me" /></qg:on-collision>
      <qg:on-collision with="slab" cooldown="60"><q:call function="hurt" args="me" /></qg:on-collision>
      <qg:on-collision with="stairs"><q:call function="down" /></qg:on-collision>
      <qg:on-hit with="enemy"><q:call function="slay" args="other" /></qg:on-hit>
    </qg:character>

    <!-- the crushers: each slides from one wall to the other and back, for ever, at its own pace -->
    <qg:instance prefab="Slab" name="slab-1" x="81" y="27" />
    <qg:instance prefab="Slab" name="slab-2" x="135" y="189" />
    <qg:instance prefab="Slab" name="slab-3" x="189" y="27" />
    <qg:timer after="1">
      <qg:tween target="slab-1" property="y" to="189" seconds="1.6" trans="sine" ease="in-out" repeat="-1" yoyo="true" />
      <qg:tween target="slab-2" property="y" to="27" seconds="1.2" trans="sine" ease="in-out" repeat="-1" yoyo="true" />
      <qg:tween target="slab-3" property="y" to="189" seconds="2" trans="sine" ease="in-out" repeat="-1" yoyo="true" />
    </qg:timer>

    <qg:instance prefab="Heart" name="heart-1" x="162" y="108" />
    <qg:instance prefab="Gem" name="gem-4" x="108" y="189" />
    <qg:instance prefab="Gem" name="gem-5" x="162" y="45" />
    <qg:instance prefab="Bat" name="bat-1" x="216" y="54" />
    <qg:instance prefab="Bat" name="bat-2" x="216" y="171" />
    <qg:instance prefab="Stairs" name="stairs" x="225" y="117" />

    <qg:hud position="top-left" size="10">
      <qg:inventory />
      <qg:text bind="message" />
    </qg:hud>
  </qg:scene>

  <!-- ===== Crypt 3: the vault, which two levers keep shut. ===== -->

  <qg:scene name="crypt-3" width="256" height="224" background="#100e16" seed="3" save="true">
    <qg:music sound="crypt" />
    <q:set name="message" value="THE VAULT. TWO LEVERS HOLD IT SHUT." />
    <q:set name="pulled" value="0" type="number" />
    <q:set name="won" value="false" type="boolean" />

    <q:function name="slay" params="foe">
      <qg:play sound="hit" vary="0.15" />
      <qg:swap target="foe" prefab="Fallen" />
    </q:function>
    <q:function name="pull" params="lever">
      <qg:play sound="open" pitch="0.75" />
      <qg:swap target="lever" prefab="LeverOn" />
      <q:set name="pulled" value="{pulled + 1}" />
      <q:if condition="{pulled == 2}">
        <qg:set-tile col="6" row="8" tile="12" />
        <qg:set-tile col="7" row="8" tile="12" />
        <qg:emit particles="rumble" at="chest" dy="-27" />
        <q:set name="message" value="THE VAULT IS OPEN." />
      <q:else>
        <q:set name="message" value="ONE MORE LEVER." />
      </q:else>
      </q:if>
    </q:function>
    <q:function name="treasure" params="it">
      <q:if condition="{not won}">
        <q:set name="won" value="true" />
        <qg:play sound="win" />
        <qg:emit particles="treasure" at="it" />
        <q:set name="message" value="THE VAULT IS YOURS." />
        <qg:goto-scene name="the-end" fade="1.5" />
      </q:if>
    </q:function>

    <qg:tilemap tileset="crypt" collision="true">
2,2,2,2,2,2,2,2,2,2,2,2,2,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
3,1,1,1,1,1,1,1,1,1,1,1,1,3
2,1,1,2,1,1,1,1,1,1,2,1,1,2
2,1,1,2,1,1,1,1,1,1,2,1,1,2
2,1,1,2,1,1,1,1,1,1,2,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,2,2,2,2,3,2,2,3,2,2,2,2,2
2,2,2,2,2,1,1,1,1,2,2,2,2,2
2,2,2,2,2,1,1,1,1,2,2,2,2,2
2,2,2,2,2,2,2,2,2,2,2,2,2,2
    </qg:tilemap>
    <qg:emitter particles="torch" x="9" y="57" />
    <qg:emitter particles="torch" x="243" y="57" />
    <qg:emitter particles="torch" x="99" y="147" />
    <qg:emitter particles="torch" x="153" y="147" />

    <qg:character id="p1" controller="topdown" player="1" sheet="delvers" frame="0"
                  x="45" y="45" hitbox="12x14" speed="70"
                  attack-action="jump" attack-reach="16" attack-frames="12" attack-sound="hit">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1,2" fps="8" />
      <qg:animation name="walk-up" frames="3,4" fps="8" />
      <qg:animation name="walk-down" frames="5,6" fps="8" />
      <qg:animation name="attack" frames="7" />
      <qg:animation name="attack-up" frames="8" />
      <qg:animation name="attack-down" frames="9" />
      <qg:on-collision with="enemy" cooldown="60"><q:call function="hurt" args="me" /></qg:on-collision>
      <qg:on-collision with="lever"><q:call function="pull" args="other" /></qg:on-collision>
      <qg:on-collision with="chest"><q:call function="treasure" args="other" /></qg:on-collision>
      <qg:on-collision with="arrow"><qg:destroy target="other" /><q:call function="hurt" args="me" /></qg:on-collision>
      <qg:on-hit with="enemy"><q:call function="slay" args="other" /></qg:on-hit>
    </qg:character>
    <qg:character id="p2" controller="topdown" player="2" sheet="delvers" frame="10"
                  x="207" y="45" hitbox="12x14" speed="70" if="{net_status() != 'offline'}"
                  attack-action="jump" attack-reach="16" attack-frames="12" attack-sound="hit">
      <qg:animation name="idle" frames="10" />
      <qg:animation name="walk" frames="11,12" fps="8" />
      <qg:animation name="walk-up" frames="13,14" fps="8" />
      <qg:animation name="walk-down" frames="15,16" fps="8" />
      <qg:animation name="attack" frames="17" />
      <qg:animation name="attack-up" frames="18" />
      <qg:animation name="attack-down" frames="19" />
      <qg:on-collision with="enemy" cooldown="60"><q:call function="hurt" args="me" /></qg:on-collision>
      <qg:on-collision with="lever"><q:call function="pull" args="other" /></qg:on-collision>
      <qg:on-collision with="chest"><q:call function="treasure" args="other" /></qg:on-collision>
      <qg:on-collision with="arrow"><qg:destroy target="other" /><q:call function="hurt" args="me" /></qg:on-collision>
      <qg:on-hit with="enemy"><q:call function="slay" args="other" /></qg:on-hit>
    </qg:character>

    <qg:instance prefab="Lever" name="lever-west" x="27" y="135" />
    <qg:instance prefab="Lever" name="lever-east" x="225" y="135" />
    <qg:instance prefab="Chest" name="chest" x="126" y="180" />
    <qg:timer after="1">
      <qg:tween target="chest" property="y" to="176" seconds="0.8" trans="sine" ease="in-out" repeat="-1" yoyo="true" />
    </qg:timer>
    <qg:instance prefab="Gem" name="gem-6" x="225" y="27" />
    <qg:instance prefab="Gem" name="gem-7" x="126" y="99" />
    <qg:instance prefab="Skeleton" name="skeleton-1" x="126" y="63" />
    <qg:instance prefab="Skeleton" name="skeleton-2" x="81" y="117" />
    <qg:instance prefab="Skeleton" name="skeleton-3" x="171" y="117" />
    <qg:instance prefab="Archer" name="archer" x="207" y="81" />

    <qg:hud position="top-left" size="10">
      <qg:inventory />
      <qg:text bind="message" />
    </qg:hud>
  </qg:scene>

  <!-- ===== The end, and the fall ===== -->

  <qg:scene name="the-end" width="256" height="224" background="#141020">
    <qg:music sound="torchlight" />
    <qg:emitter particles="treasure" x="128" y="150" />
    <qg:sprite sheet="crypt" frame="7" x="128" y="120" gd:scale="3,3" />
    <qg:hud position="top-center" size="16">
      <qg:text bind="message" />
      <qg:counter item="gem" label="GEMS" />
    </qg:hud>
    <qg:menu position="bottom-center">
      <qg:button label="To the title"><qg:leave /><qg:goto-scene name="title" /></qg:button>
    </qg:menu>
  </qg:scene>

  <qg:scene name="fallen" width="256" height="224" background="#000000">
    <qg:emitter particles="dust" x="128" y="0" width="256" />
    <qg:hud position="top-center" size="16"><qg:text value="{tr('THE CRYPT KEEPS YOU.')}" /></qg:hud>
    <qg:menu position="center">
      <!-- alone: back to the start of the crypt where the delver fell (it was saved on entering);
           together: from the first crypt, on both machines -->
      <qg:button label="Try again">
        <q:if condition="{net_status() == 'offline' and has_save()}">
          <qg:continue />
        <q:else>
          <qg:goto-scene name="crypt-1" />
        </q:else>
        </q:if>
      </qg:button>
      <qg:button label="To the title"><qg:leave /><qg:goto-scene name="title" /></qg:button>
    </qg:menu>
  </qg:scene>

</q:application>
