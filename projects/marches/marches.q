<q:application id="marches" type="game">

  <!-- Marches: a skirmish on a map of hexes, turn by turn. Three riders hold the
       keep by the river against four raiders who come from the east by the
       fords. Click a rider, then a hex: it rides there by the cheapest way, four
       moves a turn, a forest or a ford costing two, the hills and the marsh three;
       the river and the rocks stop it. A rider next to a raider strikes it with a
       click on the raider, and is spent for the turn. End the turn (E, or the
       button), and the raiders ride at the nearest rider, three moves each, and
       strike. The raiders all fallen, the march is held; the riders all fallen, or
       a raider in the keep, it is lost. Written for PLAN_GAMES_3.md's Phase 6: hex
       maps, terrain costs, qg:travel and cost(). The art is drawn by
       scripts/art/marches.py (CC0); the sounds are Kenney's (CC0). -->

  <qg:input action="end-turn" keys="E" />
  <!-- on a phone a tap is a click; and the end of the turn under a finger -->
  <qg:touch-button action="end-turn" label="E" x="380" y="230" size="40" />

  <!-- the land: hexes with their points up, and what a step onto each costs -->
  <qg:tileset name="land" src="assets/land.png" tile="28x32" shape="hex">
    <qg:tile frame="0" shape="none" />              <!-- grass -->
    <qg:tile frame="1" shape="none" cost="2" />     <!-- forest -->
    <qg:tile frame="2" shape="none" cost="3" />     <!-- hills -->
    <qg:tile frame="3" shape="none" cost="3" />     <!-- marsh -->
    <!-- 4, the river, and 5, the rocks: solid -->
    <qg:tile frame="6" shape="none" cost="2" />     <!-- a ford -->
    <qg:tile frame="7" shape="none" />              <!-- the keep -->
  </qg:tileset>
  <qg:spritesheet name="units" src="assets/units.png" tile="24" />
  <qg:spritesheet name="marks" src="assets/marks.png" tile="28x32" />

  <qg:sound bus="effects" name="ride" src="assets/kenney/audio/jump.ogg" />
  <qg:sound bus="effects" name="blow" src="assets/kenney/audio/stomp.ogg" />
  <qg:sound bus="effects" name="fall" src="assets/kenney/audio/hurt.ogg" />
  <qg:sound bus="effects" name="won" src="assets/kenney/audio/win.ogg" />

  <qg:prefab name="Rider" tag="rider" sheet="units" frame="0" hitbox="14x14" health="3">
    <qg:state name="ready" frame="0" initial="true" />
    <qg:state name="chosen" frame="4" />
    <qg:state name="spent" frame="1" />
    <qg:label value="{str(me.health)}" dy="-15" size="8" color="#c8d8ff" />
    <qg:on-death><qg:play sound="fall" /></qg:on-death>
  </qg:prefab>
  <qg:prefab name="Raider" tag="raider" sheet="units" frame="2" hitbox="14x14" health="2">
    <qg:state name="whole" frame="2" initial="true" />
    <qg:state name="hurt" frame="3" />
    <qg:label value="{str(me.health)}" dy="-15" size="8" color="#ffc8c0" />
    <qg:on-damage><qg:become target="me" state="hurt" /></qg:on-damage>
    <qg:on-death><qg:play sound="fall" /></qg:on-death>
  </qg:prefab>

  <qg:language lang="pt" name="Português">
    <qg:phrase text="MARCHES" as="MARCAS" />
    <qg:phrase text="Hold the ford: three riders, four raiders." as="Segure o vau: três cavaleiros, quatro saqueadores." />
    <qg:phrase text="Play" as="Jogar" />
    <qg:phrase text="Options" as="Opções" />
    <qg:phrase text="Language" as="Idioma" />
    <qg:phrase text="Click a rider." as="Clique num cavaleiro." />
    <qg:phrase text="Your turn: click a rider." as="Sua vez: clique num cavaleiro." />
    <qg:phrase text="The raiders ride." as="Os saqueadores avançam." />
    <qg:phrase text="Wait for the raiders." as="Espere os saqueadores." />
    <qg:phrase text="Where to? Four moves." as="Para onde? Quatro movimentos." />
    <qg:phrase text="A blow!" as="Um golpe!" />
    <qg:phrase text="Strike a raider next to it, or choose another rider." as="Golpeie um saqueador ao lado, ou escolha outro cavaleiro." />
    <qg:phrase text="Choose another rider, or end the turn (E)." as="Escolha outro cavaleiro, ou encerre a vez (E)." />
    <qg:phrase text="Too far, or no way there." as="Longe demais, ou sem caminho." />
    <qg:phrase text="That rider is spent." as="Esse cavaleiro já agiu." />
    <qg:phrase text="End turn" as="Encerrar a vez" />
    <qg:phrase text="The march is held." as="A marca resiste." />
    <qg:phrase text="The march is lost." as="A marca caiu." />
    <qg:phrase text="Again" as="De novo" />
    <qg:phrase text="Grass" as="Campo" />
    <qg:phrase text="Forest" as="Floresta" />
    <qg:phrase text="Hills" as="Colinas" />
    <qg:phrase text="Marsh" as="Pântano" />
    <qg:phrase text="River" as="Rio" />
    <qg:phrase text="Rocks" as="Rochas" />
    <qg:phrase text="Ford" as="Vau" />
    <qg:phrase text="Keep" as="Torre" />
    <qg:phrase text="move" as="movimento" />
    <qg:phrase text="moves" as="movimentos" />
    <qg:phrase text="OPTIONS" as="OPÇÕES" />
    <qg:phrase text="Sounds" as="Sons" />
    <qg:phrase text="Full screen" as="Tela cheia" />
    <qg:phrase text="on" as="sim" />
    <qg:phrase text="off" as="não" />
    <qg:phrase text="Back" as="Voltar" />
  </qg:language>
  <qg:language lang="es" name="Español">
    <qg:phrase text="MARCHES" as="MARCAS" />
    <qg:phrase text="Hold the ford: three riders, four raiders." as="Defiende el vado: tres jinetes, cuatro saqueadores." />
    <qg:phrase text="Play" as="Jugar" />
    <qg:phrase text="Options" as="Opciones" />
    <qg:phrase text="Language" as="Idioma" />
    <qg:phrase text="Click a rider." as="Haz clic en un jinete." />
    <qg:phrase text="Your turn: click a rider." as="Tu turno: haz clic en un jinete." />
    <qg:phrase text="The raiders ride." as="Los saqueadores avanzan." />
    <qg:phrase text="Wait for the raiders." as="Espera a los saqueadores." />
    <qg:phrase text="Where to? Four moves." as="¿Adónde? Cuatro movimientos." />
    <qg:phrase text="A blow!" as="¡Un golpe!" />
    <qg:phrase text="Strike a raider next to it, or choose another rider." as="Golpea a un saqueador a su lado, o elige otro jinete." />
    <qg:phrase text="Choose another rider, or end the turn (E)." as="Elige otro jinete, o termina el turno (E)." />
    <qg:phrase text="Too far, or no way there." as="Demasiado lejos, o sin camino." />
    <qg:phrase text="That rider is spent." as="Ese jinete ya actuó." />
    <qg:phrase text="End turn" as="Terminar turno" />
    <qg:phrase text="The march is held." as="La marca resiste." />
    <qg:phrase text="The march is lost." as="La marca ha caído." />
    <qg:phrase text="Again" as="Otra vez" />
    <qg:phrase text="Grass" as="Pradera" />
    <qg:phrase text="Forest" as="Bosque" />
    <qg:phrase text="Hills" as="Colinas" />
    <qg:phrase text="Marsh" as="Pantano" />
    <qg:phrase text="River" as="Río" />
    <qg:phrase text="Rocks" as="Rocas" />
    <qg:phrase text="Ford" as="Vado" />
    <qg:phrase text="Keep" as="Torre" />
    <qg:phrase text="move" as="movimiento" />
    <qg:phrase text="moves" as="movimientos" />
    <qg:phrase text="OPTIONS" as="OPCIONES" />
    <qg:phrase text="Sounds" as="Sonidos" />
    <qg:phrase text="Full screen" as="Pantalla completa" />
    <qg:phrase text="on" as="sí" />
    <qg:phrase text="off" as="no" />
    <qg:phrase text="Back" as="Volver" />
  </qg:language>

  <qg:scene name="title" width="406" height="280" background="#1c2a1c">
    <qg:hud position="top-center" size="32"><qg:text value="{'MARCHES'}" /></qg:hud>
    <qg:menu position="center" size="14">
      <qg:button label="Play"><qg:goto-scene name="field" fade="0.5" /></qg:button>
      <qg:button label="Options"><qg:goto-scene name="options" /></qg:button>
      <qg:button label="{tr('Language') + ': ' + language()}"><qg:next-language /></qg:button>
    </qg:menu>
    <qg:hud position="bottom-center" size="10"><qg:text value="{'Hold the ford: three riders, four raiders.'}" /></qg:hud>
  </qg:scene>

  <qg:scene name="field" width="406" height="280" background="#1c2a1c">
    <q:set name="turn" value="riders" />
    <q:set name="chosen" value="{null}" />
    <q:set name="moved" value="[]" type="array" />     <!-- the riders that rode this turn, by name -->
    <q:set name="spent" value="[]" type="array" />     <!-- the riders that struck this turn -->
    <q:set name="message" value="Click a rider." />
    <q:set name="terrain" value="{['', 'Grass', 'Forest', 'Hills', 'Marsh', 'River', 'Rocks', 'Ford', 'Keep']}" type="array" />

    <!-- a rider of the player's chosen: it rides (once a turn, four moves at most) and strikes (once) -->
    <q:function name="choose" params="rider">
      <q:if condition="{chosen != null and not (chosen.name in spent)}">
        <qg:become target="chosen" state="ready" />
      </q:if>
      <q:set name="chosen" value="{rider}" />
      <qg:become target="rider" state="chosen" />
    </q:function>
    <q:function name="strike" params="foe">
      <qg:play sound="blow" />
      <qg:damage target="foe" amount="1" />
    </q:function>

    <!-- the raiders' turn: each rides at the nearest rider, three moves, and strikes it if it is next to it -->
    <q:function name="raiders_ride">
      <q:set name="turn" value="raiders" />
      <q:set name="message" value="The raiders ride." />
      <q:if condition="{chosen != null and not (chosen.name in spent)}">
        <qg:become target="chosen" state="ready" />
      </q:if>
      <q:set name="chosen" value="{null}" />
      <qg:for-each tag="raider" var="raider">
        <qg:travel target="raider" to="{nearest(raider, 'rider')}" budget="3" step="10">
          <qg:on-end>
            <q:if condition="{tile_at(me.col, me.row) == 8}">
              <qg:goto-scene name="lost" fade="1" />
            </q:if>
            <q:if condition="{count('rider') > 0 and distance(me, nearest(me, 'rider')) &lt; 30}">
              <q:call function="strike" args="nearest(me, 'rider')" />
            </q:if>
          </qg:on-end>
        </qg:travel>
      </qg:for-each>
      <qg:after seconds="1.5">
        <q:set name="turn" value="riders" />
        <q:set name="moved" value="[]" />
        <q:set name="spent" value="[]" />
        <q:set name="message" value="Your turn: click a rider." />
        <qg:for-each tag="rider" var="rider"><qg:become target="rider" state="ready" /></qg:for-each>
      </qg:after>
    </q:function>

    <qg:tilemap tileset="land" collision="true">
1,1,2,2,1,4,5,5,4,1,2,2,1,1
1,2,2,1,1,4,5,5,4,1,1,2,3,1
1,1,1,1,3,4,5,5,4,4,1,1,3,1
1,8,1,1,3,1,7,7,1,4,1,1,1,1
1,1,1,2,1,1,5,5,1,1,2,2,1,1
1,1,2,2,1,4,5,5,4,1,2,6,6,1
1,1,1,1,1,4,5,5,1,1,1,6,1,1
6,1,1,3,3,1,5,7,4,1,3,1,1,1
6,6,1,1,1,1,5,5,4,1,3,3,1,1
6,6,6,1,1,4,5,5,4,1,1,1,1,1
    </qg:tilemap>

    <!-- each at the middle of its hex: column 2 of row 2, column 3 of row 3 (an odd row, half a hex on)... -->
    <qg:instance prefab="Rider" name="ash" x="70" y="64" />
    <qg:instance prefab="Rider" name="birch" x="112" y="88" />
    <qg:instance prefab="Rider" name="cedar" x="70" y="112" />
    <qg:instance prefab="Raider" name="raider-1" x="364" y="40" />
    <qg:instance prefab="Raider" name="raider-2" x="350" y="112" />
    <qg:instance prefab="Raider" name="raider-3" x="336" y="184" />
    <qg:instance prefab="Raider" name="raider-4" x="350" y="208" />

    <!-- the pointer snaps to the hexes -->
    <qg:cursor id="aim" player="1" cells="true" sheet="marks" frame="0" />

    <qg:on-select>
      <q:if condition="{turn != 'riders'}">
        <q:set name="message" value="Wait for the raiders." />
      </q:if>
      <!-- a rider: chosen, unless it has struck -->
      <q:elseif condition="{other != null and other.tag == 'rider' and other.name in spent}">
        <q:set name="message" value="That rider is spent." />
      </q:elseif>
      <q:elseif condition="{other != null and other.tag == 'rider'}">
        <q:call function="choose" args="other" />
        <q:if condition="{other.name in moved}">
          <q:set name="message" value="Strike a raider next to it, or choose another rider." />
        <q:else>
          <q:set name="message" value="Where to? Four moves." />
        </q:else>
        </q:if>
      </q:elseif>
      <!-- a raider next to the chosen rider: a blow, and the rider is spent -->
      <q:elseif condition="{other != null and other.tag == 'raider' and chosen != null and distance(chosen, other) &lt; 30}">
        <q:call function="strike" args="other" />
        <qg:become target="chosen" state="spent" />
        <q:set name="spent" value="{spent + [chosen.name]}" />
        <q:set name="moved" value="{moved + [chosen.name]}" />
        <q:set name="chosen" value="{null}" />
        <q:set name="message" value="A blow!" />
      </q:elseif>
      <!-- a free hex in reach of a rider that has not ridden: it rides there -->
      <q:elseif condition="{other == null and chosen != null and not (chosen.name in moved) and cost(chosen, aim) &lt;= 4}">
        <qg:play sound="ride" />
        <q:set name="moved" value="{moved + [chosen.name]}" />
        <qg:travel target="chosen" to="aim" budget="4" step="8">
          <qg:on-end>
            <q:if condition="{count('raider') > 0 and distance(me, nearest(me, 'raider')) &lt; 30}">
              <q:set name="message" value="Strike a raider next to it, or choose another rider." />
            <q:else>
              <q:set name="message" value="Choose another rider, or end the turn (E)." />
            </q:else>
            </q:if>
          </qg:on-end>
        </qg:travel>
      </q:elseif>
      <q:elseif condition="{chosen != null}">
        <q:set name="message" value="Too far, or no way there." />
      </q:elseif>
    </qg:on-select>

    <qg:on-input action="end-turn">
      <q:if condition="{turn == 'riders'}"><q:call function="raiders_ride" /></q:if>
    </qg:on-input>

    <qg:when condition="{count('raider') == 0}">
      <qg:play sound="won" />
      <qg:goto-scene name="held" fade="1" />
    </qg:when>
    <qg:when condition="{count('rider') == 0}">
      <qg:goto-scene name="lost" fade="1" />
    </qg:when>

    <!-- what the pointer is on, and what riding there costs the chosen rider -->
    <qg:hud position="bottom-left" size="10">
      <qg:text bind="message" />
      <qg:text value="{tr(terrain[tile_at(aim.col, aim.row)]) + (': ' + str(cost(chosen, aim)) + ' ' + tr_n('move', 'moves', cost(chosen, aim)) if chosen != null and cost(chosen, aim) &lt; 99 else '')}" />
    </qg:hud>
    <qg:menu position="top-right" size="10">
      <qg:button label="End turn" if="{turn == 'riders'}"><q:call function="raiders_ride" /></qg:button>
    </qg:menu>
  </qg:scene>

  <qg:scene name="held" width="406" height="280" background="#1c2a1c">
    <qg:hud position="top-center" size="20"><qg:text value="{'The march is held.'}" /></qg:hud>
    <qg:menu position="center" size="14"><qg:button label="Again"><qg:goto-scene name="field" /></qg:button></qg:menu>
  </qg:scene>
  <qg:scene name="lost" width="406" height="280" background="#2a1c1c">
    <qg:hud position="top-center" size="20"><qg:text value="{'The march is lost.'}" /></qg:hud>
    <qg:menu position="center" size="14"><qg:button label="Again"><qg:goto-scene name="field" /></qg:button></qg:menu>
  </qg:scene>

  <!-- ===== Options: how loud, the full screen, the key; kept between runs ===== -->

  <qg:scene name="options" width="406" height="280" background="#1c2a1c">
    <qg:hud position="top-center" size="24"><qg:text value="{tr('OPTIONS')}" /></qg:hud>
    <qg:menu position="center" size="14">
      <qg:slider label="Sounds" bus="effects" />
      <qg:button label="{tr('Full screen') + ': ' + (tr('on') if fullscreen() else tr('off'))}"><qg:fullscreen /></qg:button>
      <qg:rebind label="End turn" action="end-turn" />
      <qg:button label="Back"><qg:goto-scene name="title" /></qg:button>
    </qg:menu>
  </qg:scene>
</q:application>
