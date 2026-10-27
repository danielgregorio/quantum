<q:application id="outpost" type="game">

  <!-- Outpost, the game the players run (PLAN_GAME_SERVER.md, Phase 4). It holds no rule of the world: the world is
       outpost.server.q's, on the server. The game signs in to the site, draws what the world says each player sees
       (qg:mirror), sends what the player asks (qg:send) and shows what happens (qg:on-event). The map is the file
       the server reads, so only what moves goes over the network.

       The arrows step (at once: the world's step is predicted). A click on a beast attacks it, on Marta or Captain
       Rhea talks to her (their minds answer: Phase 5), on the ground walks there. B is the bag, C the chat. -->

  <qg:connect world="outpost.server.q" server="wss://outpost.quantumframework.net" local="ws://127.0.0.1:7700" />

  <qg:input action="bag" keys="B, I" />
  <qg:input action="chat" keys="C" />

  <qg:tileset name="land" src="assets/land.png" tile="16" />
  <qg:spritesheet name="folk" src="assets/folk.png" tile="16" />
  <qg:spritesheet name="beasts" src="assets/beasts.png" tile="16" />

  <!-- the kinds of the world's entities: what each looks like. A mirrored prefab's me is the entity as the world
       sent it; it walks from tile to tile in the time the world gives a step -->
  <qg:prefab name="Hero" sheet="folk" frame="0" hitbox="14x14">
    <qg:label value="{me.name}" dy="-14" size="8" />
    <qg:health-bar value="{me.hp}" max="{me.max_hp}" dy="-10" />
  </qg:prefab>
  <qg:prefab name="Trader" sheet="folk" frame="2" hitbox="14x14">
    <qg:label value="{me.title}" dy="-14" size="8" color="#55ffff" />
  </qg:prefab>
  <qg:prefab name="Captain" sheet="folk" frame="3" hitbox="14x14">
    <qg:label value="{me.title}" dy="-14" size="8" color="#55ffff" />
  </qg:prefab>
  <qg:prefab name="Rat" sheet="beasts" frame="0" hitbox="12x10">
    <qg:health-bar value="{me.hp}" max="{me.max_hp}" dy="-8" color="#e04040" />
  </qg:prefab>
  <qg:prefab name="Wolf" sheet="beasts" frame="1" hitbox="14x12">
    <qg:health-bar value="{me.hp}" max="{me.max_hp}" dy="-9" color="#e04040" />
  </qg:prefab>
  <qg:prefab name="Bear" sheet="beasts" frame="2" hitbox="28x24" scale="2">
    <qg:label value="{'The Old Bear'}" dy="-22" size="8" color="#ffaa00" />
    <qg:health-bar value="{me.hp}" max="{me.max_hp}" dy="-18" width="28" color="#e04040" />
  </qg:prefab>

  <!-- where the site signs in; the account and the password typed; what the game has to say -->
  <q:set name="site" value="https://outpost.quantumframework.net/sign-in" />
  <q:set name="account" value="" />
  <q:set name="password" value="" />
  <q:set name="note" value="" />
  <q:set name="line1" value="" />
  <q:set name="line2" value="" />
  <q:set name="line3" value="" />
  <q:set name="typed" value="" />
  <q:set name="talking" value="" />
  <q:set name="words" value="" />
  <q:set name="said" value="" />

  <!-- ===== The title: sign in with the site's account ===== -->
  <qg:scene name="title" width="480" height="270" background="#10141c">
    <qg:hud position="top-center" size="32"><qg:text value="{'OUTPOST'}" color="#ffaa00" /></qg:hud>
    <qg:menu position="center" size="12">
      <qg:field label="Account" bind="account" />
      <qg:field label="Password" bind="password" secret="true" />
      <qg:button label="Enter the world">
        <q:set name="note" value="Signing in..." />
        <qg:sign-in to="{site}" data="{ {'account': account, 'password': password} }" timeout="15">
          <qg:on-done>
            <q:set name="password" value="" />
            <q:set name="note" value="" />
            <qg:goto-scene name="mainland" />
          </qg:on-done>
          <qg:on-fail>
            <q:set name="password" value="" />
            <q:set name="note" value="{reason}" />
          </qg:on-fail>
        </qg:sign-in>
      </qg:button>
    </qg:menu>
    <qg:hud position="bottom-center" size="10"><qg:text value="{note}" color="#ff5555" /></qg:hud>
  </qg:scene>

  <!-- ===== The world: the server's, seen through the hero's eyes ===== -->
  <qg:scene name="mainland" width="480" height="270" background="#000000" world="true">
    <qg:tilemap tileset="land" src="maps/mainland.tmx" />
    <qg:mirror view="around" />                                   <!-- each entity of the view, as its kind's prefab -->
    <qg:camera follow="me" bounds="tilemap" />
    <qg:cursor grid="16" step="0" />                               <!-- the mouse; the arrows are the hero's -->

    <qg:on-input action="up"><qg:send command="step" dir="north" /></qg:on-input>
    <qg:on-input action="down"><qg:send command="step" dir="south" /></qg:on-input>
    <qg:on-input action="left"><qg:send command="step" dir="west" /></qg:on-input>
    <qg:on-input action="right"><qg:send command="step" dir="east" /></qg:on-input>

    <!-- a click: on a beast (or a hero, out of the town), attack it; on Marta, her shop; on Rhea, her quests; on the
         ground, go there -->
    <qg:on-select>
      <q:if condition="{other != null and (other.kind == 'Trader' or other.kind == 'Captain')}">
        <q:set name="talking" value="{other.id}" />
        <q:set name="said" value="" />
        <qg:open-overlay name="talk" />
        <q:elseif condition="{other != null and other.id != me().id}"><qg:send command="attack" who="{other.id}" /></q:elseif>
        <q:else><qg:send command="go" to="{ {'x': cursor.col, 'y': cursor.row} }" /></q:else>
      </q:if>
    </qg:on-select>

    <!-- what happens, seen: the world's events where this player sees -->
    <qg:on-event name="hit"><qg:emit text="{str(value)}" at="other" color="#ff5555" /></qg:on-event>
    <qg:on-event name="heal"><qg:emit text="{'+' + str(value)}" at="other" color="#55ff55" /></qg:on-event>
    <qg:on-event name="level"><qg:emit text="{tr('LEVEL') + ' ' + str(value)}" at="other" color="#ffaa00" size="12" /></qg:on-event>
    <qg:on-event name="fallen"><q:set name="note" value="{tr('You fell, and woke at the temple.')}" /></qg:on-event>
    <qg:on-event name="chat">
      <q:set name="line3" value="{line2}" />
      <q:set name="line2" value="{line1}" />
      <q:set name="line1" value="{'[' + value.channel + '] ' + value.who + ': ' + value.text}" />
    </qg:on-event>
    <qg:on-event name="npc-thinking"><q:set name="said" value="{value.who + ': ...'}" /></qg:on-event>
    <qg:on-event name="npc-says"><q:set name="said" value="{value.who + ': ' + value.text}" /></qg:on-event>
    <qg:on-refused><q:set name="note" value="{reason}" /></qg:on-refused>

    <qg:on-input action="bag"><qg:open-overlay name="bag" /></qg:on-input>
    <qg:on-input action="chat"><qg:open-overlay name="chat" /></qg:on-input>

    <qg:hud position="top-left" size="10">
      <qg:text value="{(me().name + '   ' + tr('Level') + ' ' + str(me().level)) if connected() else tr('Coming into the world...')}" color="#ffff55" />
      <qg:bar value="{me().hp}" max="{me().max_hp}" width="90" height="6" />
      <qg:text value="{str(me().gold) + ' ' + tr('gold')}" color="#ffaa00" />
    </qg:hud>
    <qg:hud position="bottom-left" size="9">
      <qg:text value="{line3}" color="#aaaaaa" />
      <qg:text value="{line2}" color="#aaaaaa" />
      <qg:text value="{line1}" />
      <qg:text value="{note}" color="#ff5555" />
    </qg:hud>
  </qg:scene>

  <!-- ===== Over the world, which goes on under them (it is the server's: it never stands still) ===== -->

  <!-- the bag: a click eats or drinks what heals, and wears what is worn -->
  <qg:overlay name="bag" freeze="false">
    <qg:hud position="top-center" size="12"><qg:text value="{tr('BAG') + '   ' + str(me().gold) + ' ' + tr('gold')}" color="#ffff55" /></qg:hud>
    <qg:menu position="center" size="10" source="{entries(me().bag)}" as="it" rows="8">
      <qg:button label="{it.key + ' x' + str(it.value)}">
        <q:if condition="{it.key == 'cheese' or it.key == 'meat' or it.key == 'health-potion'}">
          <qg:send command="use" item="{it.key}" />
          <q:else><qg:send command="equip" item="{it.key}" /></q:else>
        </q:if>
      </qg:button>
    </qg:menu>
    <qg:on-input action="cancel"><qg:close-overlay /></qg:on-input>
  </qg:overlay>

  <!-- words to Marta or Rhea: their minds answer in their own time (npc-says); the list and the quests are there
       too, for whoever would rather not talk -->
  <qg:overlay name="talk" freeze="false">
    <qg:hud position="top-center" size="11"><qg:text value="{entity(talking).title if entity(talking) != null else ''}" color="#55ffff" /></qg:hud>
    <qg:hud position="center" size="10"><qg:text value="{said}" /></qg:hud>
    <qg:menu x="16" y="170" size="10">
      <qg:field label="Say" bind="words" max-length="200" />
      <qg:button label="Tell her"><qg:send command="talk" npc="{talking}" text="{words}" /><q:set name="words" value="" /></qg:button>
      <qg:button label="The list" if="{entity(talking) != null and entity(talking).kind == 'Trader'}"><qg:open-overlay name="shop" /></qg:button>
      <qg:button label="Her work" if="{entity(talking) != null and entity(talking).kind == 'Captain'}"><qg:open-overlay name="quests" /></qg:button>
      <qg:button label="Back"><qg:close-overlay /></qg:button>
    </qg:menu>
    <qg:on-input action="cancel"><qg:close-overlay /></qg:on-input>
  </qg:overlay>

  <!-- Old Marta's shop, at the list's prices; she buys at half of what a thing is worth -->
  <qg:overlay name="shop" freeze="false">
    <qg:hud position="top-center" size="12"><qg:text value="{tr('Old Marta') + '   ' + str(me().gold) + ' ' + tr('gold')}" color="#55ffff" /></qg:hud>
    <qg:menu x="24" y="40" size="10">
      <qg:button label="cheese   2"><qg:send command="buy" item="cheese" /></qg:button>
      <qg:button label="meat   5"><qg:send command="buy" item="meat" /></qg:button>
      <qg:button label="health-potion   40"><qg:send command="buy" item="health-potion" /></qg:button>
      <qg:button label="wooden-sword   50"><qg:send command="buy" item="wooden-sword" /></qg:button>
      <qg:button label="leather-armor   80"><qg:send command="buy" item="leather-armor" /></qg:button>
      <qg:button label="iron-sword   300"><qg:send command="buy" item="iron-sword" /></qg:button>
      <qg:button label="Back"><qg:close-overlay /></qg:button>
    </qg:menu>
    <qg:menu x="260" y="40" size="10" source="{entries(me().bag)}" as="it" rows="8">
      <qg:button label="{tr('Sell') + ' ' + it.key}"><qg:send command="sell" item="{it.key}" /></qg:button>
    </qg:menu>
    <qg:on-input action="cancel"><qg:close-overlay /></qg:on-input>
  </qg:overlay>

  <!-- Captain Rhea's quests: one at a time, as the hero's level allows -->
  <qg:overlay name="quests" freeze="false">
    <qg:hud position="top-center" size="11">
      <qg:text value="{tr('Captain Rhea')}" color="#55ffff" />
      <qg:text value="{(tr('Your quest:') + ' ' + me().quest.name + ', ' + str(me().quest.done)) if len(me().quest) > 0 else tr('No quest. Rhea has work.')}" />
    </qg:hud>
    <qg:menu position="center" size="10">
      <qg:button label="Rats in the sewers (level 1)"><qg:send command="take-quest" name="sewers" /></qg:button>
      <qg:button label="Pelts for the winter (level 3)"><qg:send command="take-quest" name="pelts" /></qg:button>
      <qg:button label="The Old Bear (level 8)"><qg:send command="take-quest" name="old-bear" /></qg:button>
      <qg:button label="It is done"><qg:send command="turn-in" /></qg:button>
      <qg:button label="Back"><qg:close-overlay /></qg:button>
    </qg:menu>
    <qg:on-input action="cancel"><qg:close-overlay /></qg:on-input>
  </qg:overlay>

  <!-- the chat: a line to those near (say), far (yell) or everyone (help) -->
  <qg:overlay name="chat" freeze="false">
    <qg:menu x="16" y="170" size="10">
      <qg:field label="" bind="typed" max-length="200" />
      <qg:button label="Say"><qg:send command="chat" channel="say" text="{typed}" /><q:set name="typed" value="" /><qg:close-overlay /></qg:button>
      <qg:button label="Yell"><qg:send command="chat" channel="yell" text="{typed}" /><q:set name="typed" value="" /><qg:close-overlay /></qg:button>
      <qg:button label="Help"><qg:send command="chat" channel="help" text="{typed}" /><q:set name="typed" value="" /><qg:close-overlay /></qg:button>
    </qg:menu>
    <qg:on-input action="cancel"><qg:close-overlay /></qg:on-input>
  </qg:overlay>

  <qg:language lang="pt" name="Português">
    <qg:phrase text="Account" as="Conta" />
    <qg:phrase text="Password" as="Senha" />
    <qg:phrase text="Enter the world" as="Entrar no mundo" />
    <qg:phrase text="Signing in..." as="Entrando..." />
    <qg:phrase text="Coming into the world..." as="Entrando no mundo..." />
    <qg:phrase text="Level" as="Nível" />
    <qg:phrase text="LEVEL" as="NÍVEL" />
    <qg:phrase text="gold" as="ouro" />
    <qg:phrase text="BAG" as="MOCHILA" />
    <qg:phrase text="Sell" as="Vender" />
    <qg:phrase text="Back" as="Voltar" />
    <qg:phrase text="Old Marta" as="Velha Marta" />
    <qg:phrase text="Captain Rhea" as="Capitã Rhea" />
    <qg:phrase text="Your quest:" as="Sua missão:" />
    <qg:phrase text="No quest. Rhea has work." as="Nenhuma missão. A Rhea tem trabalho." />
    <qg:phrase text="It is done" as="Está feito" />
    <qg:phrase text="You fell, and woke at the temple." as="Você caiu, e acordou no templo." />
    <qg:phrase text="Say" as="Dizer" />
    <qg:phrase text="Yell" as="Gritar" />
    <qg:phrase text="Help" as="Ajuda" />
    <qg:phrase text="OUTPOST" as="OUTPOST" />
    <qg:phrase text="Tell her" as="Dizer a ela" />
    <qg:phrase text="The list" as="A lista" />
    <qg:phrase text="Her work" as="O trabalho dela" />
    <qg:phrase text="Rats in the sewers (level 1)" as="Ratos nos esgotos (nível 1)" />
    <qg:phrase text="Pelts for the winter (level 3)" as="Peles para o inverno (nível 3)" />
    <qg:phrase text="The Old Bear (level 8)" as="O Urso Velho (nível 8)" />
    <!-- the things keep the world's names, as the bag shows them -->
    <qg:phrase text="cheese   2" as="cheese   2" />
    <qg:phrase text="meat   5" as="meat   5" />
    <qg:phrase text="health-potion   40" as="health-potion   40" />
    <qg:phrase text="wooden-sword   50" as="wooden-sword   50" />
    <qg:phrase text="leather-armor   80" as="leather-armor   80" />
    <qg:phrase text="iron-sword   300" as="iron-sword   300" />
  </qg:language>

  <qg:language lang="es" name="Español">
    <qg:phrase text="Account" as="Cuenta" />
    <qg:phrase text="Password" as="Contraseña" />
    <qg:phrase text="Enter the world" as="Entrar al mundo" />
    <qg:phrase text="Signing in..." as="Entrando..." />
    <qg:phrase text="Coming into the world..." as="Entrando al mundo..." />
    <qg:phrase text="Level" as="Nivel" />
    <qg:phrase text="LEVEL" as="NIVEL" />
    <qg:phrase text="gold" as="oro" />
    <qg:phrase text="BAG" as="MOCHILA" />
    <qg:phrase text="Sell" as="Vender" />
    <qg:phrase text="Back" as="Volver" />
    <qg:phrase text="Old Marta" as="Vieja Marta" />
    <qg:phrase text="Captain Rhea" as="Capitana Rhea" />
    <qg:phrase text="Your quest:" as="Tu misión:" />
    <qg:phrase text="No quest. Rhea has work." as="Ninguna misión. Rhea tiene trabajo." />
    <qg:phrase text="It is done" as="Está hecho" />
    <qg:phrase text="You fell, and woke at the temple." as="Caíste, y despertaste en el templo." />
    <qg:phrase text="Say" as="Decir" />
    <qg:phrase text="Yell" as="Gritar" />
    <qg:phrase text="Help" as="Ayuda" />
    <qg:phrase text="OUTPOST" as="OUTPOST" />
    <qg:phrase text="Tell her" as="Decirle" />
    <qg:phrase text="The list" as="La lista" />
    <qg:phrase text="Her work" as="Su trabajo" />
    <qg:phrase text="Rats in the sewers (level 1)" as="Ratas en las cloacas (nivel 1)" />
    <qg:phrase text="Pelts for the winter (level 3)" as="Pieles para el invierno (nivel 3)" />
    <qg:phrase text="The Old Bear (level 8)" as="El Viejo Oso (nivel 8)" />
    <!-- the things keep the world's names, as the bag shows them -->
    <qg:phrase text="cheese   2" as="cheese   2" />
    <qg:phrase text="meat   5" as="meat   5" />
    <qg:phrase text="health-potion   40" as="health-potion   40" />
    <qg:phrase text="wooden-sword   50" as="wooden-sword   50" />
    <qg:phrase text="leather-armor   80" as="leather-armor   80" />
    <qg:phrase text="iron-sword   300" as="iron-sword   300" />
  </qg:language>
</q:application>
