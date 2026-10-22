<q:application id="rally" type="game">

  <!-- Rally: two cars round a circuit seen from above, on one keyboard or over
       the network. The circuit is wider and taller than the screen, so each
       car has a camera of its own (qg:camera player=): on one machine the
       screen splits in two, red on the left, blue on the right; over the
       network each machine shows its own car on the whole screen. The barrier
       lifts at the green light; the first to finish three laps wins. A lap
       counts at the line only after halfway round, at the top of the loop in
       the infield. The art and the circuit (a Tiled map) are drawn by
       scripts/art/rally.py (CC0); the sounds are Kenney's Pixel Platformer
       (CC0). -->

  <!-- how many laps win the race -->
  <q:set name="race_laps" value="3" type="number" />
  <!-- the last winner: 1 red, 2 blue -->
  <q:set name="winner" value="0" type="number" />

  <qg:tileset name="track" src="assets/track.png" tile="16" />
  <qg:spritesheet name="cars" src="assets/cars.png" tile="16" />
  <qg:spritesheet name="gate" src="assets/gate.png" tile="16x80" />

  <qg:sound bus="effects" name="beep" src="assets/kenney/audio/block.ogg" />
  <qg:sound bus="effects" name="go" src="assets/kenney/audio/powerup.ogg" />
  <qg:sound bus="effects" name="lap" src="assets/kenney/audio/coin.ogg" />
  <qg:sound bus="effects" name="flag" src="assets/kenney/audio/win.ogg" />

  <!-- Red drives with W A S D, blue with the arrows; over the network, each with W A S D. -->
  <qg:input action="up" keys="W, JoyUp" player="1" />
  <qg:input action="down" keys="S, JoyDown" player="1" />
  <qg:input action="left" keys="A, JoyLeft" player="1" />
  <qg:input action="right" keys="D, JoyRight" player="1" />
  <qg:input action="up" keys="Up" player="2" />
  <qg:input action="down" keys="Down" player="2" />
  <qg:input action="left" keys="Left" player="2" />
  <qg:input action="right" keys="Right" player="2" />

  <qg:multiplayer players="2" start="race" />

  <!-- The barrier across the road at the start; it lifts at the green light. -->
  <qg:prefab name="Gate" tag="gate" sheet="gate" hitbox="16x80" solid="true" />

  <!-- on a phone: a stick for the car, under a finger, in every scene -->
  <qg:touch-stick x="48" y="168" size="56" />

  <qg:language lang="pt" name="Português">
    <qg:phrase text="RALLY" as="RALI" />
    <qg:phrase text="Two players, one keyboard" as="Dois jogadores, um teclado" />
    <qg:phrase text="Over the network" as="Pela rede" />
    <qg:phrase text="Options" as="Opções" />
    <qg:phrase text="Language" as="Idioma" />
    <qg:phrase text="Quit" as="Sair" />
    <qg:phrase text="RED: W A S D    BLUE: THE ARROWS" as="VERMELHO: W A S D    AZUL: AS SETAS" />
    <qg:phrase text="TWO CARS, TWO MACHINES. ESCAPE: BACK." as="DOIS CARROS, DUAS MÁQUINAS. ESC: VOLTAR." />
    <qg:phrase text="RED" as="VERMELHO" />
    <qg:phrase text="BLUE" as="AZUL" />
    <qg:phrase text="LAP" as="VOLTA" />
    <qg:phrase text="GO!" as="JÁ!" />
    <qg:phrase text="WINS" as="VENCE" />
    <qg:phrase text="Again" as="De novo" />
    <qg:phrase text="To the title" as="Para o título" />
    <qg:phrase text="OPTIONS" as="OPÇÕES" />
    <qg:phrase text="Sounds" as="Sons" />
    <qg:phrase text="Full screen" as="Tela cheia" />
    <qg:phrase text="on" as="sim" />
    <qg:phrase text="off" as="não" />
    <qg:phrase text="Red up" as="Vermelho sobe" />
    <qg:phrase text="Red down" as="Vermelho desce" />
    <qg:phrase text="Red left" as="Vermelho esquerda" />
    <qg:phrase text="Red right" as="Vermelho direita" />
    <qg:phrase text="Blue up" as="Azul sobe" />
    <qg:phrase text="Blue down" as="Azul desce" />
    <qg:phrase text="Blue left" as="Azul esquerda" />
    <qg:phrase text="Blue right" as="Azul direita" />
    <qg:phrase text="Back" as="Voltar" />
  </qg:language>
  <qg:language lang="es" name="Español">
    <qg:phrase text="RALLY" as="RALLY" />
    <qg:phrase text="Two players, one keyboard" as="Dos jugadores, un teclado" />
    <qg:phrase text="Over the network" as="Por la red" />
    <qg:phrase text="Options" as="Opciones" />
    <qg:phrase text="Language" as="Idioma" />
    <qg:phrase text="Quit" as="Salir" />
    <qg:phrase text="RED: W A S D    BLUE: THE ARROWS" as="ROJO: W A S D    AZUL: LAS FLECHAS" />
    <qg:phrase text="TWO CARS, TWO MACHINES. ESCAPE: BACK." as="DOS COCHES, DOS MÁQUINAS. ESC: VOLVER." />
    <qg:phrase text="RED" as="ROJO" />
    <qg:phrase text="BLUE" as="AZUL" />
    <qg:phrase text="LAP" as="VUELTA" />
    <qg:phrase text="GO!" as="¡YA!" />
    <qg:phrase text="WINS" as="GANA" />
    <qg:phrase text="Again" as="Otra vez" />
    <qg:phrase text="To the title" as="Al título" />
    <qg:phrase text="OPTIONS" as="OPCIONES" />
    <qg:phrase text="Sounds" as="Sonidos" />
    <qg:phrase text="Full screen" as="Pantalla completa" />
    <qg:phrase text="on" as="sí" />
    <qg:phrase text="off" as="no" />
    <qg:phrase text="Red up" as="Rojo arriba" />
    <qg:phrase text="Red down" as="Rojo abajo" />
    <qg:phrase text="Red left" as="Rojo izquierda" />
    <qg:phrase text="Red right" as="Rojo derecha" />
    <qg:phrase text="Blue up" as="Azul arriba" />
    <qg:phrase text="Blue down" as="Azul abajo" />
    <qg:phrase text="Blue left" as="Azul izquierda" />
    <qg:phrase text="Blue right" as="Azul derecha" />
    <qg:phrase text="Back" as="Volver" />
  </qg:language>

  <qg:scene name="title" width="384" height="216" background="#2c5a2a">
    <qg:sprite sheet="cars" frame="0" x="150" y="56" gd:scale="3,3" />
    <qg:sprite sheet="cars" frame="3" x="234" y="56" gd:scale="3,3" />
    <qg:hud position="top-center" size="28"><qg:text value="{tr('RALLY')}" /></qg:hud>
    <qg:menu position="center" size="14">
      <qg:button label="Two players, one keyboard"><qg:goto-scene name="race" fade="0.3" /></qg:button>
      <qg:button label="Over the network"><qg:goto-scene name="together" /></qg:button>
      <qg:button label="Options"><qg:goto-scene name="options" /></qg:button>
      <qg:button label="{tr('Language') + ': ' + language()}"><qg:next-language /></qg:button>
      <!-- a desktop build quits; a page in a browser has nothing to quit to -->
      <qg:button label="Quit" if="{can_quit()}"><qg:quit /></qg:button>
    </qg:menu>
    <qg:hud position="bottom-center" size="10"><qg:text value="{tr('RED: W A S D    BLUE: THE ARROWS')}" /></qg:hud>
  </qg:scene>

  <!-- Two machines: one hosts, the other joins its address; the race starts as it does. -->
  <qg:scene name="together" width="384" height="216" background="#2c5a2a">
    <qg:hud position="top-center" size="10"><qg:text value="{tr('TWO CARS, TWO MACHINES. ESCAPE: BACK.')}" /></qg:hud>
    <qg:lobby local="race" local-label="Two players, one keyboard" size="12" />
    <qg:on-input action="cancel">
      <qg:leave />
      <qg:goto-scene name="title" />
    </qg:on-input>
  </qg:scene>

  <!-- The race: the circuit, the two cars on the grid behind the barrier, a
       camera for each, and the laps each has done. -->
  <qg:scene name="race" width="384" height="216" background="#2c5a2a" seed="1">
    <q:set name="laps" type="array" value="[0, 0]" />
    <!-- halfway round on this lap: the line counts it only then -->
    <q:set name="half" type="array" value="[false, false]" />
    <qg:tilemap tileset="track" src="track/track.tmx" />

    <qg:character id="red" controller="topdown" player="1" sheet="cars" frame="0" x="440" y="56"
                  hitbox="12x12" speed="150">
      <qg:animation name="walk" frames="0" />
      <qg:animation name="walk-up" frames="1" />
      <qg:animation name="walk-down" frames="2" />
      <qg:on-collision with="half"><q:call function="halfway" args="1" /></qg:on-collision>
      <qg:on-collision with="finish"><q:call function="across" args="1" /></qg:on-collision>
    </qg:character>
    <qg:character id="blue" controller="topdown" player="2" sheet="cars" frame="3" x="440" y="88"
                  hitbox="12x12" speed="150">
      <qg:animation name="walk" frames="3" />
      <qg:animation name="walk-up" frames="4" />
      <qg:animation name="walk-down" frames="5" />
      <qg:on-collision with="half"><q:call function="halfway" args="2" /></qg:on-collision>
      <qg:on-collision with="finish"><q:call function="across" args="2" /></qg:on-collision>
    </qg:character>
    <qg:instance prefab="Gate" name="gate" x="472" y="72" />

    <!-- one view each: the screen splits on one machine -->
    <qg:camera player="1" follow="red" smooth="8" lead="24" />
    <qg:camera player="2" follow="blue" smooth="8" lead="24" />

    <!-- the lights: three beeps, and the barrier lifts -->
    <qg:timer after="30"><qg:play sound="beep" /></qg:timer>
    <qg:timer after="90"><qg:play sound="beep" /></qg:timer>
    <qg:timer after="150"><qg:play sound="beep" /></qg:timer>
    <qg:timer after="210">
      <qg:play sound="go" />
      <qg:destroy target="gate" />
    </qg:timer>

    <q:function name="halfway" params="n">
      <q:set name="half" index="{n - 1}" value="{true}" />
    </q:function>
    <!-- over the line: a lap, if it went halfway round first; the last one wins -->
    <q:function name="across" params="n">
      <q:if condition="{half[n - 1]}">
        <q:set name="half" index="{n - 1}" value="{false}" />
        <q:set name="laps" index="{n - 1}" value="{laps[n - 1] + 1}" />
        <qg:play sound="lap" />
        <q:if condition="{laps[n - 1] >= race_laps and winner == 0}">
          <q:set name="winner" value="{n}" />
          <qg:play sound="flag" />
          <qg:goto-scene name="flag" fade="0.5" />
        </q:if>
      </q:if>
    </q:function>

    <qg:hud position="top-left" size="10">
      <qg:text value="{tr('RED') + '  ' + tr('LAP') + ' ' + str(min(laps[0] + 1, race_laps)) + '/' + str(race_laps)}"
               color="#ff8070" />
    </qg:hud>
    <qg:hud position="top-right" size="10">
      <qg:text value="{tr('BLUE') + '  ' + tr('LAP') + ' ' + str(min(laps[1] + 1, race_laps)) + '/' + str(race_laps)}"
               color="#88b0ff" />
    </qg:hud>
    <qg:hud position="center" size="24">
      <qg:text value="{'3' if ticks() &lt; 90 else '2' if ticks() &lt; 150 else '1' if ticks() &lt; 210 else tr('GO!') if ticks() &lt; 270 else ''}" />
    </qg:hud>
  </qg:scene>

  <qg:scene name="flag" width="384" height="216" background="#1c2a1c">
    <qg:hud position="top-center" size="20" if="{winner == 1}">
      <qg:text value="{tr('RED') + ' ' + tr('WINS')}" color="#ff8070" />
    </qg:hud>
    <qg:hud position="top-center" size="20" if="{winner == 2}">
      <qg:text value="{tr('BLUE') + ' ' + tr('WINS')}" color="#88b0ff" />
    </qg:hud>
    <qg:hud position="center"><qg:icon sheet="cars" frame="{0 if winner == 1 else 3}" scale="4" /></qg:hud>
    <qg:menu position="bottom-center" size="12">
      <qg:button label="Again"><q:set name="winner" value="0" /><qg:goto-scene name="race" fade="0.3" /></qg:button>
      <qg:button label="To the title"><q:set name="winner" value="0" /><qg:leave /><qg:goto-scene name="title" /></qg:button>
    </qg:menu>
  </qg:scene>

  <!-- ===== Options: how loud, the full screen, the keys; kept between runs ===== -->

  <qg:scene name="options" width="384" height="216" background="#2c5a2a">
    <qg:hud position="top-center" size="24"><qg:text value="{tr('OPTIONS')}" /></qg:hud>
    <qg:menu position="center" size="12" columns="2" rows="4">
      <qg:slider label="Sounds" bus="effects" />
      <qg:button label="{tr('Full screen') + ': ' + (tr('on') if fullscreen() else tr('off'))}"><qg:fullscreen /></qg:button>
      <qg:rebind label="Red up" action="up" />
      <qg:rebind label="Blue up" action="up" player="2" />
      <qg:rebind label="Red down" action="down" />
      <qg:rebind label="Blue down" action="down" player="2" />
      <qg:rebind label="Red left" action="left" />
      <qg:rebind label="Blue left" action="left" player="2" />
      <qg:rebind label="Red right" action="right" />
      <qg:rebind label="Blue right" action="right" player="2" />
      <qg:button label="Back"><qg:goto-scene name="title" /></qg:button>
    </qg:menu>
  </qg:scene>

</q:application>
