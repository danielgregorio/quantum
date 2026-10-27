<q:application id="outpost-server" type="gameserver">

  <!-- Outpost's world, as Phase 4 of PLAN_GAME_SERVER.md plays it: a frontier town, the sewers under it, the forest
       east of its gate and a cave north-east, where the Old Bear sleeps. A player signs in with the site's account
       and comes into the temple; Captain Rhea at the gate gives the town's quests, Old Marta in her shop sells and
       buys, and the rats, the wolves and the bear fight back. The world holds the rules; the game the players run is
       outpost.q, next to this file. What Outpost will be (Marta and Rhea who talk, the Director, the admin's page,
       the history) is draft/outpost.server.q: those tags come with Phases 5 and 6. -->

  <q:gameserver name="outpost" client="outpost.q" tick="10" players="500" accounts="site">

    <!-- the map the game draws too: its layer walls is what no one walks through, its areas name the places
         (temple, shop-counter, town, gate, sewers, forest, cave). Drawn by scripts/art/outpost.py -->
    <q:map name="mainland" tiled="maps/mainland.tmx" walls="walls" />

    <!-- a day of an hour, a quarter of it night: more wolves -->
    <q:clock day="60m" night="0.25" />

    <!-- every gold piece and every thing moves by the ledger: a hero comes in with twenty gold; Marta's gold is
         what the heroes paid her -->
    <q:currency name="gold" start="20" />
    <q:item name="cheese" heals="10" price="2" />
    <q:item name="meat" heals="25" price="5" />
    <q:item name="health-potion" heals="50" price="40" />
    <q:item name="wooden-sword" slot="weapon" attack="3" price="50" />
    <q:item name="iron-sword" slot="weapon" attack="7" price="300" />
    <q:item name="leather-armor" slot="armor" defense="3" price="80" />
    <q:item name="fur" worth="15" />
    <q:item name="bear-claw" worth="500" />

    <!-- a player's hero, kept between sessions: it comes back where it was -->
    <q:entity name="hero" kind="Hero" per-player="true" persist="true" speed="4/s" hp="100" attack="5" defense="2">
      <q:field name="name" value="{account.name}" />
      <q:field name="level" value="1" />
      <q:field name="weapon" value="" />
      <q:field name="armor" value="" />
      <q:field name="xp" value="0" private="true" />
      <q:field name="quest" value="{ {} }" private="true" />
      <q:field name="kills" value="0" private="true" />
    </q:entity>

    <!-- the town's two: they stand where they are made, and no one fights them -->
    <q:entity name="marta" kind="Trader" title="Old Marta">
      <q:field name="gold" value="300" private="true" />
    </q:entity>
    <q:entity name="rhea" kind="Captain" title="Captain Rhea" />

    <!-- the beasts: a brain of states, run by the world; a beast with no hero near sleeps -->
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
        <q:state name="flee" do="flee" from="{nearest(it, 'Hero', 9)}" for="6s" then="roam" />
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

    <!-- where each one lives, and how soon a beast comes back -->
    <q:spawn entity="marta" area="shop-counter" count="1" />
    <q:spawn entity="rhea" area="gate" count="1" />
    <q:spawn entity="rat" area="sewers" count="14" respawn="30s" />
    <q:spawn entity="wolf" area="forest" count="10" night-count="20" respawn="60s" />
    <q:spawn entity="bear" area="cave" count="1" respawn="15m" />

    <!-- the town's quests, from Captain Rhea, as the hero's level allows -->
    <q:quest name="sewers" title="Rats in the sewers" goal="kill:Rat:10" level="1" reward="gold:60, xp:100" />
    <q:quest name="pelts" title="Pelts for the winter" goal="bring:fur:5" level="3" reward="gold:150, xp:300" />
    <q:quest name="old-bear" title="The Old Bear" goal="bring:bear-claw:1" level="8"
             reward="gold:800, item:iron-sword, xp:2000" />

    <!-- what each player sees: the entities near its hero. Only this, and what changes in it, goes to its game -->
    <q:view name="around" where="{near(it, me, 9)}" />

    <!-- ===== What a player may ask: each command runs whole or not at all, as the player who sent it (me) ===== -->

    <!-- a step: the game shows it at once (predict), the world says yes or puts the hero back -->
    <q:command name="step" params="dir" limit="8/s" predict="true">
      <q:require condition="{me.hp > 0}" else="You have fallen." />
      <q:require condition="{walkable(ahead(me, dir))}" else="A wall." />
      <q:move entity="{me}" to="{ahead(me, dir)}" />
    </q:command>

    <!-- a click on the map: the way there, a step at a time -->
    <q:command name="go" params="to" limit="2/s">
      <q:require condition="{walkable(to)}" else="No one can stand there." />
      <q:travel entity="{me}" to="{to}" />
    </q:command>

    <q:command name="attack" params="who" limit="4/s">
      <q:require condition="{entity(who) != null and sees(me, who)}" else="You cannot see it." />
      <q:require condition="{entity(who).kind != 'Trader' and entity(who).kind != 'Captain'}"
                 else="Not the townsfolk." />
      <q:require condition="{entity(who).kind != 'Hero' or not in_area(me, 'town')}" else="Not in the town." />
      <q:require condition="{who != me.id}" else="Not yourself." />
      <q:set name="me.target" value="{who}" />
    </q:command>

    <q:command name="use" params="item" limit="2/s">
      <q:require condition="{has(me, item)}" else="You have none." />
      <q:require condition="{heals(item) > 0}" else="Not to eat or drink." />
      <q:take from="{me}" item="{item}" />
      <q:set name="me.hp" value="{min(me.max_hp, me.hp + heals(item))}" />
      <q:emit event="heal" at="{me}" value="{heals(item)}" />
    </q:command>

    <q:command name="equip" params="item">
      <q:require condition="{has(me, item)}" else="You have none." />
      <q:require condition="{slot(item) != ''}" else="Not to wear." />
      <q:if condition="{slot(item) == 'weapon'}">
        <q:set name="me.attack" value="{me.attack - bonus(me.weapon, 'attack') + bonus(item, 'attack')}" />
        <q:set name="me.weapon" value="{item}" />
        <q:else>
          <q:set name="me.defense" value="{me.defense - bonus(me.armor, 'defense') + bonus(item, 'defense')}" />
          <q:set name="me.armor" value="{item}" />
        </q:else>
      </q:if>
    </q:command>

    <!-- Marta's shop: what has a price, at its price, paid to her; she buys at half of what a thing is worth, with
         the gold she has -->
    <q:command name="buy" params="item" limit="2/s">
      <q:require condition="{nearest(me, 'Trader', 3) != null}" else="Marta is too far." />
      <q:require condition="{price(item) > 0}" else="Marta does not sell that." />
      <q:require condition="{balance(me) >= price(item)}" else="Not enough gold." />
      <q:pay from="{me}" to="{nearest(me, 'Trader', 3)}" amount="{price(item)}" />
      <q:give to="{me}" item="{item}" />
    </q:command>
    <q:command name="sell" params="item" limit="2/s">
      <q:require condition="{nearest(me, 'Trader', 3) != null}" else="Marta is too far." />
      <q:require condition="{has(me, item)}" else="You have none." />
      <q:require condition="{balance(nearest(me, 'Trader', 3)) >= max(price(item), bonus(item, 'worth')) // 2}"
                 else="Marta cannot pay that now." />
      <q:take from="{me}" item="{item}" />
      <q:pay from="{nearest(me, 'Trader', 3)}" to="{me}" amount="{max(price(item), bonus(item, 'worth')) // 2}" />
    </q:command>

    <!-- Rhea's quests: one at a time, as the hero's level allows -->
    <q:command name="take-quest" params="name">
      <q:require condition="{nearest(me, 'Captain', 3) != null}" else="Captain Rhea is at the gate." />
      <q:require condition="{quest_title(name) != ''}" else="No such quest." />
      <q:require condition="{len(me.quest) == 0}" else="One quest at a time." />
      <q:require condition="{me.level >= quest_level(name)}" else="Come back when you are stronger." />
      <q:set name="me.quest" value="{ {'name': name, 'done': 0} }" />
    </q:command>
    <q:command name="turn-in">
      <q:require condition="{nearest(me, 'Captain', 3) != null}" else="Captain Rhea is at the gate." />
      <q:require condition="{quest_done(me)}" else="It is not done." />
      <q:say to="{me}" text="Well done. {quest_title(me.quest.name)}: that is the reward." />
      <q:reward to="{me}" quest="{me.quest.name}" />
      <q:set name="me.quest" value="{ {} }" />
      <q:call function="gain" args="{me}, {0}" />
    </q:command>

    <!-- ===== The world's rules, every so often ===== -->

    <!-- a blow every two seconds, from each one next to its target -->
    <q:every interval="2s">
      <q:loop items="{fighting()}" var="a">
        <!-- one killed earlier in these two seconds strikes nothing, and is struck by no one -->
        <q:if condition="{entity(a.id) != null and entity(a.target) != null}">
          <q:call function="strike" args="{a}, {entity(a.target)}" />
        </q:if>
      </q:loop>
    </q:every>

    <!-- a hero out of a fight gets back a point of health a level every five seconds -->
    <q:every interval="5s">
      <q:loop items="{heroes()}" var="h">
        <q:if condition="{h.hp < h.max_hp and not in_fight(h)}">
          <q:set name="h.hp" value="{min(h.max_hp, h.hp + h.level)}" />
        </q:if>
      </q:loop>
    </q:every>

    <q:function name="strike" params="a, b">
      <q:set name="hit" value="{max(1, random(a.attack // 2, a.attack) - b.defense // 2)}" />
      <q:set name="b.hp" value="{b.hp - hit}" />
      <q:emit event="hit" at="{b}" value="{hit}" />
      <q:if condition="{b.hp <= 0}"><q:kill entity="{b}" by="{a}" /></q:if>
    </q:function>

    <!-- a beast killed: its worth in experience to its killer's party near, its loot to the killer, a quest's count -->
    <q:on-death kind="Rat, Wolf, Bear" as="beast" by="killer">
      <q:set name="share" value="{party_near(killer, 10)}" />
      <q:loop items="{share}" var="h">
        <q:call function="gain" args="{h}, {beast.worth // len(share)}" />
      </q:loop>
      <q:loot of="{beast}" to="{killer}" />
      <q:set name="killer.kills" value="{killer.kills + 1}" />
      <q:set name="killer.target" value="{''}" />
      <q:if condition="{quest_goal(killer) == 'kill:' + beast.kind}">
        <q:set name="killer.quest.done" value="{killer.quest.done + 1}" />
      </q:if>
    </q:on-death>

    <!-- a hero who falls loses a tenth of the experience and wakes at the temple, whole -->
    <q:on-death kind="Hero" as="hero">
      <q:set name="hero.xp" value="{hero.xp * 9 // 10}" />
      <q:set name="hero.hp" value="{hero.max_hp}" />
      <q:set name="hero.target" value="{''}" />
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
      <q:say to="{me}" text="Welcome to Outpost, {me.name}." />
    </q:on-join>

    <!-- ===== Together ===== -->

    <q:chat channels="say:7, yell:30, trade, party, help" whisper="true" limit="3/5s" filter="moderate" />
    <q:party size="5" />
    <q:trade />
  </q:gameserver>
</q:application>
