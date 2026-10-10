<q:application id="rpg" type="game">

  <!-- RPG: Godot's "JRPG" demo (godotengine/godot-demo-projects, 2d/role_playing_game,
       MIT), transcribed. A slime walks a grassy map cell by cell, reads a key,
       talks to another slime and fights it, turn by turn: Attack, Defend, Flee.
       The art and the font are the demo's (assets/LICENSE.md), packed by
       scripts/art/rpg.py; README.md says what is where. -->

  <!-- How the last fight ended ('' before any), and the cell it was started from. -->
  <q:set name="outcome" value="" />
  <q:set name="back_col" value="3" type="number" />
  <q:set name="back_row" value="4" type="number" />
  <!-- Beyond the demo: what the player carries, and what it took from the map, by name. -->
  <q:set name="keys" value="0" type="number" />
  <q:set name="potions" value="0" type="number" />
  <q:set name="taken" value="[]" type="array" />

  <!-- The demo's ui_accept: Enter, Space, the joypad's A; and a click. -->
  <qg:input action="select" keys="Enter, Space, MouseLeft, JoyA" />

  <!-- Every tile of the three layers is a picture of its own; the Grid
       layer's are the ones that stop a walker. -->
  <qg:tileset name="world" src="assets/tiles.png" tile="64" />
  <qg:spritesheet name="pawns" src="assets/pawns.png" tile="64" />
  <qg:spritesheet name="fighters" src="assets/fighters.png" tile="128" />
  <qg:spritesheet name="arena" src="assets/arena.png" tile="1280x720" />

  <qg:prefab name="Opponent" tag="opponent" sheet="pawns" frame="2" hitbox="48x48" />
  <qg:prefab name="Key" tag="key" sheet="pawns" frame="3" hitbox="48x48" />
  <qg:prefab name="Potion" tag="potion" sheet="pawns" frame="4" hitbox="48x48" />

  <!-- ===== Exploration: grid_movement/exploration.tscn ===== -->

  <qg:scene name="exploration" width="1280" height="720" background="#62a033">
    <qg:tilemap tileset="world">
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0
    </qg:tilemap>
    <qg:tilemap tileset="world">
0,0,0,0,0,0,0,0,0,0,0,2,3,3,3,4,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,5,6,6,6,7,0,0,0,0
0,0,8,9,10,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,11,12,4,0,0,13,13,13,13,10,0,0,0,0,0,0,0,0
0,0,11,12,14,0,0,15,15,15,15,14,0,0,0,0,0,0,0,0
0,0,5,16,7,0,0,6,6,6,6,17,0,0,0,8,13,13,12,0
0,0,0,0,0,0,0,0,0,0,0,18,13,19,0,20,12,12,12,0
0,0,0,0,0,0,0,0,0,0,0,20,21,14,0,22,12,12,12,12
0,0,0,0,0,0,0,0,0,0,0,5,23,17,0,24,23,23,12,12
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
    </qg:tilemap>
    <qg:tilemap tileset="world" collision="true">
25,26,26,26,26,26,26,26,26,26,26,26,26,26,26,26,26,26,27,28
29,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,30,0,31,28
29,0,0,0,0,0,32,33,33,33,34,0,0,0,0,0,0,0,31,28
29,0,0,0,0,0,31,25,26,26,35,0,0,0,0,0,0,32,36,28
29,0,0,0,0,0,31,29,0,0,0,0,0,0,0,0,0,37,38,28
29,0,0,0,0,0,31,39,33,33,34,0,0,0,0,0,0,40,27,28
29,41,0,0,0,0,40,42,26,26,35,0,0,0,0,0,0,0,31,28
43,44,34,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,31,28
28,28,29,0,0,0,0,0,0,0,0,0,0,0,0,0,0,32,36,28
28,28,43,44,44,44,44,34,0,0,0,0,0,0,0,0,0,37,38,28
28,28,28,28,28,28,28,43,44,44,44,44,44,44,44,44,44,36,38,28
    </qg:tilemap>

    <qg:instance prefab="Key" name="key" x="544" y="288" if="{'key' not in taken}" />
    <qg:instance prefab="Potion" name="potion-1" x="96" y="96" if="{'potion-1' not in taken}" />
    <qg:instance prefab="Potion" name="potion-2" x="928" y="608" if="{'potion-2' not in taken}" />
    <qg:instance prefab="Opponent" x="800" y="480" />

    <qg:character id="player" controller="grid" diagonal="true" step-frames="15"
                  sheet="pawns" frame="0" x="224" y="288" hitbox="48x48">
      <qg:animation name="idle" frames="0" fps="1" />
      <qg:animation name="walk" frames="0" fps="1" />
      <qg:animation name="bump" frames="1" fps="1" />
      <qg:on-collision with="key">
        <q:set name="taken" value="{taken + [other.name]}" />
        <q:set name="keys" value="{keys + 1}" />
        <qg:destroy target="other" />
        <qg:say dialogue="key" />
      </qg:on-collision>
      <qg:on-collision with="potion">
        <q:set name="taken" value="{taken + [other.name]}" />
        <q:set name="potions" value="{potions + 1}" />
        <qg:destroy target="other" />
        <qg:say dialogue="potion" />
      </qg:on-collision>
      <qg:on-collision with="opponent">
        <q:set name="back_col" value="{me.col}" />
        <q:set name="back_row" value="{me.row}" />
        <qg:say dialogue="npc" />
      </qg:on-collision>
    </qg:character>

    <!-- dialogue/dialogue_data/*.json -->
    <qg:dialogue name="npc" font="assets/montserrat_extra_bold.otf" size="28">
      <qg:line who="UNKNOWN" text="Hey, it's a good time to have a JRPG fight, right?" />
      <qg:line who="UNKNOWN" text="Let me introduce myself, I'm your OPPONENT." />
      <qg:line who="OPPONENT" text="Enough talking. Let's fight!" />
      <qg:on-end>
        <qg:goto-scene name="combat" fade="0.4" />
      </qg:on-end>
    </qg:dialogue>
    <qg:dialogue name="key" font="assets/montserrat_extra_bold.otf" size="28">
      <qg:line who="PLAYER" text="Just a key..." />
      <qg:line who="PLAYER" text="I'll keep it anyway." />
    </qg:dialogue>
    <qg:dialogue name="potion" font="assets/montserrat_extra_bold.otf" size="28">
      <qg:line who="PLAYER" text="A potion! In a fight, it gives back 5 life." />
    </qg:dialogue>

    <!-- What the player carries. -->
    <qg:hud position="top-left" font="assets/montserrat_extra_bold.otf" size="24">
      <qg:counter bind="potions" label="Potions" />
      <qg:counter bind="keys" label="Keys" />
    </qg:hud>
    <qg:dialogue name="won" font="assets/montserrat_extra_bold.otf" size="28">
      <qg:line who="OPPONENT" text="Congratulations, you won!" />
      <qg:on-end><q:set name="outcome" value="" /></qg:on-end>
    </qg:dialogue>
    <qg:dialogue name="lost" font="assets/montserrat_extra_bold.otf" size="28">
      <qg:line who="OPPONENT" text="Aha! I won, maybe you can try again next time." />
      <qg:on-end><q:set name="outcome" value="" /></qg:on-end>
    </qg:dialogue>

    <!-- Back from a fight: where it started, and what the opponent says of it. -->
    <q:if condition="{outcome != ''}">
      <qg:put target="player" x="{back_col * 64 + 32}" y="{back_row * 64 + 32}" />
      <q:if condition="{outcome == 'won'}"><qg:say dialogue="won" /></q:if>
      <q:if condition="{outcome == 'lost'}"><qg:say dialogue="lost" /></q:if>
    </q:if>
  </qg:scene>

  <!-- ===== Combat: combat/combat.tscn, turn_queue.gd, combatant.gd, health.gd ===== -->

  <qg:scene name="combat" width="1280" height="720" background="#4a4a4a">
    <!-- player.tscn: 10 life, 2 damage, 1 defense, 1 base armor;
         opponent.tscn: 7 life, 3 damage, 1 defense, no armor. -->
    <q:set name="life" value="10" type="number" />
    <q:set name="armor" value="1" type="number" />
    <q:set name="foe_life" value="7" type="number" />
    <q:set name="foe_armor" value="0" type="number" />
    <q:set name="turn" value="player" />
    <q:set name="wait" value="0" type="number" />   <!-- the opponent's Timer: 0.25 s -->

    <!-- health.gd: a hit takes the damage less the armor. -->
    <q:function name="end" params="result">
      <q:set name="outcome" value="{result}" />
      <qg:goto-scene name="exploration" fade="0.4" />
    </q:function>
    <q:function name="foes_turn">
      <q:set name="turn" value="opponent" />
      <q:if condition="{foe_armor >= 0 + 1}"><q:set name="foe_armor" value="0" /></q:if>
      <q:set name="wait" value="15" />
    </q:function>

    <qg:sprite sheet="arena" x="640" y="360" />
    <qg:sprite sheet="fighters" frame="4" x="440" y="470" />
    <qg:sprite sheet="fighters" frame="4" x="840" y="470" />
    <qg:sprite sheet="fighters" frame="0" x="440" y="420" />
    <qg:sprite sheet="fighters" frame="2" x="840" y="420" />

    <qg:hud position="top-left" font="assets/montserrat_extra_bold.otf" size="32">
      <qg:text value="{'Player'}" />
      <qg:bar bind="life" max="10" width="320" height="20" color="#d81b60" />
    </qg:hud>
    <qg:hud position="top-right" font="assets/montserrat_extra_bold.otf" size="32">
      <qg:text value="{'Opponent'}" />
      <qg:bar bind="foe_life" max="7" width="320" height="20" color="#d81b60" />
    </qg:hud>

    <!-- ui.gd: the buttons work on the player's turn. -->
    <qg:menu position="bottom-center" font="assets/montserrat_extra_bold.otf" size="36"
             if="{turn == 'player'}">
      <qg:button label="Attack">
        <q:set name="foe_life" value="{foe_life - 2 + foe_armor}" />
        <qg:shake frames="10" strength="6" />
        <q:if condition="{foe_life <= 0}"><q:call function="end" args="'won'" /></q:if>
        <q:if condition="{foe_life > 0}"><q:call function="foes_turn" /></q:if>
      </qg:button>
      <qg:button label="Defend">
        <q:set name="armor" value="{armor + 1}" />
        <q:call function="foes_turn" />
      </qg:button>
      <!-- beyond the demo: a potion gives back 5 life (health.gd's heal, up to the most) -->
      <qg:button label="Potion" if="{potions > 0}">
        <q:set name="potions" value="{potions - 1}" />
        <q:set name="life" value="{min(10, life + 5)}" />
        <q:call function="foes_turn" />
      </qg:button>
      <qg:button label="Flee">
        <q:call function="end" args="'lost'" />
      </qg:button>
    </qg:menu>

    <!-- opponent.gd: a quarter of a second into its turn, it attacks. -->
    <qg:timer every="1">
      <q:if condition="{turn == 'opponent' and wait > 0}">
        <q:set name="wait" value="{wait - 1}" />
        <q:if condition="{wait == 0}">
          <q:set name="life" value="{life - 3 + armor}" />
          <qg:shake frames="10" strength="6" />
          <q:if condition="{life <= 0}"><q:call function="end" args="'lost'" /></q:if>
          <q:if condition="{life > 0}">
            <q:set name="turn" value="player" />
            <q:if condition="{armor >= 1 + 1}"><q:set name="armor" value="1" /></q:if>
          </q:if>
        </q:if>
      </q:if>
    </qg:timer>
  </qg:scene>

</q:application>
