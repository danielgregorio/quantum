<q:application id="siege" type="game">

  <!-- Siege: a keep under siege, seen from above, alone or for two over the
       network. Raiders come in waves from the edges and make for the tower in
       the keep's middle. The archer walks with WASD (or the left stick), aims
       with the mouse (or the right stick) and shoots as fire is let go: held
       for most of a second, the shot is a bolt that goes through raiders and
       off the walls. With two, the second player is a knight on a horse who
       turns and spurs it on, and rides the raiders down. The tower zaps the
       nearest raider now and then. The art is drawn by scripts/art/siege.py
       (CC0); the sounds are Kenney's Pixel Platformer (CC0). -->

  <q:set name="score" value="0" type="number" />
  <q:set name="hearts" value="5" type="number" />
  <q:set name="wave" value="0" type="number" />
  <!-- the five best scores, kept between runs -->
  <q:set name="best" value="[]" type="array" saved="true" />

  <!-- the tower is hurt, and the siege may be over (once: two raiders may reach it on one tick) -->
  <q:function name="breach">
    <q:if condition="{hearts > 0}">
      <qg:play sound="hurt" />
      <q:set name="hearts" value="{hearts - 1}" />
      <q:if condition="{hearts <= 0}">
        <q:set name="best" value="{sort(best + [score], true)[:5]}" />
        <qg:goto-scene name="fallen" fade="0.6" />
      </q:if>
    </q:if>
  </q:function>

  <!-- 16-pixel tiles: 1 grass, 2 grass with flowers, 3 the keep's floor (walked on), 4 a wall -->
  <qg:tileset name="ground" src="assets/ground.png" tile="16">
    <qg:tile frame="0" shape="none" />
    <qg:tile frame="1" shape="none" />
    <qg:tile frame="2" shape="none" />
  </qg:tileset>
  <qg:spritesheet name="siege" src="assets/siege.png" tile="16" />

  <qg:sound bus="effects" name="twang" src="assets/kenney/audio/jump.ogg" />
  <qg:sound bus="effects" name="hit" src="assets/kenney/audio/stomp.ogg" />
  <qg:sound bus="effects" name="clank" src="assets/kenney/audio/block.ogg" />
  <qg:sound bus="effects" name="zap" src="assets/kenney/audio/powerup.ogg" />
  <qg:sound bus="effects" name="hurt" src="assets/kenney/audio/hurt.ogg" />
  <qg:sound bus="effects" name="horn" src="assets/kenney/audio/win.ogg" />

  <!-- fire: the mouse's left button, J, or the right trigger; the right stick aims -->
  <qg:input action="fire" keys="MouseLeft, J, JoyR2" />
  <qg:input action="aim_left" keys="JoyRightStickLeft" />
  <qg:input action="aim_right" keys="JoyRightStickRight" />
  <qg:input action="aim_up" keys="JoyRightStickUp" />
  <qg:input action="aim_down" keys="JoyRightStickDown" />

  <qg:multiplayer players="2" start="keep" />

  <qg:particles name="fire" preset="fire" color="#ff9030" amount="12" />
  <qg:particles name="dust" preset="dust" color="#c8b080" amount="6" />
  <qg:particles name="fallen" preset="smoke" color="#a09080" />

  <!-- An arrow flies straight, over the walls; a bolt, the charged shot, is
       faster, goes through what it hits and glances off the walls' stones (a
       shot round a corner), leaving a trail. -->
  <qg:prefab name="Arrow" tag="arrow" sheet="siege" frame="8" hitbox="6x6"
             ai="fly" speed="240" rotate="true" lifetime="60" />
  <qg:prefab name="Bolt" tag="bolt" sheet="siege" frame="9" hitbox="8x8"
             ai="fly" speed="300" rotate="true" walls="bounce" lifetime="120" trail="#ffd070" />

  <!-- Raiders make for the tower through the gates, knowing where it is
       behind the walls, and keep a little apart so a wave comes as a crowd,
       not a pile. A hit squashes one and shows what it took. -->
  <qg:prefab name="Raider" tag="raider" sheet="siege" frame="4" hitbox="12x12" health="2"
             ai="behavior" speed="34" sight="400" spacing="14">
    <qg:animation name="walk" frames="4,5" fps="6" />
    <qg:behavior><qg:seek target="tower" through-walls="true" /></qg:behavior>
    <qg:on-collision with="arrow"><q:call function="struck" args="me, other, 1" /></qg:on-collision>
    <qg:on-collision with="bolt"><q:call function="struck" args="me, null, 3" /></qg:on-collision>
    <qg:on-collision with="tower"><q:call function="reached" args="me, other" /></qg:on-collision>
    <qg:on-death>
      <q:set name="score" value="{score + 10}" />
      <qg:emit particles="fallen" at="me" />
      <qg:emit text="+10" at="me" dy="-10" color="#ffe070" />
    </qg:on-death>
  </qg:prefab>
  <!-- A brute is a raider (extends=: its way to the tower and what hits it), slow, that takes
       eight hits; how many it has left is over its head. -->
  <qg:prefab name="Brute" extends="Raider" frame="6" hitbox="14x14" health="8" scale="1.5" speed="20" spacing="20">
    <qg:animation name="walk" frames="6,7" fps="4" />
    <qg:label value="{me.health}" dy="-16" size="8" color="#ff8080" />
    <qg:on-death>
      <q:set name="score" value="{score + 50}" />
      <qg:emit particles="fallen" at="me" />
      <qg:emit text="+50" at="me" dy="-14" color="#ffe070" />
    </qg:on-death>
  </qg:prefab>
  <!-- A ram comes from the left with its shield in front: an arrow that meets
       the shield (the ram hits it from the left) glances off; one from behind
       or the sides breaks it. It carries a torch. -->
  <qg:prefab name="Ram" tag="raider" sheet="siege" frame="10" hitbox="16x12" health="4"
             ai="behavior" speed="18" sight="400" particles="fire">
    <qg:behavior><qg:seek target="tower" way="straight" through-walls="true" /></qg:behavior>
    <qg:on-collision with="arrow" side="left">
      <qg:play sound="clank" />
      <qg:destroy target="other" />
    </qg:on-collision>
    <qg:on-collision with="arrow"><q:call function="struck" args="me, other, 1" /></qg:on-collision>
    <qg:on-collision with="bolt"><q:call function="struck" args="me, null, 3" /></qg:on-collision>
    <qg:on-collision with="tower"><q:call function="reached" args="me, other" /></qg:on-collision>
    <qg:on-death>
      <q:set name="score" value="{score + 30}" />
      <qg:emit particles="fallen" at="me" />
      <qg:emit text="+30" at="me" dy="-10" color="#ffe070" />
    </qg:on-death>
  </qg:prefab>
  <!-- the tower in the keep's middle, with a fire on top; a raider that reaches it
       is a breach: the raider is gone, and the tower loses a heart -->
  <qg:prefab name="Tower" tag="tower" sheet="siege" frame="11" hitbox="16x16" solid="true" particles="fire" />
  <q:function name="reached" params="raider, tower">
    <qg:destroy target="raider" />
    <qg:shake at="tower" frames="10" strength="3" />
    <q:call function="breach" />
  </q:function>

  <!-- a hit: what it took floats up, the raider squashes and flashes; an arrow stops there -->
  <q:function name="struck" params="raider, shot, amount">
    <qg:play sound="hit" vary="0.15" />
    <qg:damage target="raider" amount="{amount}" />
    <qg:emit text="{str(amount)}" at="raider" dy="-8" color="#ffffff" />
    <qg:tween target="raider" property="scale-x" from="1.4" to="1" seconds="0.2" trans="back" />
    <qg:tween target="raider" property="scale-y" from="0.6" to="1" seconds="0.2" trans="back" />
    <qg:tween target="raider" property="tint" from="#ff6060" to="#ffffff" seconds="0.25" />
    <q:if condition="{shot != null}"><qg:destroy target="shot" /></q:if>
  </q:function>

  <!-- the game in Portuguese and Spanish (a web page's ?lang=pt, the command line's q-lang, or the system's language) -->
    <!-- on a phone: what the keys do, under a finger, in every scene -->
  <qg:touch-stick x="40" y="200" />
  <qg:touch-button action="fire" label="A" x="284" y="200" />

  <qg:language lang="pt" name="Português">
    <qg:phrase text="SIEGE" as="CERCO" />
    <qg:phrase text="Play alone" as="Jogar sozinho" />
    <qg:phrase text="Play together" as="Jogar juntos" />
    <qg:phrase text="Language" as="Idioma" />
    <qg:phrase text="Quit" as="Sair" />
    <qg:phrase text="SCORE" as="PONTOS" />
    <qg:phrase text="WAVE" as="ONDA" />
    <qg:phrase text="TOWER" as="TORRE" />
    <qg:phrase text="ARCHER" as="ARQUEIRO" />
    <qg:phrase text="KNIGHT" as="CAVALEIRO" />
    <qg:phrase text="HERE THEY COME" as="LÁ VÊM ELES" />
    <qg:phrase text="THE KEEP HAS FALLEN" as="A FORTALEZA CAIU" />
    <qg:phrase text="BEST" as="MELHORES" />
    <qg:phrase text="To the title" as="Para o início" />
    <qg:phrase text="TWO PLAYERS, EACH ON THEIR OWN MACHINE" as="DOIS JOGADORES, CADA UM NA SUA MÁQUINA" />
      <qg:phrase text="Options" as="Opções" />
    <qg:phrase text="OPTIONS" as="OPÇÕES" />
    <qg:phrase text="Sounds" as="Sons" />
    <qg:phrase text="Full screen" as="Tela cheia" />
    <qg:phrase text="on" as="sim" />
    <qg:phrase text="off" as="não" />
    <qg:phrase text="Back" as="Voltar" />
    <qg:phrase text="Fire" as="Atirar" />
</qg:language>
  <qg:language lang="es" name="Español">
    <qg:phrase text="SIEGE" as="ASEDIO" />
    <qg:phrase text="Play alone" as="Jugar solo" />
    <qg:phrase text="Play together" as="Jugar juntos" />
    <qg:phrase text="Language" as="Idioma" />
    <qg:phrase text="Quit" as="Salir" />
    <qg:phrase text="SCORE" as="PUNTOS" />
    <qg:phrase text="WAVE" as="OLEADA" />
    <qg:phrase text="TOWER" as="TORRE" />
    <qg:phrase text="ARCHER" as="ARQUERO" />
    <qg:phrase text="KNIGHT" as="CABALLERO" />
    <qg:phrase text="HERE THEY COME" as="AHÍ VIENEN" />
    <qg:phrase text="THE KEEP HAS FALLEN" as="LA FORTALEZA HA CAÍDO" />
    <qg:phrase text="BEST" as="MEJORES" />
    <qg:phrase text="To the title" as="Al inicio" />
    <qg:phrase text="TWO PLAYERS, EACH ON THEIR OWN MACHINE" as="DOS JUGADORES, CADA UNO EN SU MÁQUINA" />
      <qg:phrase text="Options" as="Opciones" />
    <qg:phrase text="OPTIONS" as="OPCIONES" />
    <qg:phrase text="Sounds" as="Sonidos" />
    <qg:phrase text="Full screen" as="Pantalla completa" />
    <qg:phrase text="on" as="sí" />
    <qg:phrase text="off" as="no" />
    <qg:phrase text="Back" as="Volver" />
    <qg:phrase text="Fire" as="Disparar" />
</qg:language>

  <qg:scene name="title" width="320" height="240" background="#2e3b24">
    <qg:hud position="top-center" size="32"><qg:text value="{tr('SIEGE')}" /></qg:hud>
    <qg:menu position="center" size="14">
      <qg:button label="Play alone"><q:call function="anew" /><qg:goto-scene name="keep" fade="0.3" /></qg:button>
      <qg:button label="Play together"><q:call function="anew" /><qg:goto-scene name="together" /></qg:button>
      <qg:button label="Options"><qg:goto-scene name="options" /></qg:button>
      <qg:button label="{tr('Language') + ': ' + language()}"><qg:next-language /></qg:button>
      <qg:button label="Quit" if="{can_quit()}"><qg:quit /></qg:button>
    </qg:menu>
    <q:function name="anew">
      <q:set name="score" value="0" />
      <q:set name="hearts" value="5" />
      <q:set name="wave" value="0" />
    </q:function>
  </qg:scene>

  <qg:scene name="together" width="320" height="240" background="#2e3b24">
    <qg:hud position="top-center" size="10"><qg:text value="{tr('TWO PLAYERS, EACH ON THEIR OWN MACHINE')}" /></qg:hud>
    <qg:lobby local="keep" local-label="Play alone" size="12" />
    <qg:on-input action="cancel">
      <qg:leave />
      <qg:goto-scene name="title" />
    </qg:on-input>
  </qg:scene>

  <!-- The keep: grass all round, the walls with a gate on each side, the tower
       in the middle. Things are drawn by how low they stand (y-sort), so a
       raider behind the tower is hidden by it. -->
  <qg:scene name="keep" width="320" height="240" background="#3c5a2c" seed="5" y-sort="true">
    <q:set name="message" value="" />
    <qg:tilemap tileset="ground" collision="true">
1,1,1,1,1,1,2,1,1,1,1,1,1,1,1,1,2,1,1,1
1,1,1,1,1,1,2,1,1,1,1,1,1,1,1,1,1,1,1,1
1,1,1,1,1,2,1,1,2,1,1,1,1,1,1,1,1,2,1,2
1,1,2,1,1,4,4,4,4,4,3,4,4,4,4,4,1,1,1,1
1,1,2,1,1,4,3,3,3,3,3,3,3,3,3,4,1,1,1,2
1,1,1,1,1,4,3,3,3,3,3,3,3,3,3,4,1,1,1,1
1,1,1,1,1,4,3,3,3,3,3,3,3,3,3,4,1,1,1,1
1,1,1,1,1,3,3,3,3,3,3,3,3,3,3,3,1,1,1,1
2,1,1,1,1,4,3,3,3,3,3,3,3,3,3,4,1,1,1,1
1,1,1,1,1,4,3,3,3,3,3,3,3,3,3,4,2,1,1,1
1,1,1,2,1,4,3,3,3,3,3,3,3,3,3,4,1,1,2,1
1,1,1,1,1,4,4,4,4,4,3,4,4,4,4,4,1,1,1,1
1,1,1,1,1,2,1,1,1,1,1,1,1,1,1,1,1,1,1,1
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,2,1,1,1
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1
    </qg:tilemap>
    <qg:instance prefab="Tower" name="tower" x="168" y="120" />

    <!-- the archer: walks, aims at the pointer (or with the right stick) -->
    <qg:character id="p1" controller="topdown" player="1" sheet="siege" frame="0"
                  x="140" y="120" hitbox="12x12" speed="80" bounds="scene">
      <qg:animation name="idle" frames="0" />
      <qg:animation name="walk" frames="0,1" fps="8" />
      <qg:label value="{tr('ARCHER')}" dy="-14" size="8" if="{net_status() != 'offline'}" />
    </qg:character>
    <qg:cursor id="aim" player="1" step="0" sheet="siege" frame="12" />

    <!-- the knight, with two: left and right turn the horse, up spurs it on -->
    <qg:character id="p2" controller="behavior" player="2" sheet="siege" frame="2"
                  x="196" y="120" hitbox="14x14" if="{net_status() != 'offline'}">
      <qg:behavior>
        <qg:steer turn="200" thrust="260" drag="1.6" max="140" />
        <qg:keep-inside />
      </qg:behavior>
      <qg:label value="{tr('KNIGHT')}" dy="-14" size="8" />
      <qg:on-collision with="raider" cooldown="20">
        <q:if condition="{abs(me.vx) + abs(me.vy) > 60}">
          <q:call function="struck" args="other, null, 2" />
        </q:if>
      </qg:on-collision>
    </qg:character>

    <!-- A shot leaves as fire is let go, at the pointer or the way the right
         stick points: held 40 ticks or more, a bolt. While it is charging, a
         line shows where it will go. -->
    <qg:on-input action="fire" on="release">
      <q:set name="sx" value="{strength('aim_right') - strength('aim_left')}" />
      <q:set name="sy" value="{strength('aim_down') - strength('aim_up')}" />
      <q:set name="dx" value="{sx if sx != 0 or sy != 0 else aim.x - p1.x}" />
      <q:set name="dy" value="{sy if sx != 0 or sy != 0 else aim.y - p1.y}" />
      <qg:play sound="twang" vary="0.1" />
      <q:if condition="{pressed_for('fire') >= 40}">
        <qg:spawn prefab="Bolt" at="p1" heading="{dx},{dy}" />
        <q:else><qg:spawn prefab="Arrow" at="p1" heading="{dx},{dy}" /></q:else>
      </q:if>
    </qg:on-input>
    <qg:timer every="2">
      <q:if condition="{pressing('fire') and pressed_for('fire') >= 40}">
        <qg:beam from="p1" to="aim" seconds="0.05" color="#ffe080" width="1" />
      </q:if>
    </qg:timer>

    <!-- every three seconds the tower zaps the raider nearest it, within 90 px -->
    <qg:timer every="180" from="120">
      <q:set name="near" value="{nearest(tower, 'raider')}" />
      <q:if condition="{near != null and distance(tower, near) < 90}">
        <qg:play sound="zap" />
        <qg:beam from="tower" to="near" seconds="0.2" color="#80d0ff" width="2" />
        <q:call function="struck" args="near, null, 2" />
      </q:if>
    </qg:timer>

    <!-- The waves: none left, the next comes after a breath, bigger; each
         third wave brings a brute, each fourth a ram from the left. -->
    <qg:when condition="{count('raider') == 0}">
      <q:set name="wave" value="{wave + 1}" />
      <q:set name="message" value="{tr('HERE THEY COME')}" />
      <qg:play sound="horn" />
      <qg:after seconds="2">
        <q:set name="message" value="" />
        <!-- from the edges: by turns the sides and the top or bottom, the rest from the seed -->
        <q:loop var="i" from="1" to="{3 + wave * 2}">
          <q:if condition="{i % 2 == 0}">
            <qg:spawn prefab="Raider" x="{8 if random(0, 1) < 0.5 else 312}" y="{random(16, 224)}" />
            <q:else><qg:spawn prefab="Raider" x="{random(16, 304)}" y="{8 if random(0, 1) < 0.5 else 232}" /></q:else>
          </q:if>
        </q:loop>
        <q:if condition="{wave % 3 == 0}"><qg:spawn prefab="Brute" x="168" y="10" /></q:if>
        <q:if condition="{wave % 4 == 0}"><qg:spawn prefab="Ram" x="10" y="120" /></q:if>
      </qg:after>
    </qg:when>

    <qg:hud position="top-left" size="10"><qg:text value="{tr('SCORE') + ' ' + str(score)}" /></qg:hud>
    <qg:hud position="top-center" size="10"><qg:text value="{tr('WAVE') + ' ' + str(int(wave))}" /></qg:hud>
    <qg:hud position="top-right" size="10"><qg:text value="{tr('TOWER') + ' ' + str(int(hearts))}" /></qg:hud>
    <qg:hud position="center" size="14"><qg:text bind="message" /></qg:hud>
  </qg:scene>

  <qg:scene name="fallen" width="320" height="240" background="#1c1a14">
    <qg:hud position="top-center" size="14"><qg:text value="{tr('THE KEEP HAS FALLEN')}" /></qg:hud>
    <qg:hud position="center" size="12">
      <qg:text value="{tr('SCORE') + ' ' + str(score)}" />
      <qg:text value="{tr('BEST') + ' ' + (str(best[0]) if len(best) > 0 else '-')}" />
    </qg:hud>
    <qg:menu position="bottom-center" size="12">
      <qg:button label="To the title"><qg:leave /><qg:goto-scene name="title" /></qg:button>
    </qg:menu>
  </qg:scene>

  <!-- ===== Options: how loud, the full screen, the keys; kept between runs ===== -->

  <qg:scene name="options" width="320" height="240" background="#2e3b24">
    <qg:hud position="top-center" size="24"><qg:text value="{tr('OPTIONS')}" /></qg:hud>
    <qg:menu position="center" size="14">
      <qg:slider label="Sounds" bus="effects" />
      <qg:button label="{tr('Full screen') + ': ' + (tr('on') if fullscreen() else tr('off'))}"><qg:fullscreen /></qg:button>
      <qg:rebind label="Fire" action="fire" />
      <qg:button label="Back"><qg:goto-scene name="title" /></qg:button>
    </qg:menu>
  </qg:scene>

</q:application>
