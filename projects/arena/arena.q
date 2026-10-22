<q:application id="arena" type="game">

  <!-- Arena: a one-on-one fighting game in the shape of the arcade classics —
       two fighters, walk, jump, crouch, block, a punch and a kick with frame
       data, best of three rounds on a clock — written to see what a fighting
       game asks of the language, and played by two over the network in
       lockstep, which is the fighting games' own netcode. The sprites are
       placeholders drawn for the repository (assets/LICENSE.md). -->

  <q:set name="wins_1" value="0" type="number" />
  <q:set name="wins_2" value="0" type="number" />

  <qg:spritesheet name="red" src="assets/red.png" tile="64x96" />
  <qg:spritesheet name="blue" src="assets/blue.png" tile="64x96" />
  <qg:spritesheet name="stage" src="assets/stage.png" tile="640x360" />

  <!-- Player 1: A/D, W to jump, S to crouch, J punch, K kick. Player 2 on the
       same keyboard: the arrows, . punch, / kick. Over the network each peer
       is one player on player 1's keys. -->
  <qg:input action="jump" keys="W, Space, JoyA" />
  <qg:input action="punch" keys="J, JoyX" />
  <qg:input action="kick" keys="K, JoyB" />
  <qg:input player="2" action="left" keys="Left" />
  <qg:input player="2" action="right" keys="Right" />
  <qg:input player="2" action="down" keys="Down" />
  <qg:input player="2" action="jump" keys="Up" />
  <qg:input player="2" action="punch" keys="Period" />
  <qg:input player="2" action="kick" keys="Slash" />
  <qg:multiplayer players="2" delay="2" rollback="8" start="fight" />

  <!-- the game in Portuguese and Spanish (a web page's ?lang=pt, the command line's q-lang, or the system's language) -->
    <!-- on a phone: what the keys do, under a finger, in every scene -->
  <qg:touch-stick x="70" y="290" size="96" />
  <qg:touch-button action="punch" label="P" x="520" y="300" size="64" />
  <qg:touch-button action="kick" label="K" x="595" y="250" size="64" />
  <qg:touch-button action="jump" label="J" x="595" y="325" size="48" />

  <qg:language lang="pt" name="Português">
    <qg:phrase text="ARENA" as="ARENA" />
    <qg:phrase text="Two players, one keyboard" as="Dois jogadores, um teclado" />
    <qg:phrase text="ROUND 1 - FIGHT" as="ROUND 1 - LUTEM" />
    <qg:phrase text="ROUND 2 - FIGHT" as="ROUND 2 - LUTEM" />
    <qg:phrase text="ROUND 3 - FIGHT" as="ROUND 3 - LUTEM" />
    <qg:phrase text="PLAYER 1 WINS THE ROUND" as="JOGADOR 1 VENCE O ROUND" />
    <qg:phrase text="PLAYER 2 WINS THE ROUND" as="JOGADOR 2 VENCE O ROUND" />
    <qg:phrase text="TIME - PLAYER 1 TAKES THE ROUND" as="TEMPO - O ROUND É DO JOGADOR 1" />
    <qg:phrase text="TIME - PLAYER 2 TAKES THE ROUND" as="TEMPO - O ROUND É DO JOGADOR 2" />
    <qg:phrase text="PLAYER 1 WINS - press jump" as="JOGADOR 1 VENCE - aperte pular" />
    <qg:phrase text="PLAYER 2 WINS - press jump" as="JOGADOR 2 VENCE - aperte pular" />
    <qg:phrase text="P1 rounds" as="Rounds J1" />
    <qg:phrase text="P2 rounds" as="Rounds J2" />
      <qg:phrase text="OPTIONS" as="OPÇÕES" />
    <qg:phrase text="Full screen" as="Tela cheia" />
    <qg:phrase text="on" as="sim" />
    <qg:phrase text="off" as="não" />
    <qg:phrase text="Back" as="Voltar" />
    <qg:phrase text="P1 punch" as="J1 soco" />
    <qg:phrase text="P2 punch" as="J2 soco" />
    <qg:phrase text="P1 kick" as="J1 chute" />
    <qg:phrase text="P2 kick" as="J2 chute" />
    <qg:phrase text="P1 jump" as="J1 pulo" />
    <qg:phrase text="P2 jump" as="J2 pulo" />
    <qg:phrase text="P1 crouch" as="J1 agachar" />
    <qg:phrase text="P2 crouch" as="J2 agachar" />
</qg:language>
  <qg:language lang="es" name="Español">
    <qg:phrase text="ARENA" as="ARENA" />
    <qg:phrase text="Two players, one keyboard" as="Dos jugadores, un teclado" />
    <qg:phrase text="ROUND 1 - FIGHT" as="ASALTO 1 - A PELEAR" />
    <qg:phrase text="ROUND 2 - FIGHT" as="ASALTO 2 - A PELEAR" />
    <qg:phrase text="ROUND 3 - FIGHT" as="ASALTO 3 - A PELEAR" />
    <qg:phrase text="PLAYER 1 WINS THE ROUND" as="EL JUGADOR 1 GANA EL ASALTO" />
    <qg:phrase text="PLAYER 2 WINS THE ROUND" as="EL JUGADOR 2 GANA EL ASALTO" />
    <qg:phrase text="TIME - PLAYER 1 TAKES THE ROUND" as="TIEMPO - EL ASALTO ES DEL JUGADOR 1" />
    <qg:phrase text="TIME - PLAYER 2 TAKES THE ROUND" as="TIEMPO - EL ASALTO ES DEL JUGADOR 2" />
    <qg:phrase text="PLAYER 1 WINS - press jump" as="GANA EL JUGADOR 1 - pulsa saltar" />
    <qg:phrase text="PLAYER 2 WINS - press jump" as="GANA EL JUGADOR 2 - pulsa saltar" />
    <qg:phrase text="P1 rounds" as="Asaltos J1" />
    <qg:phrase text="P2 rounds" as="Asaltos J2" />
      <qg:phrase text="OPTIONS" as="OPCIONES" />
    <qg:phrase text="Full screen" as="Pantalla completa" />
    <qg:phrase text="on" as="sí" />
    <qg:phrase text="off" as="no" />
    <qg:phrase text="Back" as="Volver" />
    <qg:phrase text="P1 punch" as="J1 puñetazo" />
    <qg:phrase text="P2 punch" as="J2 puñetazo" />
    <qg:phrase text="P1 kick" as="J1 patada" />
    <qg:phrase text="P2 kick" as="J2 patada" />
    <qg:phrase text="P1 jump" as="J1 salto" />
    <qg:phrase text="P2 jump" as="J2 salto" />
    <qg:phrase text="P1 crouch" as="J1 agacharse" />
    <qg:phrase text="P2 crouch" as="J2 agacharse" />
</qg:language>

  <!-- The title: two on one keyboard, or one on each machine. -->
  <qg:scene name="title" width="640" height="360" background="#201820">
    <qg:sprite sheet="stage" x="320" y="180" />
    <qg:hud position="top-center" size="40"><qg:text value="{'ARENA'}" /></qg:hud>
    <qg:lobby local="fight" local-label="Two players, one keyboard" size="18" options="options" />
  </qg:scene>

  <qg:scene name="fight" width="640" height="360" background="#201820" seed="1">
    <q:set name="wins_1" value="0" />
    <q:set name="wins_2" value="0" />
    <q:set name="round" value="1" type="number" />
    <q:set name="clock" value="99" type="number" />
    <q:set name="message" value="ROUND 1 - FIGHT" />
    <q:set name="reset_in" value="0" type="number" />

    <qg:sprite sheet="stage" x="320" y="180" />

    <qg:character id="p1" controller="fighter" player="1" sheet="red" frame="0" x="200" y="252" hitbox="40x90"
                  speed="140" jump-height="100" health="100" facing="right">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1, 2" fps="8" />
      <qg:animation name="jump" frames="3" />
      <qg:animation name="crouch" frames="4" />
      <qg:animation name="block" frames="5" />
      <qg:animation name="hit" frames="12" />
      <qg:animation name="ko" frames="13" />
      <qg:move name="punch" action="punch" frames="6, 7, 8" fps="15" active="1" reach="36x20" at="40,-10" damage="8" stun="14" push="40" />
      <qg:move name="kick" action="kick" frames="9, 10, 11" fps="10" active="1" reach="44x20" at="44,8" damage="12" stun="20" push="70" />
      <qg:on-ko>
        <q:set name="wins_2" value="{wins_2 + 1}" />
        <q:set name="message" value="PLAYER 2 WINS THE ROUND" />
        <q:set name="reset_in" value="120" />
      </qg:on-ko>
    </qg:character>
    <qg:character id="p2" controller="fighter" player="2" sheet="blue" frame="0" x="440" y="252" hitbox="40x90"
                  speed="140" jump-height="100" health="100" facing="left">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1, 2" fps="8" />
      <qg:animation name="jump" frames="3" />
      <qg:animation name="crouch" frames="4" />
      <qg:animation name="block" frames="5" />
      <qg:animation name="hit" frames="12" />
      <qg:animation name="ko" frames="13" />
      <qg:move name="punch" action="punch" frames="6, 7, 8" fps="15" active="1" reach="36x20" at="40,-10" damage="8" stun="14" push="40" />
      <qg:move name="kick" action="kick" frames="9, 10, 11" fps="10" active="1" reach="44x20" at="44,8" damage="12" stun="20" push="70" />
      <qg:on-ko>
        <q:set name="wins_1" value="{wins_1 + 1}" />
        <q:set name="message" value="PLAYER 1 WINS THE ROUND" />
        <q:set name="reset_in" value="120" />
      </qg:on-ko>
    </qg:character>

    <!-- The clock: a second a second; at zero the healthier fighter takes the round. -->
    <qg:timer every="60">
      <q:if condition="{clock > 0 and reset_in == 0}">
        <q:set name="clock" value="{clock - 1}" />
        <q:if condition="{clock == 0}">
          <q:if condition="{p1.health >= p2.health}">
            <q:set name="wins_1" value="{wins_1 + 1}" />
            <q:set name="message" value="TIME - PLAYER 1 TAKES THE ROUND" />
          <q:else>
            <q:set name="wins_2" value="{wins_2 + 1}" />
            <q:set name="message" value="TIME - PLAYER 2 TAKES THE ROUND" />
          </q:else>
          </q:if>
          <q:set name="reset_in" value="120" />
        </q:if>
      </q:if>
    </qg:timer>
    <!-- Between rounds: two seconds of the message, then both back at their marks,
         or the match's end at two rounds. -->
    <qg:timer every="1">
      <q:if condition="{reset_in > 0}">
        <q:set name="reset_in" value="{reset_in - 1}" />
        <q:if condition="{reset_in == 0}">
          <q:if condition="{wins_1 >= 2 or wins_2 >= 2}">
            <qg:goto-scene name="result" />
          </q:if>
          <q:set name="round" value="{round + 1}" />
          <q:set name="clock" value="99" />
          <q:set name="message" value="{'ROUND ' + str(round) + ' - FIGHT'}" />
          <q:call function="reset_fighters" />
        </q:if>
      </q:if>
    </qg:timer>
    <q:function name="reset_fighters">
      <qg:respawn target="p1" />
      <qg:respawn target="p2" />
    </q:function>
    <qg:hud position="top-left" size="12">
      <qg:bar bind="p1.health" max="100" width="200" height="12" color="#e04040" />
      <qg:counter bind="wins_1" label="P1 rounds" />
    </qg:hud>
    <qg:hud position="top-right" size="12">
      <qg:bar bind="p2.health" max="100" width="200" height="12" color="#4060e0" />
      <qg:counter bind="wins_2" label="P2 rounds" />
    </qg:hud>
    <qg:hud position="top-center" size="16">
      <qg:counter bind="clock" />
      <qg:text bind="message" />
    </qg:hud>
  </qg:scene>

  <qg:scene name="result" width="640" height="360" background="#101018">
    <q:set name="message" value="{'PLAYER ' + ('1' if wins_1 > wins_2 else '2') + ' WINS - press jump'}" />
    <qg:hud position="center" size="24"><qg:text bind="message" /></qg:hud>
    <qg:on-input action="jump"><qg:goto-scene name="fight" /></qg:on-input>
  </qg:scene>

  <!-- ===== Options: how loud, the full screen, the keys; kept between runs ===== -->

  <qg:scene name="options" width="640" height="360" background="#201820">
    <qg:hud position="top-center" size="32"><qg:text value="{tr('OPTIONS')}" /></qg:hud>
    <qg:menu position="center" size="16" columns="2" rows="4">
      <qg:rebind label="P1 punch" action="punch" />
      <qg:rebind label="P2 punch" action="punch" player="2" />
      <qg:rebind label="P1 kick" action="kick" />
      <qg:rebind label="P2 kick" action="kick" player="2" />
      <qg:rebind label="P1 jump" action="jump" />
      <qg:rebind label="P2 jump" action="jump" player="2" />
      <qg:rebind label="P1 crouch" action="down" />
      <qg:rebind label="P2 crouch" action="down" player="2" />
      <qg:button label="{tr('Full screen') + ': ' + (tr('on') if fullscreen() else tr('off'))}"><qg:fullscreen /></qg:button>
      <qg:button label="Back"><qg:goto-scene name="title" /></qg:button>
    </qg:menu>
  </qg:scene>

</q:application>
