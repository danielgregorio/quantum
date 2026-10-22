<q:application id="keep" type="game">

  <!-- Keep: the top-down adventure that drives the game language (PLAN_GAMES_2.md).
       Six rooms of a keep, seen from above. A character that walks in eight
       directions and swings a sword; slimes that wander and bats that chase;
       hearts; a key and a locked door; a switch that opens a gate in another
       room; a chest at the end. A title to start anew or continue: each
       room entered saves the game. The dungeon, the hero and the monsters are drawn
       for it by scripts/art/keep.py (CC0); the sounds are Kenney's Pixel
       Platformer (CC0). -->

  <!-- The game's state, kept across rooms. -->
  <q:set name="hearts" value="3" type="number" />
  <q:set name="keys" value="0" type="number" />
  <q:set name="taken" value="[]" type="array" />      <!-- things picked up, by name -->
  <q:set name="opened" value="[]" type="array" />     <!-- doors and gates opened, by name -->
  <q:set name="message" value="" />
  <!-- a new game: the state as the keep was found -->
  <q:function name="anew">
    <q:set name="hearts" value="3" />
    <q:set name="keys" value="0" />
    <q:set name="taken" value="[]" />
    <q:set name="opened" value="[]" />
    <q:set name="message" value="" />
  </q:function>
  <!-- three games, each kept apart (qg:save slot=): one goes on where it was, an empty one starts -->
  <q:function name="game_label" params="n">
    <q:return value="{tr('Game') + ' ' + str(n) + ': ' + (tr('go on') if has_save(n) else tr('new'))}" />
  </q:function>
  <q:function name="play" params="n">
    <q:if condition="{has_save(n)}">
      <qg:continue slot="{n}" />
      <q:else>
        <q:call function="anew" />
        <qg:save slot="{n}" scene="room-1" />
        <qg:goto-scene name="room-1" />
      </q:else>
    </q:if>
  </q:function>
  <!-- a hurt, the same in every room: a function of the game -->
  <q:function name="hurt" params="me">
    <qg:play sound="hurt" />
    <q:set name="hearts" value="{hearts - 1}" />
    <q:if condition="{hearts <= 0}">
      <qg:goto-scene name="game-over" />
    </q:if>
  </q:function>

  <!-- 1 is the floor (walked on: no collision), 2 the wall. -->
  <qg:tileset name="dungeon" src="assets/dungeon.png" tile="18">
    <qg:tile frame="0" shape="none" />
  </qg:tileset>
  <qg:spritesheet name="hero" src="assets/hero.png" tile="24" />

  <qg:sound name="hit" bus="effects" src="assets/kenney/audio/stomp.ogg" />
  <qg:sound name="hurt" bus="effects" src="assets/kenney/audio/hurt.ogg" />
  <qg:sound name="pick" bus="effects" src="assets/kenney/audio/coin.ogg" />
  <qg:sound name="open" bus="effects" src="assets/kenney/audio/block.ogg" />
  <qg:sound name="win" bus="effects" src="assets/kenney/audio/win.ogg" />

  <!-- on a phone: a stick to walk and a button for the sword, in every scene -->
  <qg:touch-stick x="40" y="184" />
  <qg:touch-button action="jump" label="A" x="220" y="184" />

  <!-- effects: only seen, the game's state never depends on them -->
  <qg:particles name="sparkle" preset="stars" color="#fff0a0" />
  <qg:particles name="slain" preset="smoke" color="#b0a0c0" />
  <qg:particles name="treasure" preset="confetti" />

  <qg:prefab name="Key" tag="key" sheet="dungeon" frame="8" hitbox="12x12" />
  <qg:prefab name="Heart" tag="heart" sheet="dungeon" frame="9" hitbox="12x12" />
  <qg:prefab name="Door" tag="door" sheet="dungeon" frame="2" hitbox="18x18" solid="true" />
  <qg:prefab name="Gate" tag="gate" sheet="dungeon" frame="3" hitbox="18x18" solid="true" />
  <qg:prefab name="Switch" tag="switch" sheet="dungeon" frame="4" hitbox="14x14" />
  <qg:prefab name="SwitchOn" tag="switch-on" sheet="dungeon" frame="5" hitbox="14x14" />
  <qg:prefab name="Sign" tag="sign" sheet="dungeon" frame="6" hitbox="18x18" solid="true" />
  <qg:prefab name="Chest" tag="chest" sheet="dungeon" frame="7" hitbox="16x16" />

  <qg:prefab name="Slime" tag="enemy" sheet="hero" frame="10" hitbox="14x14"
             ai="wander" speed="25">
    <qg:animation name="walk" frames="10,11,12,11" fps="6" />
  </qg:prefab>
  <qg:prefab name="Bat" tag="enemy" sheet="hero" frame="13" hitbox="14x14"
             ai="chase" speed="40" sight="90">
    <qg:animation name="walk" frames="13,14,15,14" fps="10" />
  </qg:prefab>

  <!-- the game in Portuguese and Spanish (a web page's ?lang=pt, the command line's q-lang, or the system's language) -->
  <qg:language lang="pt" name="Português">
    <qg:phrase text="HEARTS" as="CORAÇÕES" />
    <qg:phrase text="KEYS" as="CHAVES" />
    <qg:phrase text="THE KEY IS NORTH. THE SWITCH IS SOUTH." as="A CHAVE ESTÁ AO NORTE. A ALAVANCA, AO SUL." />
    <qg:phrase text="LOCKED. FIND THE KEY." as="TRANCADO. ACHE A CHAVE." />
    <qg:phrase text="SOMETHING OPENED FAR AWAY." as="ALGO SE ABRIU AO LONGE." />
    <qg:phrase text="A GATE. A SWITCH MUST OPEN IT." as="UM PORTÃO. UMA ALAVANCA DEVE ABRI-LO." />
    <qg:phrase text="THE TREASURE OF THE KEEP IS YOURS." as="O TESOURO DA FORTALEZA É SEU." />
    <qg:phrase text="YOU FELL. PRESS JUMP." as="VOCÊ CAIU. APERTE PULAR." />
    <qg:phrase text="New game" as="Novo jogo" />
    <qg:phrase text="Continue" as="Continuar" />
    <qg:phrase text="Language" as="Idioma" />
    <qg:phrase text="The keep is quiet again." as="A fortaleza está quieta outra vez." />
    <qg:phrase text="Once more" as="Mais uma vez" />
    <qg:phrase text="To the title" as="Para o início" />
      <qg:phrase text="Options" as="Opções" />
    <qg:phrase text="OPTIONS" as="OPÇÕES" />
    <qg:phrase text="Sounds" as="Sons" />
    <qg:phrase text="Full screen" as="Tela cheia" />
    <qg:phrase text="on" as="sim" />
    <qg:phrase text="off" as="não" />
    <qg:phrase text="Back" as="Voltar" />
    <qg:phrase text="Sword" as="Espada" />
    <qg:phrase text="Game" as="Jogo" />
    <qg:phrase text="go on" as="continuar" />
    <qg:phrase text="new" as="novo" />
</qg:language>
  <qg:language lang="es" name="Español">
    <qg:phrase text="HEARTS" as="CORAZONES" />
    <qg:phrase text="KEYS" as="LLAVES" />
    <qg:phrase text="THE KEY IS NORTH. THE SWITCH IS SOUTH." as="LA LLAVE ESTÁ AL NORTE. LA PALANCA, AL SUR." />
    <qg:phrase text="LOCKED. FIND THE KEY." as="CERRADO. BUSCA LA LLAVE." />
    <qg:phrase text="SOMETHING OPENED FAR AWAY." as="ALGO SE ABRIÓ A LO LEJOS." />
    <qg:phrase text="A GATE. A SWITCH MUST OPEN IT." as="UNA REJA. UNA PALANCA DEBE ABRIRLA." />
    <qg:phrase text="THE TREASURE OF THE KEEP IS YOURS." as="EL TESORO DE LA FORTALEZA ES TUYO." />
    <qg:phrase text="YOU FELL. PRESS JUMP." as="HAS CAÍDO. PULSA SALTAR." />
    <qg:phrase text="New game" as="Nueva partida" />
    <qg:phrase text="Continue" as="Continuar" />
    <qg:phrase text="Language" as="Idioma" />
    <qg:phrase text="The keep is quiet again." as="La fortaleza vuelve a estar en calma." />
    <qg:phrase text="Once more" as="Otra vez" />
    <qg:phrase text="To the title" as="Al inicio" />
      <qg:phrase text="Options" as="Opciones" />
    <qg:phrase text="OPTIONS" as="OPCIONES" />
    <qg:phrase text="Sounds" as="Sonidos" />
    <qg:phrase text="Full screen" as="Pantalla completa" />
    <qg:phrase text="on" as="sí" />
    <qg:phrase text="off" as="no" />
    <qg:phrase text="Back" as="Volver" />
    <qg:phrase text="Sword" as="Espada" />
    <qg:phrase text="Game" as="Partida" />
    <qg:phrase text="go on" as="seguir" />
    <qg:phrase text="new" as="nueva" />
</qg:language>

  <!-- ===== The title: a new game, or the saved one (each room entered saves it) ===== -->

  <qg:scene name="title" width="256" height="224" background="#2b2b3a">
    <qg:hud position="top-center" size="32"><qg:text value="{'KEEP'}" /></qg:hud>
    <qg:menu position="center" size="14">
      <qg:button label="{game_label(1)}"><q:call function="play" args="1" /></qg:button>
      <qg:button label="{game_label(2)}"><q:call function="play" args="2" /></qg:button>
      <qg:button label="{game_label(3)}"><q:call function="play" args="3" /></qg:button>
      <qg:button label="Options"><qg:goto-scene name="options" /></qg:button>
      <qg:button label="{tr('Language') + ': ' + language()}"><qg:next-language /></qg:button>
    </qg:menu>
  </qg:scene>

  <!-- ===== Options: how loud, the full screen, the sword's key; kept between runs ===== -->

  <qg:scene name="options" width="256" height="224" background="#2b2b3a">
    <qg:hud position="top-center" size="24"><qg:text value="{tr('OPTIONS')}" /></qg:hud>
    <qg:menu position="center" size="12">
      <qg:slider label="Sounds" bus="effects" />
      <qg:button label="{tr('Full screen') + ': ' + (tr('on') if fullscreen() else tr('off'))}"><qg:fullscreen /></qg:button>
      <qg:rebind label="Sword" action="jump" />
      <qg:button label="Back"><qg:goto-scene name="title" /></qg:button>
    </qg:menu>
  </qg:scene>

  <!-- ===== Room 1: the entrance. East to room 2. ===== -->

  <qg:scene name="room-1" width="256" height="224" background="#2b2b3a" seed="1" save="true">
    <qg:tilemap tileset="dungeon" collision="true">
2,2,2,2,2,2,2,2,2,2,2,2,2,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,1
2,1,1,1,1,1,1,1,1,1,1,1,1,1
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,2,2,2,2,2,2,2,2,2,2,2,2,2
    </qg:tilemap>

    <qg:character id="player" controller="topdown" sheet="hero" frame="0"
                  x="60" y="108" hitbox="14x14" speed="70"
                  attack-action="jump" attack-reach="16" attack-frames="12" attack-sound="hit">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1,2" fps="8" />
      <qg:animation name="walk-up" frames="3,4" fps="8" />
      <qg:animation name="walk-down" frames="5,6" fps="8" />
      <qg:animation name="attack" frames="7" />
      <qg:animation name="attack-up" frames="8" />
      <qg:animation name="attack-down" frames="9" />
      <qg:on-collision with="sign">
        <q:set name="message" value="THE KEY IS NORTH. THE SWITCH IS SOUTH." />
      </qg:on-collision>
      <qg:on-collision with="enemy" cooldown="60">
        <q:call function="hurt" args="me" />
      </qg:on-collision>
      <qg:on-hit with="enemy">
        <qg:emit particles="slain" at="other" />
        <qg:destroy target="other" />
      </qg:on-hit>
    </qg:character>

    <qg:instance prefab="Sign" x="99" y="63" />
    <qg:instance prefab="Slime" name="slime-1" x="180" y="150" if="{'slime-1' not in taken}" />

    <qg:exit name="east" x="252" y="99" width="8" height="36" to="room-2" at="west" />

    <qg:hud position="top-left">
      <qg:icon sheet="dungeon" frame="9" />
      <qg:counter bind="hearts" label="HEARTS" color="#ff8080" />
      <qg:icon sheet="dungeon" frame="8" />
      <qg:counter bind="keys" label="KEYS" color="#ffe070" />
    </qg:hud>
    <qg:hud position="bottom-left" if="{message != ''}"><qg:text bind="message" /></qg:hud>
  </qg:scene>

  <!-- ===== Room 2: the crossing. West to 1, north to 3, south to 4, east (locked) to 5. ===== -->

  <qg:scene name="room-2" width="256" height="224" background="#2b2b3a" seed="2" save="true">
    <qg:tilemap tileset="dungeon" collision="true">
2,2,2,2,2,2,1,1,2,2,2,2,2,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
1,1,1,1,1,1,1,1,1,1,1,1,1,1
1,1,1,1,1,1,1,1,1,1,1,1,1,1
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,2,2,2,2,2,1,1,2,2,2,2,2,2
    </qg:tilemap>

    <qg:character id="player" controller="topdown" sheet="hero" frame="0"
                  x="126" y="108" hitbox="14x14" speed="70"
                  attack-action="jump" attack-reach="16" attack-frames="12" attack-sound="hit">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1,2" fps="8" />
      <qg:animation name="walk-up" frames="3,4" fps="8" />
      <qg:animation name="walk-down" frames="5,6" fps="8" />
      <qg:animation name="attack" frames="7" />
      <qg:animation name="attack-up" frames="8" />
      <qg:animation name="attack-down" frames="9" />
      <qg:on-collision with="enemy" cooldown="60">
        <q:call function="hurt" args="me" />
      </qg:on-collision>
      <qg:on-hit with="enemy">
        <qg:emit particles="slain" at="other" />
        <qg:destroy target="other" />
      </qg:on-hit>
      <qg:on-collision with="door">
        <q:if condition="{keys > 0}">
          <q:set name="keys" value="{keys - 1}" />
          <q:set name="opened" value="{opened + [other.name]}" />
          <qg:play sound="open" />
          <qg:destroy target="other" />
        <q:else>
          <q:set name="message" value="LOCKED. FIND THE KEY." />
        </q:else>
        </q:if>
      </qg:on-collision>
    </qg:character>

    <qg:instance prefab="Bat" name="bat-1" x="190" y="60" if="{'bat-1' not in taken}" />
    <qg:instance prefab="Door" name="door-1" x="225" y="108" if="{'door-1' not in opened}" />

    <qg:exit name="west" x="-4" y="99" width="8" height="36" to="room-1" at="east" />
    <qg:exit name="north" x="117" y="-4" width="36" height="8" to="room-3" at="south" />
    <qg:exit name="south" x="117" y="220" width="36" height="8" to="room-4" at="north" />
    <qg:exit name="east" x="252" y="99" width="8" height="36" to="room-5" at="west" />

    <qg:hud position="top-left">
      <qg:icon sheet="dungeon" frame="9" />
      <qg:counter bind="hearts" label="HEARTS" color="#ff8080" />
      <qg:icon sheet="dungeon" frame="8" />
      <qg:counter bind="keys" label="KEYS" color="#ffe070" />
    </qg:hud>
    <qg:hud position="bottom-left" if="{message != ''}"><qg:text bind="message" /></qg:hud>
  </qg:scene>

  <!-- ===== Room 3: the key, guarded. South to 2. ===== -->

  <qg:scene name="room-3" width="256" height="224" background="#2b2b3a" seed="3" save="true">
    <qg:tilemap tileset="dungeon" collision="true">
2,2,2,2,2,2,2,2,2,2,2,2,2,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,2,2,1,1,2,2,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,2,2,1,1,2,2,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,2,2,2,2,2,1,1,2,2,2,2,2,2
    </qg:tilemap>

    <qg:character id="player" controller="topdown" sheet="hero" frame="0"
                  x="126" y="190" hitbox="14x14" speed="70"
                  attack-action="jump" attack-reach="16" attack-frames="12" attack-sound="hit">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1,2" fps="8" />
      <qg:animation name="walk-up" frames="3,4" fps="8" />
      <qg:animation name="walk-down" frames="5,6" fps="8" />
      <qg:animation name="attack" frames="7" />
      <qg:animation name="attack-up" frames="8" />
      <qg:animation name="attack-down" frames="9" />
      <qg:on-collision with="enemy" cooldown="60">
        <q:call function="hurt" args="me" />
      </qg:on-collision>
      <qg:on-hit with="enemy">
        <qg:emit particles="slain" at="other" />
        <qg:destroy target="other" />
      </qg:on-hit>
      <qg:on-collision with="key">
        <qg:play sound="pick" />
        <qg:emit particles="sparkle" at="other" />
        <q:set name="keys" value="{keys + 1}" />
        <q:set name="taken" value="{taken + [other.name]}" />
        <qg:destroy target="other" />
      </qg:on-collision>
      <qg:on-collision with="heart">
        <qg:play sound="pick" />
        <qg:emit particles="sparkle" at="other" />
        <q:set name="hearts" value="{hearts + 1}" />
        <q:set name="taken" value="{taken + [other.name]}" />
        <qg:destroy target="other" />
      </qg:on-collision>
    </qg:character>

    <qg:instance prefab="Key" name="key-1" x="126" y="99" if="{'key-1' not in taken}" />
    <qg:instance prefab="Heart" name="heart-1" x="45" y="45" if="{'heart-1' not in taken}" />
    <!-- what can be picked up breathes, so the eye finds it (only its picture: where it is stays) -->
    <qg:timer after="1">
      <qg:tween target="key-1" property="scale" to="1.3" seconds="0.6" repeat="-1" yoyo="true" />
      <qg:tween target="heart-1" property="scale" to="1.3" seconds="0.6" repeat="-1" yoyo="true" />
    </qg:timer>
    <qg:instance prefab="Slime" name="slime-3" x="190" y="99" if="{'slime-3' not in taken}" />

    <qg:exit name="south" x="117" y="220" width="36" height="8" to="room-2" at="north" />

    <qg:hud position="top-left">
      <qg:icon sheet="dungeon" frame="9" />
      <qg:counter bind="hearts" label="HEARTS" color="#ff8080" />
      <qg:icon sheet="dungeon" frame="8" />
      <qg:counter bind="keys" label="KEYS" color="#ffe070" />
    </qg:hud>
    <qg:hud position="bottom-left" if="{message != ''}"><qg:text bind="message" /></qg:hud>
  </qg:scene>

  <!-- ===== Room 4: the switch. North to 2. ===== -->

  <qg:scene name="room-4" width="256" height="224" background="#2b2b3a" seed="4" save="true">
    <qg:tilemap tileset="dungeon" collision="true">
2,2,2,2,2,2,1,1,2,2,2,2,2,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,2,2,2,2,2,2,2,2,2,2,2,2,2
    </qg:tilemap>

    <qg:character id="player" controller="topdown" sheet="hero" frame="0"
                  x="126" y="36" hitbox="14x14" speed="70"
                  attack-action="jump" attack-reach="16" attack-frames="12" attack-sound="hit">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1,2" fps="8" />
      <qg:animation name="walk-up" frames="3,4" fps="8" />
      <qg:animation name="walk-down" frames="5,6" fps="8" />
      <qg:animation name="attack" frames="7" />
      <qg:animation name="attack-up" frames="8" />
      <qg:animation name="attack-down" frames="9" />
      <qg:on-collision with="enemy" cooldown="60">
        <q:call function="hurt" args="me" />
      </qg:on-collision>
      <qg:on-hit with="enemy">
        <qg:emit particles="slain" at="other" />
        <qg:destroy target="other" />
      </qg:on-hit>
      <qg:on-hit with="switch">
        <qg:play sound="open" />
        <q:set name="opened" value="{opened + ['gate-1']}" />
        <q:set name="message" value="SOMETHING OPENED FAR AWAY." />
        <qg:swap target="other" prefab="SwitchOn" />
      </qg:on-hit>
    </qg:character>

    <qg:instance prefab="Switch" x="126" y="171" if="{'gate-1' not in opened}" />
    <qg:instance prefab="SwitchOn" x="126" y="171" if="{'gate-1' in opened}" />
    <qg:instance prefab="Bat" name="bat-2" x="60" y="150" if="{'bat-2' not in taken}" />

    <qg:exit name="north" x="117" y="-4" width="36" height="8" to="room-2" at="south" />

    <qg:hud position="top-left">
      <qg:icon sheet="dungeon" frame="9" />
      <qg:counter bind="hearts" label="HEARTS" color="#ff8080" />
      <qg:icon sheet="dungeon" frame="8" />
      <qg:counter bind="keys" label="KEYS" color="#ffe070" />
    </qg:hud>
    <qg:hud position="bottom-left" if="{message != ''}"><qg:text bind="message" /></qg:hud>
  </qg:scene>

  <!-- ===== Room 5: behind the locked door; the gate the switch opens. West to 2, east to 6. ===== -->

  <qg:scene name="room-5" width="256" height="224" background="#2b2b3a" seed="5" save="true">
    <qg:tilemap tileset="dungeon" collision="true">
2,2,2,2,2,2,2,2,2,2,2,2,2,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,2,2,2,2,2
1,1,1,1,1,1,1,1,1,1,1,1,1,1
1,1,1,1,1,1,1,1,1,1,1,1,1,1
2,1,1,1,1,1,1,1,1,2,2,2,2,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,2,2,2,2,2,2,2,2,2,2,2,2,2
    </qg:tilemap>

    <qg:character id="player" controller="topdown" sheet="hero" frame="0"
                  x="36" y="108" hitbox="14x14" speed="70"
                  attack-action="jump" attack-reach="16" attack-frames="12" attack-sound="hit">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1,2" fps="8" />
      <qg:animation name="walk-up" frames="3,4" fps="8" />
      <qg:animation name="walk-down" frames="5,6" fps="8" />
      <qg:animation name="attack" frames="7" />
      <qg:animation name="attack-up" frames="8" />
      <qg:animation name="attack-down" frames="9" />
      <qg:on-collision with="enemy" cooldown="60">
        <q:call function="hurt" args="me" />
      </qg:on-collision>
      <qg:on-hit with="enemy">
        <qg:emit particles="slain" at="other" />
        <qg:destroy target="other" />
      </qg:on-hit>
      <qg:on-collision with="gate">
        <q:set name="message" value="A GATE. A SWITCH MUST OPEN IT." />
      </qg:on-collision>
    </qg:character>

    <!-- The gate stands in the corridor until the switch in room 4 is thrown. -->
    <qg:instance prefab="Gate" name="gate-1" x="171" y="99" if="{'gate-1' not in opened}" />
    <qg:instance prefab="Gate" name="gate-1b" x="171" y="117" if="{'gate-1' not in opened}" />
    <qg:instance prefab="Slime" name="slime-4" x="90" y="60" if="{'slime-4' not in taken}" />

    <qg:exit name="west" x="-4" y="99" width="8" height="36" to="room-2" at="east" />
    <qg:exit name="east" x="252" y="99" width="8" height="36" to="room-6" at="west" />

    <qg:hud position="top-left">
      <qg:icon sheet="dungeon" frame="9" />
      <qg:counter bind="hearts" label="HEARTS" color="#ff8080" />
      <qg:icon sheet="dungeon" frame="8" />
      <qg:counter bind="keys" label="KEYS" color="#ffe070" />
    </qg:hud>
    <qg:hud position="bottom-left" if="{message != ''}"><qg:text bind="message" /></qg:hud>
  </qg:scene>

  <!-- ===== Room 6: the chest. ===== -->

  <qg:scene name="room-6" width="256" height="224" background="#2b2b3a" seed="6" save="true">
    <qg:tilemap tileset="dungeon" collision="true">
2,2,2,2,2,2,2,2,2,2,2,2,2,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
1,1,1,1,1,1,1,1,1,1,1,1,1,2
1,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,1,1,1,1,1,1,1,1,1,1,1,1,2
2,2,2,2,2,2,2,2,2,2,2,2,2,2
    </qg:tilemap>

    <qg:character id="player" controller="topdown" sheet="hero" frame="0"
                  x="36" y="108" hitbox="14x14" speed="70"
                  attack-action="jump" attack-reach="16" attack-frames="12" attack-sound="hit">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="1,2" fps="8" />
      <qg:animation name="walk-up" frames="3,4" fps="8" />
      <qg:animation name="walk-down" frames="5,6" fps="8" />
      <qg:animation name="attack" frames="7" />
      <qg:animation name="attack-up" frames="8" />
      <qg:animation name="attack-down" frames="9" />
      <qg:on-collision with="chest">
        <qg:play sound="win" />
        <qg:emit particles="treasure" at="other" />
        <q:set name="message" value="THE TREASURE OF THE KEEP IS YOURS." />
        <qg:goto-scene name="the-end" />
      </qg:on-collision>
    </qg:character>

    <qg:instance prefab="Chest" name="chest" x="190" y="108" />
    <qg:timer after="1">
      <qg:tween target="chest" property="rotation" from="-8" to="8" seconds="0.4" repeat="-1" yoyo="true" />
    </qg:timer>

    <qg:exit name="west" x="-4" y="99" width="8" height="36" to="room-5" at="east" />

    <qg:hud position="top-left">
      <qg:icon sheet="dungeon" frame="9" />
      <qg:counter bind="hearts" label="HEARTS" color="#ff8080" />
      <qg:icon sheet="dungeon" frame="8" />
      <qg:counter bind="keys" label="KEYS" color="#ffe070" />
    </qg:hud>
    <qg:hud position="bottom-left" if="{message != ''}"><qg:text bind="message" /></qg:hud>
  </qg:scene>

  <!-- ===== The end, and the game over ===== -->

  <qg:scene name="the-end" width="256" height="224" background="#102030">
    <qg:hud position="top-center">
      <qg:text bind="message" />
    </qg:hud>
    <!-- a moment later, what now: the keep again, or the title -->
    <qg:dialogue name="end" size="12" speed="30">
      <qg:line who="KEEP" text="The keep is quiet again.">
        <qg:choice label="Once more"><q:call function="anew" /><qg:goto-scene name="room-1" /></qg:choice>
        <qg:choice label="To the title"><qg:goto-scene name="title" /></qg:choice>
      </qg:line>
    </qg:dialogue>
    <qg:timer after="90"><qg:say dialogue="end" /></qg:timer>
  </qg:scene>

  <qg:scene name="game-over" width="256" height="224" background="#000000">
    <q:set name="title" value="YOU FELL. PRESS JUMP." />
    <qg:on-input action="jump">
      <q:call function="anew" />
      <qg:goto-scene name="room-1" />
    </qg:on-input>
    <qg:hud position="top-center">
      <qg:text bind="title" />
    </qg:hud>
  </qg:scene>

</q:application>
