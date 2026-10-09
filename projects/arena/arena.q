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
  <qg:multiplayer players="2" delay="3" start="fight" />

  <!-- The title: two on one keyboard, or one on each machine. -->
  <qg:scene name="title" width="640" height="360" background="#201820">
    <qg:sprite sheet="stage" x="320" y="180" />
    <qg:hud position="top-center" size="40"><qg:text value="{'ARENA'}" /></qg:hud>
    <qg:lobby local="fight" local-label="Two players, one keyboard" size="18" />
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

</q:application>
