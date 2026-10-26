<q:application id="outpost-server" type="gameserver">

  <!-- Outpost's world, as it should read: Phase 0 of PLAN_GAME_SERVER.md, written before any of its tags exist.
       A frontier town, its sewers, the forest around it and a cave, for five hundred players at once. What the
       world holds, what each player sees and what each player may do are said here; the network, the saving, the
       accounts, the history and the admin's page are the Quantum's. The game the players run is outpost.q, next
       to this file: it draws what the server says and sends what the player asks. -->

  <q:gameserver name="outpost" client="outpost.q" tick="10" players="500" accounts="site">

    <!-- the client's own map: the walls the player sees are the walls the server keeps. The areas layer names the
         places (temple, shop-counter, gate, sewers, forest, cave, town) and the safe ones (no one attacks a hero
         in the town) -->
    <q:map name="mainland" tiled="maps/mainland.tmx" walls="walls" areas="areas" safe="town" />

    <!-- a day of an hour, a quarter of it night: more wolves, and the Director's mood -->
    <q:clock day="60m" night="0.25" />

    <!-- every gold piece and every item moves by the ledger: none is made or lost but by q:give, q:pay, q:take
         and a loot, and the admin's page shows where they come from and where they go -->
    <q:currency name="gold" />
    <q:item name="cheese" heals="10" price="2" />
    <q:item name="meat" heals="25" price="5" />
    <q:item name="health-potion" heals="50" price="40" />
    <q:item name="wooden-sword" slot="weapon" attack="3" price="50" />
    <q:item name="iron-sword" slot="weapon" attack="7" price="300" />
    <q:item name="leather-armor" slot="armor" defense="3" price="80" />
    <q:item name="fur" price="15" />
    <q:item name="bear-claw" price="500" />

    <!-- what the players may know: the town's story, read by the NPCs and the Director -->
    <q:knowledge name="lore">
      <q:source type="directory" path="lore" pattern="*.md" />
    </q:knowledge>

    <!-- a player's hero: one an account, kept between sessions. Every entity has its place (at, facing), its
         kind (the client's prefab), and, if it fights, hp, max_hp, attack, defense and target. A private field
         goes only to its player; the others go to whoever sees the hero -->
    <q:entity name="hero" kind="Hero" per-player="true" persist="true" speed="4/s" hp="100" attack="5" defense="2">
      <q:field name="name" value="{account.name}" />
      <q:field name="outfit" value="{account.outfit}" />
      <q:field name="level" value="1" />
      <q:field name="weapon" value="" />
      <q:field name="armor" value="" />
      <q:field name="xp" value="0" private="true" />
      <q:field name="quest" value="{ {} }" private="true" />
      <q:field name="kills" value="{ {} }" private="true" />
    </q:entity>

    <!-- the beasts: a brain of states, as a qg:prefab's, run by the server; a beast with no hero near sleeps -->
    <q:entity name="rat" kind="Rat" speed="2/s" hp="20" attack="3" defense="0" worth="5">
      <q:brain>
        <q:state name="roam" initial="true" do="wander" within="5">
          <q:when condition="{nearest(it, 'Hero', 3) != null}" become="bite" />
        </q:state>
        <q:state name="bite" do="chase" target="{nearest(it, 'Hero', 6)}">
          <q:when condition="{it.target == ''}" become="roam" />
        </q:state>
      </q:brain>
      <q:loot><q:drop item="cheese" chance="0.5" /><q:drop gold="0-3" /></q:loot>
    </q:entity>
    <q:entity name="wolf" kind="Wolf" speed="3/s" hp="60" attack="8" defense="2" worth="25">
      <q:brain>
        <q:state name="roam" initial="true" do="wander" within="8">
          <q:when condition="{nearest(it, 'Hero', 5) != null}" become="hunt" />
        </q:state>
        <q:state name="hunt" do="chase" target="{nearest(it, 'Hero', 9)}">
          <q:when condition="{it.hp < 15}" become="flee" />
          <q:when condition="{it.target == ''}" become="roam" />
        </q:state>
        <q:state name="flee" do="flee" from="{it.target}" for="6s" then="roam" />
      </q:brain>
      <q:loot><q:drop item="meat" chance="0.6" /><q:drop item="fur" chance="0.3" /><q:drop gold="2-8" /></q:loot>
    </q:entity>
    <q:entity name="bear" kind="Bear" speed="2/s" hp="600" attack="22" defense="8" worth="400">
      <q:brain>
        <q:state name="sleep" initial="true" do="stand">
          <q:when condition="{nearest(it, 'Hero', 4) != null}" become="rage" />
        </q:state>
        <q:state name="rage" do="chase" target="{nearest(it, 'Hero', 12)}">
          <q:when condition="{it.target == ''}" become="sleep" />
        </q:state>
      </q:brain>
      <q:loot><q:drop item="bear-claw" chance="0.25" /><q:drop gold="60-120" /></q:loot>
    </q:entity>

    <!-- where the beasts live, and how soon they come back -->
    <q:spawn entity="rat" area="sewers" count="14" respawn="30s" />
    <q:spawn entity="wolf" area="forest" count="10" night-count="20" respawn="60s" />
    <q:spawn entity="bear" area="cave" count="1" respawn="15m" announce="The Old Bear wakes in the cave." />

    <!-- the quests Captain Rhea may give: her agent picks among these, it never makes one up -->
    <q:quest name="sewers" title="Rats in the sewers" goal="kill:Rat:10" level="1" reward="gold:60, xp:100" />
    <q:quest name="pelts" title="Pelts for the winter" goal="bring:fur:5" level="3" reward="gold:150, xp:300" />
    <q:quest name="old-bear" title="The Old Bear" goal="bring:bear-claw:1" level="8" reward="gold:800, item:iron-sword, xp:2000" />

    <!-- Old Marta, the trader: she talks, haggles and remembers. Her agent acts only through her tools, which are
         commands: whatever it is told, a price stays within a fifth of the list's -->
    <q:npc name="marta" kind="Trader" at="shop-counter" title="Old Marta">
      <q:agent model="small" knowledge="lore" memory="per-player" budget="40/day" maxIterations="4">
        <q:instruction>You are Old Marta, who has kept Outpost's shop for forty winters. You are wary and you love
          to haggle; you sell and buy only with your tools, and you remember who bargained fairly and who did not.
          Answer in the player's language, in two sentences at most.</q:instruction>
        <q:tool command="npc-sell" description="Sell the player an item, at a price you both agreed" />
        <q:tool command="npc-buy" description="Buy an item from the player, at a price you both agreed" />
      </q:agent>
      <!-- when the agent is off, out of budget or slow: lines, and the shop's list (outpost.q's shop) -->
      <q:fallback>
        <q:line text="Potions, swords, armour. Look at the list." />
      </q:fallback>
    </q:npc>

    <!-- Captain Rhea keeps the gate and gives the quests, one at a time, as the player's level allows -->
    <q:npc name="rhea" kind="Captain" at="gate" title="Captain Rhea">
      <q:agent model="small" knowledge="lore" memory="per-player" budget="40/day" maxIterations="4">
        <q:instruction>You are Captain Rhea, who keeps Outpost's gate. You give one quest at a time from your
          tools, fit for the player's level, and you reward it when it is done. Brief, a soldier's words.</q:instruction>
        <q:tool command="give-quest" description="Give the player one of the town's quests" />
        <q:tool command="reward-quest" description="Reward the player's quest if it is done" />
      </q:agent>
      <q:fallback>
        <q:line text="The sewers are full of rats. Ten of them, and come back." />
      </q:fallback>
    </q:npc>

    <!-- the Director, the game's master: every ten minutes it looks at the world and may propose an event; what
         it proposes waits for an admin's yes on /admin (approve="admin"), as the Hive's actuator waits for its
         whitelist -->
    <q:director every="10m" approve="admin" knowledge="lore" budget="30/day">
      <q:instruction>You are the fate of Outpost. Keep the town alive: when it is quiet, stir it; when the
        newcomers die too often, spare them. Propose one event at a time, and say why.</q:instruction>
      <q:look value="{ {'online': online(), 'night': is_night(), 'deaths_last_hour': deaths(60), 'gold': supply('gold'), 'levels': levels()} }" />
      <q:tool command="wolf-raid" description="Wolves at the town's gate for ten minutes" />
      <q:tool command="wake-the-bear" description="The Old Bear wakes now" />
      <q:tool command="announce" description="A line to every player" />
    </q:director>

    <!-- what each player sees: the entities near its hero. Only this, and what changes in it, goes to its client -->
    <q:view name="around" where="{near(it, me, 9)}" />

    <!-- ===== What a player may ask: each command runs whole or not at all, as the player who sent it (me) ===== -->

    <!-- a step: the client shows it at once (predict), the server says yes or puts the hero back -->
    <q:command name="step" params="dir" limit="8/s" predict="true">
      <q:require condition="{me.hp > 0 and walkable(ahead(me, dir))}" />
      <q:move entity="{me}" to="{ahead(me, dir)}" />
    </q:command>

    <!-- a click on the map: the way there, a step at a time -->
    <q:command name="go" params="to" limit="2/s">
      <q:require condition="{me.hp > 0 and walkable(to)}" />
      <q:travel entity="{me}" to="{to}" />
    </q:command>

    <q:command name="attack" params="who" limit="4/s">
      <q:require condition="{sees(me, who)}" />
      <q:require condition="{who.kind != 'Hero' or not in_area(me, 'town')}" else="Not in the town." />
      <q:set name="me.target" value="{who.id}" />
    </q:command>

    <q:command name="use" params="item" limit="2/s">
      <q:require condition="{has(me, item) and heals(item) > 0}" />
      <q:take from="{me}" item="{item}" />
      <q:set name="me.hp" value="{min(me.max_hp, me.hp + heals(item))}" />
      <q:emit event="heal" at="{me}" value="{heals(item)}" />
    </q:command>

    <q:command name="equip" params="item">
      <q:require condition="{has(me, item) and slot(item) != ''}" />
      <q:if condition="{slot(item) == 'weapon'}">
        <q:set name="me.attack" value="{me.attack - bonus(me.weapon, 'attack') + bonus(item, 'attack')}" />
        <q:set name="me.weapon" value="{item}" />
        <q:else>
          <q:set name="me.defense" value="{me.defense - bonus(me.armor, 'defense') + bonus(item, 'defense')}" />
          <q:set name="me.armor" value="{item}" />
        </q:else>
      </q:if>
    </q:command>

    <!-- the shop's list, without a word: the list's price, near Marta -->
    <q:command name="buy" params="item" limit="2/s">
      <q:require condition="{near(me, 'marta', 3)}" else="Marta is too far." />
      <q:require condition="{balance(me, 'gold') >= price(item)}" else="Not enough gold." />
      <q:pay from="{me}" to="marta" amount="{price(item)}" />
      <q:give to="{me}" item="{item}" />
    </q:command>

    <!-- words to an NPC: its agent answers in its own time (to whoever is near: an event) and may use its tools -->
    <q:command name="talk" params="npc, text" limit="1/3s">
      <q:require condition="{near(me, npc, 3)}" else="Come closer." />
      <q:ask npc="{npc}" text="{text}" />
    </q:command>

    <!-- ===== The NPCs' tools: commands only an NPC's agent may run (by="npc"), as the player it talks to ===== -->

    <q:command name="npc-sell" params="item, price" by="npc">
      <q:require condition="{price >= 0.8 * price(item) and price <= 1.2 * price(item)}" else="Not at that price." />
      <q:require condition="{balance(me, 'gold') >= price}" else="You cannot pay that." />
      <q:pay from="{me}" to="{npc}" amount="{price}" />
      <q:give to="{me}" item="{item}" />
    </q:command>
    <q:command name="npc-buy" params="item, price" by="npc">
      <q:require condition="{has(me, item) and price >= 0.4 * price(item) and price <= 0.6 * price(item)}" else="Not at that price." />
      <q:take from="{me}" item="{item}" />
      <q:pay from="{npc}" to="{me}" amount="{price}" />
    </q:command>
    <q:command name="give-quest" params="quest" by="npc">
      <q:require condition="{len(me.quest) == 0 and me.level >= quest_level(quest)}" else="One quest at a time." />
      <q:set name="me.quest" value="{ {'name': quest, 'done': 0} }" />
    </q:command>
    <q:command name="reward-quest" by="npc">
      <q:require condition="{quest_done(me)}" else="It is not done." />
      <q:reward to="{me}" quest="{me.quest.name}" />
      <q:set name="me.quest" value="{ {} }" />
    </q:command>

    <!-- ===== The Director's tools (by="director"), and the admins' (by="admin") ===== -->

    <q:command name="wolf-raid" by="director, admin">
      <q:spawn entity="wolf" area="gate" count="12" for="10m" />
      <q:say channel="yell" to="all" text="Wolves at the gate!" />
    </q:command>
    <q:command name="wake-the-bear" by="director, admin">
      <q:spawn entity="bear" area="cave" count="1" />
    </q:command>
    <q:command name="announce" params="text" by="director, admin">
      <q:say channel="system" to="all" text="{text}" />
    </q:command>

    <!-- ===== The world's rules, every so often ===== -->

    <!-- a blow every two seconds, from each one next to its target -->
    <q:every interval="2s">
      <q:loop items="{fighting()}" var="a">
        <q:call function="strike" args="{a}, {entity(a.target)}" />
      </q:loop>
    </q:every>

    <!-- a hero out of a fight gets back a point of health a level every five seconds -->
    <q:every interval="5s">
      <q:loop items="{heroes()}" var="h">
        <q:if condition="{h.hp > 0 and h.hp < h.max_hp and not in_fight(h)}">
          <q:set name="h.hp" value="{min(h.max_hp, h.hp + h.level)}" />
        </q:if>
      </q:loop>
    </q:every>

    <q:function name="strike" params="a, b">
      <q:set name="hit" value="{max(0, round(random(a.attack / 2, a.attack)) - round(b.defense / 2))}" />
      <q:set name="b.hp" value="{b.hp - hit}" />
      <q:emit event="hit" at="{b}" value="{hit}" />
      <q:if condition="{b.hp <= 0}"><q:kill entity="{b}" by="{a}" /></q:if>
    </q:function>

    <!-- a beast killed: its worth in experience to its killer's party near, its loot to the killer, a quest's count -->
    <q:on-death kind="Rat, Wolf, Bear" as="beast" by="killer">
      <q:loop items="{party_near(killer, 10)}" var="h">
        <q:call function="gain" args="{h}, {round(beast.worth / len(party_near(killer, 10)))}" />
      </q:loop>
      <q:loot of="{beast}" to="{killer}" />
      <q:if condition="{quest_goal(killer) == 'kill:' + beast.kind}">
        <q:set name="killer.quest.done" value="{killer.quest.done + 1}" />
      </q:if>
    </q:on-death>

    <!-- a hero who falls loses a tenth of the experience and wakes at the temple -->
    <q:on-death kind="Hero" as="hero">
      <q:set name="hero.xp" value="{round(hero.xp * 0.9)}" />
      <q:set name="hero.hp" value="{hero.max_hp}" />
      <q:move entity="{hero}" to="temple" />
      <q:emit event="fallen" at="{hero}" />
    </q:on-death>

    <!-- 50 × level² to the next level: each level ten more health, a point of attack and of defense -->
    <q:function name="gain" params="h, xp">
      <q:set name="h.xp" value="{h.xp + xp}" />
      <q:set name="up" value="{floor(sqrt(h.xp / 50)) + 1 - h.level}" />
      <q:if condition="{up > 0}">
        <q:set name="h.level" value="{h.level + up}" />
        <q:set name="h.max_hp" value="{h.max_hp + 10 * up}" />
        <q:set name="h.attack" value="{h.attack + up}" />
        <q:set name="h.defense" value="{h.defense + up}" />
        <q:emit event="level" at="{h}" value="{h.level}" />
      </q:if>
    </q:function>

    <!-- a player comes into the world: where the hero was, or the temple the first time -->
    <q:on-join>
      <q:if condition="{me.at == null}"><q:move entity="{me}" to="temple" /></q:if>
      <q:say channel="system" to="{me}" text="Welcome to Outpost, {me.name}." />
    </q:on-join>

    <!-- ===== Together ===== -->

    <q:chat channels="say:7, yell:30, trade, party, help" whisper="true" limit="3/5s" filter="moderate" />
    <q:party size="5" share="xp" within="10" />
    <q:trade />

    <!-- the Old Bear's den, for a party alone: a copy of the cave a party enters, and leaves when it is done -->
    <q:room name="bear-den" map="maps/cave.tmx" party="2-5" from="cave-door" back="cave-door" />

    <!-- ===== What the Quantum gives the world ===== -->

    <!-- every command and every rule's change, kept fourteen days with a snapshot every five minutes: the world can
         be opened at any instant of them (quantum gameserver replay), and a player's last minutes undone -->
    <q:history keep="14d" snapshot="5m" />

    <!-- the admin's page: the live map, who is on, any entity, the ledger, the Director's proposals, kick and ban -->
    <q:admin path="/admin" role="gm" />

    <!-- bots that play by the protocol, marked as bots: for the load test and `quantum gameserver audit` -->
    <q:bots brain="explorer" count="0" />
  </q:gameserver>
</q:application>
