<q:application id="crates" type="game">

  <!-- Crates: a box-pushing puzzle on a dockside, the game that drives Phase 3
       of PLAN_GAMES_3.md. Three rooms drawn in Tiled (rooms/*.tmx): their
       walls, the harbour's water, the pads and every crate, gate and key are
       the maps', and so are the doors between them, the sign by each door, a
       gull's way over the water and each room's title and hint. The worker
       walks a cell at a time with the keys, or goes where it is clicked by
       the shortest way, and pushes what it walks into. The art is drawn for
       it by scripts/art/crates.py (CC0); the sounds are Kenney's Pixel
       Platformer (CC0). -->

  <q:set name="message" value="" />

  <!-- the crates of the room standing on a pad: a pad is a tile of the map's pads layer -->
  <q:function name="placed">
    <q:set name="n" value="0" type="number" />
    <qg:for-each tag="crate" var="c">
      <q:if condition="{tile_at(c.col, c.row, 'pads') != 0}">
        <q:set name="n" value="{n + 1}" />
      </q:if>
    </qg:for-each>
    <q:return value="{n}" />
  </q:function>
  <!-- the gates that close a room open, and the camera goes to show it -->
  <q:function name="open_gates">
    <qg:for-each tag="gate" var="g">
      <q:if condition="{g.state == 'shut'}">
        <qg:camera-to target="g" zoom="2" seconds="0.5" hold="0.8" />
        <qg:emit particles="dust" at="g" />
        <qg:destroy target="g" />
      </q:if>
    </qg:for-each>
    <qg:play sound="open" />
  </q:function>

  <qg:input action="restart" keys="R" />

  <!-- warehouse.png: 1 concrete, 2 brick, 3 a corner, 4 an edge, 5 a pad, 6 planks, 7 an arrow, 8 stripes.
       water.png: the harbour's four frames in turn, and a pier. -->
  <qg:tileset name="warehouse" src="assets/warehouse.png" tile="16" />
  <qg:tileset name="water" src="assets/water.png" tile="16">
    <qg:tile frame="0" frames="4" fps="4" />
  </qg:tileset>
  <qg:spritesheet name="people" src="assets/people.png" tile="16" />
  <qg:spritesheet name="faces" src="assets/faces.png" tile="32" />

  <qg:sound name="push" src="assets/kenney/audio/block.ogg" />
  <qg:sound name="open" src="assets/kenney/audio/powerup.ogg" />
  <qg:sound name="pick" src="assets/kenney/audio/coin.ogg" />
  <qg:sound name="done" src="assets/kenney/audio/win.ogg" />
  <qg:particles name="dust" preset="smoke" color="#c8c0b0" />
  <qg:particles name="cheer" preset="confetti" />

  <!-- a crate; a barrel is one, drawn round -->
  <qg:prefab name="Crate" tag="crate" sheet="people" frame="6" hitbox="14x14" solid="true" pushable="true" />
  <qg:prefab name="Barrel" extends="Crate" frame="7" />
  <qg:prefab name="Foreman" tag="foreman" sheet="people" frame="4" hitbox="14x14" solid="true">
    <qg:state name="waiting" initial="true" />
    <qg:state name="pleased" frame="5" />
  </qg:prefab>
  <!-- a gate is shut until the room's crates are in place; one with state locked in the map opens with the key -->
  <qg:prefab name="Gate" tag="gate" sheet="people" frame="8" hitbox="16x16" solid="true">
    <qg:state name="shut" initial="true" />
    <qg:state name="locked" frame="9" />
  </qg:prefab>
  <qg:prefab name="Key" tag="key" sheet="people" frame="10" hitbox="12x12" />
  <qg:prefab name="Gull" tag="gull" sheet="people" frame="11" hitbox="8x8" ai="path" speed="40" layer="2">
    <qg:animation name="fly" frames="11,12" fps="4" />
    <qg:on-screen-exit><qg:destroy /></qg:on-screen-exit>
  </qg:prefab>

  <qg:language lang="pt" name="Português">
    <qg:phrase text="New game" as="Novo jogo" />
    <qg:phrase text="Continue" as="Continuar" />
    <qg:phrase text="Language" as="Idioma" />
    <qg:phrase text="PADS" as="PLATAFORMAS" />
    <qg:phrase text="THE DOCK" as="O CAIS" />
    <qg:phrase text="THE YARD" as="O PÁTIO" />
    <qg:phrase text="THE LOFT" as="O SÓTÃO" />
    <qg:phrase text="PUSH THE CRATES ONTO THE PADS." as="EMPURRE AS CAIXAS PARA AS PLATAFORMAS." />
    <qg:phrase text="THE KEY IS ON THE PIER." as="A CHAVE ESTÁ NO PÍER." />
    <qg:phrase text="BARRELS PUSH LIKE CRATES." as="BARRIS SE EMPURRAM COMO CAIXAS." />
    <qg:phrase text="THE GATE OPENS." as="O PORTÃO SE ABRE." />
    <qg:phrase text="SHUT TILL THE CRATES ARE IN." as="FECHADO ATÉ AS CAIXAS ESTAREM NO LUGAR." />
    <qg:phrase text="LOCKED. THE KEY IS ON THE PIER." as="TRANCADO. A CHAVE ESTÁ NO PÍER." />
    <qg:phrase text="GOT THE KEY." as="PEGOU A CHAVE." />
    <qg:phrase text="UNLOCKED." as="DESTRANCADO." />
    <qg:phrase text="ALL STOWED. GOOD WORK." as="TUDO GUARDADO. BOM TRABALHO." />
    <qg:phrase text="R: START THE ROOM OVER" as="R: RECOMEÇAR A SALA" />
    <qg:phrase text="FOREMAN" as="CAPATAZ" />
    <qg:phrase text="Morning. Two crates came in on the boat." as="Bom dia. Chegaram duas caixas no barco." />
    <qg:phrase text="Push them onto the yellow pads. Need a hand?" as="Empurre-as para as plataformas amarelas. Precisa de ajuda?" />
    <qg:phrase text="How do I push?" as="Como eu empurro?" />
    <qg:phrase text="On it, boss." as="Deixa comigo, chefe." />
    <qg:phrase text="Walk into a crate and it moves on, if nothing is behind it." as="Ande contra uma caixa e ela avança, se nada estiver atrás dela." />
    <qg:phrase text="Or click a crate next to you." as="Ou clique numa caixa ao seu lado." />
    <qg:phrase text="Stuck? R starts the room over." as="Travou? R recomeça a sala." />
    <qg:phrase text="The gate opens when they are in place." as="O portão abre quando elas estiverem no lugar." />
    <qg:phrase text="Last room. The barrels too." as="Última sala. Os barris também." />
    <qg:phrase text="That's the lot. Good work!" as="É tudo. Bom trabalho!" />
    <qg:phrase text="Another shift?" as="Mais um turno?" />
    <qg:phrase text="Home time." as="Hora de ir para casa." />
  </qg:language>
  <qg:language lang="es" name="Español">
    <qg:phrase text="New game" as="Nueva partida" />
    <qg:phrase text="Continue" as="Continuar" />
    <qg:phrase text="Language" as="Idioma" />
    <qg:phrase text="PADS" as="PLATAFORMAS" />
    <qg:phrase text="THE DOCK" as="EL MUELLE" />
    <qg:phrase text="THE YARD" as="EL PATIO" />
    <qg:phrase text="THE LOFT" as="EL DESVÁN" />
    <qg:phrase text="PUSH THE CRATES ONTO THE PADS." as="EMPUJA LAS CAJAS A LAS PLATAFORMAS." />
    <qg:phrase text="THE KEY IS ON THE PIER." as="LA LLAVE ESTÁ EN EL MUELLE." />
    <qg:phrase text="BARRELS PUSH LIKE CRATES." as="LOS BARRILES SE EMPUJAN COMO LAS CAJAS." />
    <qg:phrase text="THE GATE OPENS." as="LA PUERTA SE ABRE." />
    <qg:phrase text="SHUT TILL THE CRATES ARE IN." as="CERRADA HASTA QUE LAS CAJAS ESTÉN EN SU SITIO." />
    <qg:phrase text="LOCKED. THE KEY IS ON THE PIER." as="CERRADA CON LLAVE. LA LLAVE ESTÁ EN EL MUELLE." />
    <qg:phrase text="GOT THE KEY." as="TIENES LA LLAVE." />
    <qg:phrase text="UNLOCKED." as="ABIERTA." />
    <qg:phrase text="ALL STOWED. GOOD WORK." as="TODO GUARDADO. BUEN TRABAJO." />
    <qg:phrase text="R: START THE ROOM OVER" as="R: EMPEZAR LA SALA DE NUEVO" />
    <qg:phrase text="FOREMAN" as="CAPATAZ" />
    <qg:phrase text="Morning. Two crates came in on the boat." as="Buenos días. Llegaron dos cajas en el barco." />
    <qg:phrase text="Push them onto the yellow pads. Need a hand?" as="Empújalas a las plataformas amarillas. ¿Necesitas ayuda?" />
    <qg:phrase text="How do I push?" as="¿Cómo empujo?" />
    <qg:phrase text="On it, boss." as="Enseguida, jefe." />
    <qg:phrase text="Walk into a crate and it moves on, if nothing is behind it." as="Camina contra una caja y avanza, si nada hay detrás." />
    <qg:phrase text="Or click a crate next to you." as="O haz clic en una caja a tu lado." />
    <qg:phrase text="Stuck? R starts the room over." as="¿Atascado? R empieza la sala de nuevo." />
    <qg:phrase text="The gate opens when they are in place." as="La puerta se abre cuando estén en su sitio." />
    <qg:phrase text="Last room. The barrels too." as="Última sala. Los barriles también." />
    <qg:phrase text="That's the lot. Good work!" as="Eso es todo. ¡Buen trabajo!" />
    <qg:phrase text="Another shift?" as="¿Otro turno?" />
    <qg:phrase text="Home time." as="Hora de volver a casa." />
  </qg:language>

  <!-- ===== The title ===== -->

  <qg:scene name="title" width="320" height="192" background="#20283a">
    <qg:hud position="top-center" size="32"><qg:text value="{'CRATES'}" /></qg:hud>
    <qg:menu position="center">
      <qg:button label="New game"><qg:goto-scene name="dock" fade="0.3" /></qg:button>
      <qg:button label="Continue" if="{has_save()}"><qg:continue /></qg:button>
      <qg:button label="{tr('Language') + ': ' + language()}"><qg:next-language /></qg:button>
    </qg:menu>
  </qg:scene>

  <!-- ===== The dock: two crates, and the foreman to talk to ===== -->

  <qg:scene name="dock" width="320" height="192" background="#20283a" save="true">
    <qg:tilemap tileset="warehouse" src="rooms/dock.tmx" />
    <qg:cursor player="1" grid="16" sheet="people" frame="13" />
    <qg:character id="worker" controller="pointer" sheet="people" frame="0" x="8" y="88" hitbox="12x12"
                  step-frames="10">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1,2" fps="12" />
      <qg:animation name="bump" frames="3" />
      <qg:on-collision with="crate"><qg:play sound="push" /></qg:on-collision>
      <qg:on-collision with="sign"><q:set name="message" value="{tiled('hint')}" /></qg:on-collision>
      <qg:on-collision with="foreman"><qg:say dialogue="foreman" /></qg:on-collision>
      <qg:on-collision with="gate"><q:set name="message" value="SHUT TILL THE CRATES ARE IN." /></qg:on-collision>
    </qg:character>
    <qg:camera follow="worker" bounds="tilemap" />
    <qg:dialogue name="foreman" size="9" speed="40" sheet="faces">
      <qg:line who="FOREMAN" portrait="0" text="Morning. Two crates came in on the boat." />
      <qg:line who="FOREMAN" portrait="0" text="Push them onto the yellow pads. Need a hand?">
        <qg:choice label="How do I push?"><qg:say dialogue="how" /></qg:choice>
        <qg:choice label="On it, boss." />
      </qg:line>
      <qg:line who="FOREMAN" portrait="0" text="The gate opens when they are in place." />
    </qg:dialogue>
    <qg:dialogue name="how" size="9" speed="40" sheet="faces">
      <qg:line who="FOREMAN" portrait="0" text="Walk into a crate and it moves on, if nothing is behind it." />
      <qg:line who="FOREMAN" portrait="0" text="Or click a crate next to you." />
      <qg:line who="FOREMAN" portrait="0" text="Stuck? R starts the room over." />
    </qg:dialogue>
    <qg:when condition="{placed() == count('crate')}">
      <q:set name="message" value="THE GATE OPENS." />
      <q:call function="open_gates" />
    </qg:when>
    <qg:on-input action="restart"><qg:goto-scene name="dock" /></qg:on-input>
    <qg:hud position="top-left" size="12">
      <qg:text value="{tr(tiled('title')) + '   ' + tr('PADS') + ' ' + str(placed()) + '/' + str(count('crate'))}" />
      <qg:text bind="message" />
    </qg:hud>
  </qg:scene>

  <!-- ===== The yard: the harbour, a key on the pier, a locked gate ===== -->

  <qg:scene name="yard" width="320" height="192" background="#20283a" save="true">
    <qg:tilemap tileset="warehouse" src="rooms/yard.tmx" />
    <qg:cursor player="1" grid="16" sheet="people" frame="13" />
    <qg:character id="worker" controller="pointer" sheet="people" frame="0" x="8" y="88" hitbox="12x12"
                  step-frames="10">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1,2" fps="12" />
      <qg:animation name="bump" frames="3" />
      <qg:on-collision with="crate"><qg:play sound="push" /></qg:on-collision>
      <qg:on-collision with="sign"><q:set name="message" value="{tiled('hint')}" /></qg:on-collision>
      <qg:on-collision with="key">
        <qg:attach target="other" dy="-10" />
        <qg:play sound="pick" />
        <q:set name="message" value="GOT THE KEY." />
      </qg:on-collision>
      <qg:on-collision with="gate">
        <q:if condition="{other.state == 'locked' and carrying(me, 'key') != null}">
          <qg:for-each tag="key" var="k"><qg:destroy target="k" /></qg:for-each>
          <qg:emit particles="dust" at="other" />
          <qg:destroy target="other" />
          <qg:play sound="open" />
          <q:set name="message" value="UNLOCKED." />
          <q:elseif condition="{other.state == 'locked'}">
            <q:set name="message" value="LOCKED. THE KEY IS ON THE PIER." />
          </q:elseif>
          <q:else><q:set name="message" value="SHUT TILL THE CRATES ARE IN." /></q:else>
        </q:if>
      </qg:on-collision>
    </qg:character>
    <qg:camera follow="worker" bounds="tilemap" />
    <qg:when condition="{placed() == count('crate')}">
      <q:set name="message" value="THE GATE OPENS." />
      <q:call function="open_gates" />
    </qg:when>
    <!-- now and then a gull, along the way drawn in the map -->
    <qg:timer every="420" from="60"><qg:spawn prefab="Gull" at="path" path="gull" /></qg:timer>
    <qg:on-input action="restart"><qg:goto-scene name="yard" /></qg:on-input>
    <qg:hud position="top-left" size="12">
      <qg:text value="{tr(tiled('title')) + '   ' + tr('PADS') + ' ' + str(placed()) + '/' + str(count('crate'))}" />
      <qg:text bind="message" />
    </qg:hud>
  </qg:scene>

  <!-- ===== The loft: crates and barrels, and the foreman waiting at the end ===== -->

  <qg:scene name="loft" width="320" height="192" background="#20283a" save="true">
    <qg:tilemap tileset="warehouse" src="rooms/loft.tmx" />
    <qg:cursor player="1" grid="16" sheet="people" frame="13" />
    <qg:character id="worker" controller="pointer" sheet="people" frame="0" x="8" y="88" hitbox="12x12"
                  step-frames="10">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1,2" fps="12" />
      <qg:animation name="bump" frames="3" />
      <qg:on-collision with="crate"><qg:play sound="push" /></qg:on-collision>
      <qg:on-collision with="sign"><q:set name="message" value="{tiled('hint')}" /></qg:on-collision>
      <qg:on-collision with="foreman">
        <q:if condition="{other.state == 'pleased'}">
          <qg:say dialogue="done" />
          <q:else><qg:say dialogue="last" /></q:else>
        </q:if>
      </qg:on-collision>
    </qg:character>
    <qg:camera follow="worker" bounds="tilemap" />
    <qg:dialogue name="last" size="9" speed="40" sheet="faces">
      <qg:line who="FOREMAN" portrait="0" text="Last room. The barrels too." />
    </qg:dialogue>
    <qg:dialogue name="done" size="9" speed="40" sheet="faces">
      <qg:line who="FOREMAN" portrait="1" text="That's the lot. Good work!">
        <qg:choice label="Another shift?"><qg:goto-scene name="dock" fade="0.5" /></qg:choice>
        <qg:choice label="Home time."><qg:goto-scene name="title" fade="0.5" /></qg:choice>
      </qg:line>
    </qg:dialogue>
    <qg:when condition="{placed() == count('crate')}">
      <q:set name="message" value="ALL STOWED. GOOD WORK." />
      <qg:play sound="done" />
      <qg:for-each tag="foreman" var="f">
        <qg:become target="f" state="pleased" />
        <qg:camera-to target="f" zoom="2" seconds="0.5" hold="1" />
        <qg:emit particles="cheer" at="f" />
      </qg:for-each>
    </qg:when>
    <qg:on-input action="restart"><qg:goto-scene name="loft" /></qg:on-input>
    <qg:hud position="top-left" size="12">
      <qg:text value="{tr(tiled('title')) + '   ' + tr('PADS') + ' ' + str(placed()) + '/' + str(count('crate'))}" />
      <qg:text bind="message" />
    </qg:hud>
  </qg:scene>

</q:application>
