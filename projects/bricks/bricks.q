<q:application id="bricks" type="game">

  <!-- Bricks: a brick breaker, alone or for two to four over the network.
       A paddle (one each, over the network) keeps a ball in play, and the
       ball breaks the bricks it hits. Steel bricks take two hits, a bomb
       brick breaks the bricks around it, and the last brick of a level
       breaks in slow motion. Each level is a few lines of text, one letter
       a brick. The art is drawn by scripts/art/bricks.py (CC0); the sounds
       are Kenney's Pixel Platformer (CC0). -->

  <q:set name="score" value="0" type="number" />
  <q:set name="lives" value="3" type="number" />
  <q:set name="level" value="1" type="number" />
  <!-- what each player is called, over the network: the names they send -->
  <q:set name="names" type="array" value='["", "", "", ""]' />
  <!-- the levels, nine bricks to a row: R O Y G B the colours (one hit), S steel
       (two), X a bomb, . none -->
  <q:set name="levels" type="array" value='[
    ["RRRRRRRRR", "OOOOOOOOO", "YYYYXYYYY", "GGGGGGGGG", "BBBBBBBBB"],
    ["S.S.S.S.S", "RRRRRRRRR", "OOXOOOXOO", "YYYYYYYYY", ".GGGGGGG.", "..BBBBB.."],
    ["SSSSSSSSS", "R.XRRRX.R", "OOOOOOOOO", "YSYYXYYSY", "GGGGGGGGG", "BBBXBXBBB", "S.......S"]
  ]' />

  <qg:spritesheet name="bricks" src="assets/bricks.png" tile="32x12" />
  <qg:spritesheet name="paddles" src="assets/paddles.png" tile="48x8" />
  <qg:spritesheet name="ball" src="assets/ball.png" tile="8" />

  <qg:sound bus="effects" name="bounce" src="assets/kenney/audio/jump.ogg" />
  <qg:sound bus="effects" name="break" src="assets/kenney/audio/block.ogg" />
  <qg:sound bus="effects" name="clank" src="assets/kenney/audio/stomp.ogg" />
  <qg:sound bus="effects" name="boom" src="assets/kenney/audio/powerup.ogg" />
  <qg:sound bus="effects" name="lost" src="assets/kenney/audio/hurt.ogg" />
  <qg:sound bus="effects" name="clear" src="assets/kenney/audio/win.ogg" />

  <!-- The serve: Space, Up, W or the joypad's A, as it is let go. -->
  <qg:input action="jump" keys="Space, Up, W, JoyA" />

  <!-- Two to four players, each on their own machine. The game starts as the
       fourth joins, or when the host chooses to start with two or three:
       first who is who, then the first level. -->
  <qg:multiplayer players="4" min-players="2" start="names" />

  <!-- A player's name, or "Player 2" until they give one. -->
  <q:function name="who" params="n">
    <q:if condition="{names[n - 1] == ''}"><q:return value="{tr('Player') + ' ' + str(n)}" /></q:if>
    <q:return value="{names[n - 1]}" />
  </q:function>

  <!-- The ball flies at 150 px/s, a little faster every second. It bounces
       off the sides and the top, and off a brick by the side it hit, which
       takes a hit; the ball flashes as it does. -->
  <qg:prefab name="Ball" tag="ball" sheet="ball" hitbox="8x8" ai="fly" heading="0.4,-1" speed="150" accel="1">
    <qg:on-collision with="side">
      <qg:deflect target="me" axis="x" />
      <qg:play sound="bounce" volume="-8" vary="0.1" />
    </qg:on-collision>
    <qg:on-collision with="top">
      <qg:deflect target="me" axis="y" />
      <qg:play sound="bounce" volume="-8" vary="0.1" />
    </qg:on-collision>
    <qg:on-collision with="brick">
      <q:if condition="{abs(me.x - other.x) > 16}">
        <qg:deflect target="me" axis="x" />
        <q:else><qg:deflect target="me" axis="y" /></q:else>
      </q:if>
      <qg:tween target="me" property="tint" from="#ffd060" to="#ffffff" seconds="0.3" />
      <qg:damage target="other" amount="1" />
    </qg:on-collision>
    <qg:on-collision with="bomb">
      <qg:deflect target="me" axis="y" />
      <qg:tween target="me" property="tint" from="#ff5040" to="#ffffff" seconds="0.5" />
      <qg:damage target="other" amount="1" />
    </qg:on-collision>
  </qg:prefab>

  <!-- The bricks: five colours of one hit, steel of two (cracked after the
       first), and the bomb, which breaks the bricks around it (the level's
       qg:on-death of="bomb"). -->
  <qg:prefab name="Red" tag="brick" sheet="bricks" frame="0" hitbox="32x12">
    <qg:on-death>
      <qg:play sound="break" vary="0.2" />
      <qg:burst at="me" color="#d64040" count="10" />
      <q:set name="score" value="{score + 50}" />
    </qg:on-death>
  </qg:prefab>
  <qg:prefab name="Orange" tag="brick" sheet="bricks" frame="1" hitbox="32x12">
    <qg:on-death>
      <qg:play sound="break" vary="0.2" />
      <qg:burst at="me" color="#e88030" count="10" />
      <q:set name="score" value="{score + 40}" />
    </qg:on-death>
  </qg:prefab>
  <qg:prefab name="Yellow" tag="brick" sheet="bricks" frame="2" hitbox="32x12">
    <qg:on-death>
      <qg:play sound="break" vary="0.2" />
      <qg:burst at="me" color="#ecc838" count="10" />
      <q:set name="score" value="{score + 30}" />
    </qg:on-death>
  </qg:prefab>
  <qg:prefab name="Green" tag="brick" sheet="bricks" frame="3" hitbox="32x12">
    <qg:on-death>
      <qg:play sound="break" vary="0.2" />
      <qg:burst at="me" color="#58b858" count="10" />
      <q:set name="score" value="{score + 20}" />
    </qg:on-death>
  </qg:prefab>
  <qg:prefab name="Blue" tag="brick" sheet="bricks" frame="4" hitbox="32x12">
    <qg:on-death>
      <qg:play sound="break" vary="0.2" />
      <qg:burst at="me" color="#4884dc" count="10" />
      <q:set name="score" value="{score + 10}" />
    </qg:on-death>
  </qg:prefab>
  <qg:prefab name="Steel" tag="brick" sheet="bricks" frame="5" hitbox="32x12" health="2">
    <qg:state name="whole" frame="5" initial="true" />
    <qg:state name="cracked" frame="6" />
    <qg:on-damage>
      <qg:play sound="clank" />
      <qg:become target="me" state="cracked" />
    </qg:on-damage>
    <qg:on-death>
      <qg:play sound="break" pitch="0.8" />
      <qg:burst at="me" color="#969cac" count="16" />
      <q:set name="score" value="{score + 80}" />
    </qg:on-death>
  </qg:prefab>
  <qg:prefab name="Bomb" tag="bomb" sheet="bricks" frame="7" hitbox="32x12">
    <qg:on-death>
      <qg:play sound="boom" />
      <qg:burst at="me" color="#ff7040" count="24" />
      <q:set name="score" value="{score + 100}" />
    </qg:on-death>
  </qg:prefab>

  <!-- the game in Portuguese and Spanish (a web page's ?lang=pt, the command line's q-lang, or the system's language) -->
    <!-- on a phone: what the keys do, under a finger, in every scene -->
  <qg:touch-button action="left" label="&lt;" x="34" y="206" size="48" />
  <qg:touch-button action="right" label="&gt;" x="90" y="206" size="48" />
  <qg:touch-button action="jump" label="A" x="286" y="206" size="48" />

  <qg:language lang="pt" name="Português">
    <qg:phrase text="BRICKS" as="TIJOLOS" />
    <qg:phrase text="Play alone" as="Jogar sozinho" />
    <qg:phrase text="Play together" as="Jogar junto" />
    <qg:phrase text="Quit" as="Sair" />
    <qg:phrase text="Language" as="Idioma" />
    <qg:phrase text="To the title" as="Para o título" />
    <qg:phrase text="SCORE" as="PONTOS" />
    <qg:phrase text="LIVES" as="VIDAS" />
    <qg:phrase text="LEVEL" as="FASE" />
    <qg:phrase text="SPACE: SERVE" as="ESPAÇO: SACAR" />
    <qg:phrase text="TWO TO FOUR PLAYERS, EACH ON THEIR OWN MACHINE" as="DE DOIS A QUATRO JOGADORES, CADA UM NA SUA MÁQUINA" />
    <qg:phrase text="EVERY BRICK IS BROKEN" as="TODOS OS TIJOLOS QUEBRADOS" />
    <qg:phrase text="THE BALLS ARE GONE" as="AS BOLAS ACABARAM" />
      <qg:phrase text="Options" as="Opções" />
    <qg:phrase text="OPTIONS" as="OPÇÕES" />
    <qg:phrase text="Sounds" as="Sons" />
    <qg:phrase text="Full screen" as="Tela cheia" />
    <qg:phrase text="on" as="sim" />
    <qg:phrase text="off" as="não" />
    <qg:phrase text="Back" as="Voltar" />
    <qg:phrase text="Serve" as="Sacar" />
    <qg:phrase text="Left" as="Esquerda" />
    <qg:phrase text="Right" as="Direita" />
    <qg:phrase text="WHO IS WHO" as="QUEM É QUEM" />
    <qg:phrase text="Player" as="Jogador" />
    <qg:phrase text="Your name" as="Seu nome" />
    <qg:phrase text="PLAYER 1: SPACE TO START" as="JOGADOR 1: ESPAÇO PARA COMEÇAR" />
</qg:language>
  <qg:language lang="es" name="Español">
    <qg:phrase text="BRICKS" as="LADRILLOS" />
    <qg:phrase text="Play alone" as="Jugar solo" />
    <qg:phrase text="Play together" as="Jugar juntos" />
    <qg:phrase text="Quit" as="Salir" />
    <qg:phrase text="Language" as="Idioma" />
    <qg:phrase text="To the title" as="Al título" />
    <qg:phrase text="SCORE" as="PUNTOS" />
    <qg:phrase text="LIVES" as="VIDAS" />
    <qg:phrase text="LEVEL" as="NIVEL" />
    <qg:phrase text="SPACE: SERVE" as="ESPACIO: SACAR" />
    <qg:phrase text="TWO TO FOUR PLAYERS, EACH ON THEIR OWN MACHINE" as="DE DOS A CUATRO JUGADORES, CADA UNO EN SU MÁQUINA" />
    <qg:phrase text="EVERY BRICK IS BROKEN" as="TODOS LOS LADRILLOS ROTOS" />
    <qg:phrase text="THE BALLS ARE GONE" as="SE ACABARON LAS PELOTAS" />
      <qg:phrase text="Options" as="Opciones" />
    <qg:phrase text="OPTIONS" as="OPCIONES" />
    <qg:phrase text="Sounds" as="Sonidos" />
    <qg:phrase text="Full screen" as="Pantalla completa" />
    <qg:phrase text="on" as="sí" />
    <qg:phrase text="off" as="no" />
    <qg:phrase text="Back" as="Volver" />
    <qg:phrase text="Serve" as="Sacar" />
    <qg:phrase text="Left" as="Izquierda" />
    <qg:phrase text="Right" as="Derecha" />
    <qg:phrase text="WHO IS WHO" as="QUIÉN ES QUIÉN" />
    <qg:phrase text="Player" as="Jugador" />
    <qg:phrase text="Your name" as="Tu nombre" />
    <qg:phrase text="PLAYER 1: SPACE TO START" as="JUGADOR 1: ESPACIO PARA EMPEZAR" />
</qg:language>

  <qg:scene name="title" width="320" height="240" background="#1c1a2c">
    <qg:sprite sheet="bricks" frame="0" x="64" y="56" />
    <qg:sprite sheet="bricks" frame="1" x="112" y="56" />
    <qg:sprite sheet="bricks" frame="2" x="160" y="56" />
    <qg:sprite sheet="bricks" frame="3" x="208" y="56" />
    <qg:sprite sheet="bricks" frame="4" x="256" y="56" />
    <qg:hud position="top-center" size="32"><qg:text value="{tr('BRICKS')}" /></qg:hud>
    <qg:menu position="center" size="14">
      <qg:button label="Play alone"><q:call function="anew" /><qg:goto-scene name="level" fade="0.3" /></qg:button>
      <qg:button label="Play together"><q:call function="anew" /><qg:goto-scene name="together" /></qg:button>
      <qg:button label="Options"><qg:goto-scene name="options" /></qg:button>
      <qg:button label="{tr('Language') + ': ' + language()}"><qg:next-language /></qg:button>
      <!-- a desktop build quits; a page in a browser has nothing to quit to -->
      <qg:button label="Quit" if="{can_quit()}"><qg:quit /></qg:button>
    </qg:menu>
    <q:function name="anew">
      <q:set name="score" value="0" />
      <q:set name="lives" value="3" />
      <q:set name="level" value="1" />
    </q:function>
  </qg:scene>

  <!-- Two to four machines: one hosts, the others join its address. The game
       starts as the fourth joins, or when the host chooses to start sooner. -->
  <qg:scene name="together" width="320" height="240" background="#1c1a2c">
    <qg:hud position="top-center" size="10"><qg:text value="{tr('TWO TO FOUR PLAYERS, EACH ON THEIR OWN MACHINE')}" /></qg:hud>
    <qg:lobby local="level" local-label="Play alone" size="12" />
    <qg:on-input action="cancel">
      <qg:leave />
      <qg:goto-scene name="title" />
    </qg:on-input>
  </qg:scene>

  <!-- Who is who: each player types a name at their own machine (Enter opens
       the box, Enter sends it). The field is shared: what is sent reaches every
       machine on the same tick, as the keys do, and each shows it beside that
       player's paddle. Player 1 starts the first level with the serve. -->
  <qg:scene name="names" width="320" height="240" background="#1c1a2c">
    <q:set name="typed" value="" />
    <qg:hud position="top-center" size="14"><qg:text value="{tr('WHO IS WHO')}" /></qg:hud>
    <qg:hud position="center" size="12">
      <qg:icon sheet="paddles" frame="0" />
      <qg:text value="{who(1)}" color="#40dce6" />
      <qg:icon sheet="paddles" frame="1" />
      <qg:text value="{who(2)}" color="#e650c8" />
      <qg:icon sheet="paddles" frame="2" />
      <qg:text value="{who(3) if net_players() >= 3 else '-'}" color="#96e646" />
      <qg:icon sheet="paddles" frame="3" />
      <qg:text value="{who(4) if net_players() >= 4 else '-'}" color="#f0b030" />
      <qg:text value="{tr('PLAYER 1: SPACE TO START')}" />
    </qg:hud>
    <qg:menu local="true" position="bottom-center" size="12">
      <qg:field bind="typed" label="Your name" shared="true" max-length="10">
        <q:set name="names" index="{sender - 1}" value="{text}" />
      </qg:field>
    </qg:menu>
    <qg:on-input action="jump" on="release">
      <qg:goto-scene name="level" fade="0.3" />
    </qg:on-input>
  </qg:scene>

  <!-- A level: the bricks of levels[level - 1], a paddle for each player, the
       ball served from the first paddle. -->
  <qg:scene name="level" width="320" height="240" background="#1c1a2c" seed="1">
    <q:set name="serving" value="true" type="boolean" />
    <q:set name="done" value="false" type="boolean" />
    <q:call function="build" args="{levels[int(level) - 1]}" />

    <qg:hud position="top-left" size="10"><qg:text value="{tr('SCORE') + ' ' + str(score)}" /></qg:hud>
    <qg:hud position="top-center" size="10"><qg:text value="{tr('LEVEL') + ' ' + str(int(level))}" /></qg:hud>
    <qg:hud position="top-right" size="10"><qg:text value="{tr('LIVES') + ' ' + str(int(lives))}" /></qg:hud>
    <qg:hud position="bottom-center" size="10"><qg:text value="{tr('SPACE: SERVE') if serving else ''}" /></qg:hud>

    <!-- the walls: the sides and the top; the bottom is open -->
    <qg:zone name="left-wall" tag="side" x="-20" y="0" width="20" height="240" />
    <qg:zone name="right-wall" tag="side" x="320" y="0" width="20" height="240" />
    <qg:zone name="ceiling" tag="top" x="0" y="0" width="320" height="16" />

    <!-- A paddle runs along the bottom, kept on the screen. The ball leaves
         it at a slant: straight up from its middle, more aslant towards its
         ends. It squashes a little as it does. -->
    <qg:character id="p1" controller="ship" player="1" axis="horizontal" speed="240"
                  sheet="paddles" frame="0" x="160" y="226" hitbox="48x8">
      <qg:on-collision with="ball"><q:call function="hit" args="me, other" /></qg:on-collision>
    </qg:character>
    <qg:character id="p2" controller="ship" player="2" axis="horizontal" speed="240" if="{net_players() >= 2}"
                  sheet="paddles" frame="1" x="80" y="226" hitbox="48x8">
      <qg:on-collision with="ball"><q:call function="hit" args="me, other" /></qg:on-collision>
    </qg:character>
    <qg:character id="p3" controller="ship" player="3" axis="horizontal" speed="240" if="{net_players() >= 3}"
                  sheet="paddles" frame="2" x="240" y="226" hitbox="48x8">
      <qg:on-collision with="ball"><q:call function="hit" args="me, other" /></qg:on-collision>
    </qg:character>
    <qg:character id="p4" controller="ship" player="4" axis="horizontal" speed="240" if="{net_players() >= 4}"
                  sheet="paddles" frame="3" x="120" y="226" hitbox="48x8">
      <qg:on-collision with="ball"><q:call function="hit" args="me, other" /></qg:on-collision>
    </qg:character>
    <q:function name="hit" params="paddle, ball">
      <qg:deflect target="ball" dx="{(ball.x - paddle.x) / 24}" dy="-1" />
      <qg:tween target="paddle" property="scale" from="1.2" to="1" seconds="0.2" trans="back" />
      <qg:play sound="bounce" vary="0.1" />
    </q:function>

    <!-- The serve: as the action is let go, a ball leaves the first paddle. -->
    <qg:on-input action="jump" on="release">
      <q:if condition="{serving and not done}">
        <q:set name="serving" value="false" />
        <qg:spawn prefab="Ball" at="p1" dy="-10" />
      </q:if>
    </qg:on-input>

    <!-- A ball out at the bottom is lost; with none left, a life. -->
    <qg:on-screen-exit of="ball" side="bottom">
      <qg:destroy target="other" />
      <q:if condition="{count('ball') == 0 and not done}">
        <qg:play sound="lost" />
        <q:set name="lives" value="{lives - 1}" />
        <q:if condition="{lives <= 0}">
          <qg:goto-scene name="over" fade="0.5" />
          <q:else><q:set name="serving" value="true" /></q:else>
        </q:if>
      </q:if>
    </qg:on-screen-exit>

    <!-- A bomb breaks every brick within a brick and a half of it. -->
    <qg:on-death of="bomb">
      <qg:shake at="other" frames="12" strength="3" />
      <qg:for-each tag="brick" var="near">
        <q:if condition="{distance(near, other) < 48}">
          <qg:damage target="near" amount="2" />
        </q:if>
      </qg:for-each>
    </qg:on-death>

    <!-- The last brick: slow motion, the balls fade out, the paddle hops, the next level. -->
    <qg:when condition="{count('brick') + count('bomb') == 0}">
      <q:set name="done" value="true" />
      <qg:play sound="clear" />
      <qg:time-scale scale="0.25" seconds="1.5" />
      <qg:for-each tag="ball" var="b">
        <qg:tween target="b" property="alpha" to="0" seconds="0.3">
          <qg:on-end><qg:destroy target="me" /></qg:on-end>
        </qg:tween>
      </qg:for-each>
      <qg:tween target="p1" property="y" to="214" seconds="0.4" trans="quad" yoyo="true" repeat="1">
        <qg:on-end><q:call function="next" /></qg:on-end>
      </qg:tween>
    </qg:when>
    <q:function name="next">
      <q:if condition="{level >= len(levels)}">
        <qg:goto-scene name="won" fade="0.5" />
        <q:else>
          <q:set name="level" value="{level + 1}" />
          <qg:goto-scene name="level" fade="0.3" />
        </q:else>
      </q:if>
    </q:function>

    <!-- the level: a letter a brick, nine to a row -->
    <q:function name="build" params="lines">
      <q:loop var="r" from="0" to="{len(lines) - 1}">
        <q:loop var="c" from="0" to="{len(lines[r]) - 1}">
          <q:call function="place" args="{lines[r][c]}, {32 + c * 32}, {40 + r * 12}" />
        </q:loop>
      </q:loop>
    </q:function>
    <q:function name="place" params="kind, x, y">
      <q:if condition="{kind == 'R'}"><qg:spawn prefab="Red" x="{x}" y="{y}" />
        <q:elseif condition="{kind == 'O'}"><qg:spawn prefab="Orange" x="{x}" y="{y}" /></q:elseif>
        <q:elseif condition="{kind == 'Y'}"><qg:spawn prefab="Yellow" x="{x}" y="{y}" /></q:elseif>
        <q:elseif condition="{kind == 'G'}"><qg:spawn prefab="Green" x="{x}" y="{y}" /></q:elseif>
        <q:elseif condition="{kind == 'B'}"><qg:spawn prefab="Blue" x="{x}" y="{y}" /></q:elseif>
        <q:elseif condition="{kind == 'S'}"><qg:spawn prefab="Steel" x="{x}" y="{y}" /></q:elseif>
        <q:elseif condition="{kind == 'X'}"><qg:spawn prefab="Bomb" x="{x}" y="{y}" /></q:elseif>
      </q:if>
    </q:function>
  </qg:scene>

  <qg:scene name="won" width="320" height="240" background="#1c1a2c">
    <qg:hud position="top-center" size="14"><qg:text value="{tr('EVERY BRICK IS BROKEN')}" /></qg:hud>
    <qg:hud position="center" size="12"><qg:text value="{tr('SCORE') + ' ' + str(score)}" /></qg:hud>
    <qg:menu position="bottom-center" size="12">
      <qg:button label="To the title"><qg:leave /><qg:goto-scene name="title" /></qg:button>
    </qg:menu>
  </qg:scene>

  <qg:scene name="over" width="320" height="240" background="#1c1a2c">
    <qg:hud position="top-center" size="14"><qg:text value="{tr('THE BALLS ARE GONE')}" /></qg:hud>
    <qg:hud position="center" size="12"><qg:text value="{tr('SCORE') + ' ' + str(score)}" /></qg:hud>
    <qg:menu position="bottom-center" size="12">
      <qg:button label="To the title"><qg:leave /><qg:goto-scene name="title" /></qg:button>
    </qg:menu>
  </qg:scene>

  <!-- ===== Options: how loud, the full screen, the keys; kept between runs ===== -->

  <qg:scene name="options" width="320" height="240" background="#1c1a2c">
    <qg:hud position="top-center" size="24"><qg:text value="{tr('OPTIONS')}" /></qg:hud>
    <qg:menu position="center" size="14">
      <qg:slider label="Sounds" bus="effects" />
      <qg:button label="{tr('Full screen') + ': ' + (tr('on') if fullscreen() else tr('off'))}"><qg:fullscreen /></qg:button>
      <qg:rebind label="Serve" action="jump" />
      <qg:rebind label="Left" action="left" />
      <qg:rebind label="Right" action="right" />
      <qg:button label="Back"><qg:goto-scene name="title" /></qg:button>
    </qg:menu>
  </qg:scene>

</q:application>
