<q:application id="outpost" type="game">

  <!-- Outpost, the game the players run, as it should read: Phase 0 of PLAN_GAME_SERVER.md. It holds no rule of the
       world: the world is outpost.server.q's, on the server. The game signs in, draws what the server says each
       player sees (qg:mirror), sends what the player asks (qg:send) and shows what happens (qg:on-event). The map
       is the same file the server reads, so only what moves goes over the network. -->

  <!-- where the world is: the site's server, or the one `quantum gameserver run` started on this machine -->
  <qg:connect world="outpost" server="wss://outpost.quantumframework.net" local="ws://localhost:7700" />

  <qg:input action="bag" keys="B, I" />
  <qg:input action="talk" keys="T" />
  <qg:input action="chat" keys="Enter" />
  <qg:input action="quests" keys="Q" />

  <qg:tileset name="land" src="assets/land.png" tile="16">
    <qg:tile frame="5" frames="4" fps="3" />                     <!-- the lake -->
  </qg:tileset>
  <qg:spritesheet name="folk" src="assets/folk.png" tile="16" />
  <qg:spritesheet name="beasts" src="assets/beasts.png" tile="16" />
  <qg:spritesheet name="faces" src="assets/faces.png" tile="32" />

  <qg:sound bus="effects" name="hit" src="assets/kenney/audio/stomp.ogg" />
  <qg:sound bus="effects" name="level" src="assets/kenney/audio/powerup.ogg" />
  <qg:sound bus="effects" name="coin" src="assets/kenney/audio/coin.ogg" />
  <qg:sound bus="music" name="town" src="assets/music/town.ogg" loop="true" />

  <!-- the kinds of the server's entities: what each looks like. A mirrored prefab's me is the entity as the server
       sent it (its public fields; the hero's private ones only to its player). It walks from tile to tile in the
       time the server gives a step, facing the way it goes -->
  <qg:prefab name="Hero" sheet="folk" frame="{me.outfit * 4}" hitbox="14x14">
    <qg:animation name="walk" frames="{me.outfit * 4},{me.outfit * 4 + 1}" fps="6" />
    <qg:label value="{me.name}" dy="-14" />
    <qg:health-bar value="{me.hp}" max="{me.max_hp}" dy="-10" />
  </qg:prefab>
  <qg:prefab name="Rat" sheet="beasts" frame="0" hitbox="12x10">
    <qg:animation name="walk" frames="0,1" fps="6" />
    <qg:health-bar value="{me.hp}" max="{me.max_hp}" dy="-8" />
  </qg:prefab>
  <qg:prefab name="Wolf" sheet="beasts" frame="2" hitbox="14x12">
    <qg:animation name="walk" frames="2,3" fps="8" />
    <qg:health-bar value="{me.hp}" max="{me.max_hp}" dy="-9" />
  </qg:prefab>
  <qg:prefab name="Bear" sheet="beasts" frame="4" hitbox="28x24" scale="2">
    <qg:animation name="walk" frames="4,5" fps="4" />
    <qg:label value="{'The Old Bear'}" dy="-22" color="#ffaa00" />
    <qg:health-bar value="{me.hp}" max="{me.max_hp}" dy="-18" width="28" />
  </qg:prefab>
  <qg:prefab name="Trader" sheet="folk" frame="40" hitbox="14x14">
    <qg:label value="{me.title}" dy="-14" color="#55ffff" />
  </qg:prefab>
  <qg:prefab name="Captain" sheet="folk" frame="44" hitbox="14x14">
    <qg:label value="{me.title}" dy="-14" color="#55ffff" />
  </qg:prefab>

  <q:set name="user" value="" />
  <q:set name="password" value="" />
  <q:set name="note" value="" />
  <q:set name="said" value="" />
  <q:set name="typed" value="" />
  <q:set name="talking" value="" />

  <!-- ===== The title: sign in with the site's account ===== -->
  <qg:scene name="title" width="480" height="270" background="#10141c">
    <qg:hud position="top-center" size="40"><qg:text value="{'OUTPOST'}" color="#ffaa00" /></qg:hud>
    <qg:menu position="center">
      <qg:field label="Name" bind="user" />
      <qg:field label="Password" bind="password" secret="true" />
      <qg:button label="Enter the world">
        <qg:sign-in user="{user}" password="{password}">
          <qg:on-done><qg:goto-scene name="mainland" fade="0.5" /></qg:on-done>
          <qg:on-fail><q:set name="note" value="{reason}" /></qg:on-fail>
        </qg:sign-in>
      </qg:button>
      <qg:button label="Make an account"><qg:open-url href="https://outpost.quantumframework.net/join" /></qg:button>
    </qg:menu>
    <qg:hud position="bottom-center" size="10">
      <qg:text value="{note}" color="#ff5555" />
      <qg:text value="{str(world_online()) + ' ' + tr('in the world now')}" color="#aaaaaa" />
    </qg:hud>
  </qg:scene>

  <!-- ===== The world: the server's, seen through the hero's eyes ===== -->
  <qg:scene name="mainland" width="480" height="270" background="#000000" world="true">
    <qg:tilemap tileset="land" src="maps/mainland.tmx" />
    <qg:mirror view="around" />                                   <!-- each entity of the view, as its kind's prefab -->
    <qg:camera follow="me" bounds="tilemap" />
    <qg:music sound="town" />
    <qg:cursor player="1" grid="16" />

    <!-- the arrows step (and the hero walks at once: the server's step command is predicted) -->
    <qg:on-input action="up"><qg:send command="step" dir="north" /></qg:on-input>
    <qg:on-input action="down"><qg:send command="step" dir="south" /></qg:on-input>
    <qg:on-input action="left"><qg:send command="step" dir="west" /></qg:on-input>
    <qg:on-input action="right"><qg:send command="step" dir="east" /></qg:on-input>

    <!-- a click: on a beast, attack it; on an NPC, talk to it; on the ground, go there -->
    <qg:on-select>
      <q:if condition="{other != null and other.kind in ['Rat', 'Wolf', 'Bear', 'Hero']}">
        <qg:send command="attack" who="{other.id}" />
        <q:elseif condition="{other != null and other.kind in ['Trader', 'Captain']}">
          <q:set name="talking" value="{other.id}" />
          <qg:open-overlay name="talk" />
        </q:elseif>
        <q:else><qg:send command="go" to="{ {'x': cursor.col, 'y': cursor.row} }" /></q:else>
      </q:if>
    </qg:on-select>

    <!-- what happens, seen: the server's events for what this player sees -->
    <qg:on-event name="hit"><qg:emit text="{str(value)}" at="{at}" color="#ff5555" /><qg:play sound="hit" at="{at}" /></qg:on-event>
    <qg:on-event name="heal"><qg:emit text="{'+' + str(value)}" at="{at}" color="#55ff55" /></qg:on-event>
    <qg:on-event name="level"><qg:emit text="{'LEVEL ' + str(value)}" at="{at}" color="#ffaa00" size="12" /><qg:play sound="level" /></qg:on-event>
    <qg:on-event name="fallen"><qg:shake frames="12" strength="3" /></qg:on-event>
    <qg:on-event name="npc-says"><q:set name="said" value="{who + ': ' + text}" /></qg:on-event>
    <qg:on-refused><q:set name="note" value="{reason}" /></qg:on-refused>   <!-- a command the server said no to -->

    <qg:on-input action="bag"><qg:open-overlay name="bag" /></qg:on-input>
    <qg:on-input action="quests"><qg:open-overlay name="quests" /></qg:on-input>
    <qg:on-input action="chat"><qg:open-overlay name="chat" /></qg:on-input>

    <qg:hud position="top-left" size="10">
      <qg:text value="{me().name + '   ' + tr('Level') + ' ' + str(me().level)}" color="#ffff55" />
      <qg:bar value="{me().hp}" max="{me().max_hp}" width="90" />
      <qg:bar value="{me().xp - 50 * (me().level - 1) * (me().level - 1)}" max="{50 * me().level * me().level - 50 * (me().level - 1) * (me().level - 1)}" width="90" color="#5599ff" />
      <qg:text value="{str(balance('gold')) + ' ' + tr('gold')}" color="#ffaa00" />
    </qg:hud>
    <qg:hud position="bottom-left" size="9">
      <qg:text value="{chat_lines(6)}" />                         <!-- the last lines of every channel this player hears -->
      <qg:text value="{said}" color="#55ffff" />
      <qg:text value="{note}" color="#ff5555" />
    </qg:hud>
    <qg:hud position="top-right" size="9">
      <qg:text value="{clock_text() + (' ☾' if is_night() else '')}" color="#aaaaaa" />
      <qg:text value="{str(world_online()) + ' ' + tr('online') + '   ' + str(ping()) + ' ms'}" color="#aaaaaa" />
    </qg:hud>
  </qg:scene>

  <!-- ===== Overlays over the world, which goes on under them (it is the server's: it never stands still) ===== -->

  <qg:overlay name="bag" freeze="false">
    <qg:hud position="top-center" size="12"><qg:text value="{tr('BAG') + '   ' + str(balance('gold')) + ' ' + tr('gold')}" color="#ffff55" /></qg:hud>
    <qg:menu position="center" source="{me().bag}" as="it" rows="10">
      <qg:button label="{it.name + ' x' + str(it.count)}">
        <q:if condition="{slot(it.name) != ''}"><qg:send command="equip" item="{it.name}" />
          <q:else><qg:send command="use" item="{it.name}" /></q:else>
        </q:if>
      </qg:button>
    </qg:menu>
    <qg:on-input action="cancel"><qg:close-overlay /></qg:on-input>
  </qg:overlay>

  <!-- an NPC: what the player types goes to its agent; its answers come back as npc-says; the shop's list is
       there too, at the list's prices, for whoever would rather not haggle -->
  <q:set name="talk_text" value="" />
  <qg:overlay name="talk" freeze="false">
    <qg:hud position="top-center" size="11"><qg:text value="{entity(talking).title}" color="#55ffff" /></qg:hud>
    <qg:hud position="center" size="10"><qg:text value="{said}" /></qg:hud>
    <qg:menu position="bottom-center">
      <qg:field label="Say" bind="talk_text">
        <qg:send command="talk" npc="{talking}" text="{talk_text}" />
        <q:set name="talk_text" value="" />
      </qg:field>
      <qg:button label="The list" if="{entity(talking).kind == 'Trader'}"><qg:open-overlay name="shop" /></qg:button>
      <qg:button label="Back"><qg:close-overlay /></qg:button>
    </qg:menu>
  </qg:overlay>

  <qg:overlay name="shop" freeze="false">
    <qg:menu position="center" source="{items_for_sale('marta')}" as="it" rows="8">
      <qg:button label="{it.name + '   ' + str(it.price) + ' ' + tr('gold')}"><qg:send command="buy" item="{it.name}" /></qg:button>
    </qg:menu>
    <qg:on-input action="cancel"><qg:close-overlay /></qg:on-input>
  </qg:overlay>

  <qg:overlay name="quests" freeze="false">
    <qg:hud position="center" size="11">
      <qg:text value="{quest_title(me().quest) if len(me().quest) > 0 else tr('No quest. Captain Rhea, at the gate, has work.')}" />
      <qg:text value="{quest_progress(me().quest)}" color="#aaaaaa" />
    </qg:hud>
    <qg:on-input action="cancel"><qg:close-overlay /></qg:on-input>
  </qg:overlay>

  <!-- the chat: a channel and a line; /w name for a whisper -->
  <q:set name="channel" value="say" />
  <q:function name="next_channel" params="now">
    <q:set name="all" value="{['say', 'yell', 'trade', 'party', 'help']}" />
    <q:loop var="k" from="0" to="4"><q:if condition="{all[k] == now}"><q:return value="{all[(k + 1) % 5]}" /></q:if></q:loop>
    <q:return value="{'say'}" />
  </q:function>
  <qg:overlay name="chat" freeze="false">
    <qg:menu position="bottom-left">
      <qg:button label="{'[' + channel + ']'}"><q:set name="channel" value="{next_channel(channel)}" /></qg:button>
      <qg:field label="" bind="typed">
        <qg:chat channel="{channel}" text="{typed}" />
        <q:set name="typed" value="" />
        <qg:close-overlay />
      </qg:field>
    </qg:menu>
    <qg:on-input action="cancel"><qg:close-overlay /></qg:on-input>
  </qg:overlay>

  <qg:language lang="pt" name="Português">
    <qg:phrase text="Enter the world" as="Entrar no mundo" />
    <qg:phrase text="Make an account" as="Criar uma conta" />
    <qg:phrase text="in the world now" as="no mundo agora" />
    <qg:phrase text="Level" as="Nível" />
    <qg:phrase text="gold" as="ouro" />
    <qg:phrase text="online" as="online" />
    <qg:phrase text="BAG" as="MOCHILA" />
    <qg:phrase text="Say" as="Dizer" />
    <qg:phrase text="The list" as="A lista" />
    <qg:phrase text="Back" as="Voltar" />
    <qg:phrase text="No quest. Captain Rhea, at the gate, has work." as="Nenhuma missão. A capitã Rhea, no portão, tem trabalho." />
  </qg:language>
</q:application>
