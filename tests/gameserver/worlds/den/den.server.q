<q:application id="den-server" type="gameserver">

  <!-- The den: the world of the game server's Phase 3 and 4 tests (PLAN_GAME_SERVER.md), on the meadow's map. A rat
       lives in the square: it roams near where it was made, bites a hero who comes near, dies of two blows, leaves
       cheese and a little gold to whoever killed it, and comes back thirty seconds later. At night there are two. A
       hero walks there by a click (q:travel, around the wall), and a step is shown by the game at once (predict).
       Gold and things are the ledger's: bought, sold, eaten, given, looted, and counted. -->

  <q:gameserver name="den" tick="10" players="10" client="den.q">
    <q:map name="den" tiled="den.tmx" />
    <q:clock day="10m" night="0.25" />

    <!-- the ledger: gold, and two things; a hero comes in with ten gold -->
    <q:currency name="gold" start="10" />
    <q:item name="cheese" price="2" heals="5" />
    <q:item name="sword" price="8" slot="weapon" attack="3" />

    <!-- together: a chat (near, far, the party's, everyone's help), a party of three, a trade, a quest -->
    <q:chat channels="say:7, yell:30, party, help" whisper="true" limit="3/5s" filter="moderate" />
    <q:party size="3" />
    <q:trade />
    <q:quest name="rats" title="Rats in the square" goal="kill:Rat:2" level="1" reward="gold:20, xp:50, item:sword" />

    <q:entity name="hero" kind="Hero" per-player="true" speed="10/s" hp="30" attack="5" defense="1">
      <q:field name="name" value="{account.name}" />
      <q:field name="mood" value="calm" />
      <q:field name="kills" value="0" />
      <q:field name="xp" value="0" private="true" />
      <q:field name="quest" value="{ {} }" private="true" />
    </q:entity>

    <q:entity name="rat" kind="Rat" speed="2/s" hp="10" attack="2" defense="0">
      <q:brain>
        <q:state name="roam" initial="true" do="wander" within="2">
          <q:when condition="{nearest(it, 'Hero', 3) != null}" become="bite" />
        </q:state>
        <q:state name="bite" do="chase" target="{nearest(it, 'Hero', 6)}">
          <q:when condition="{it.hp < 3}" become="flee" />
          <q:when condition="{it.target == ''}" become="roam" />
        </q:state>
        <q:state name="flee" do="flee" from="{nearest(it, 'Hero', 8)}" for="3s" then="roam" />
      </q:brain>
      <q:loot><q:drop item="cheese" /><q:drop gold="1-3" /></q:loot>
    </q:entity>

    <q:spawn entity="rat" area="square" count="1" night-count="2" respawn="30s" />

    <q:view name="around" where="{near(it, me, 8)}" />

    <!-- a step the game shows at once: the world says yes, or the hero walks back. A loud hero stands. -->
    <q:command name="step" params="dir" predict="true">
      <q:require condition="{walkable(ahead(me, dir))}" else="A wall." />
      <q:require condition="{me.mood != 'loud'}" else="You are shouting." />
      <q:move entity="{me}" to="{ahead(me, dir)}" />
    </q:command>

    <q:command name="go" params="to">
      <q:travel entity="{me}" to="{to}" />
    </q:command>

    <q:command name="attack" params="who">
      <q:require condition="{entity(who) != null and sees(me, who)}" else="You cannot see it." />
      <q:set name="me.target" value="{who}" />
    </q:command>

    <q:command name="shout">
      <q:set name="me.mood" value="loud" />
    </q:command>
    <q:command name="hush">
      <q:set name="me.mood" value="calm" />
    </q:command>

    <!-- the ledger's commands: a thing bought for its price, sold for half, eaten, gold given -->
    <q:command name="buy" params="item">
      <q:require condition="{item(item) != null}" else="No such thing." />
      <q:take from="{me}" amount="{price(item)}" />
      <q:give to="{me}" item="{item}" />
    </q:command>
    <q:command name="sell" params="item">
      <q:take from="{me}" item="{item}" />
      <q:give to="{me}" amount="{price(item) // 2}" />
    </q:command>
    <q:command name="eat" params="item">
      <q:require condition="{heals(item) > 0}" else="Not to eat." />
      <q:take from="{me}" item="{item}" />
      <q:set name="me.hp" value="{min(me.max_hp, me.hp + heals(item))}" />
    </q:command>
    <q:command name="tip" params="who, amount">
      <q:require condition="{entity(who) != null and who != me.id}" else="Nobody to tip." />
      <q:pay from="{me}" to="{who}" amount="{amount}" />
    </q:command>

    <!-- a quest, taken and turned in -->
    <q:command name="take-quest" params="name">
      <q:require condition="{quest_title(name) != ''}" else="No such quest." />
      <q:require condition="{len(me.quest) == 0}" else="One quest at a time." />
      <q:set name="me.quest" value="{ {'name': name, 'done': 0} }" />
    </q:command>
    <q:command name="turn-in">
      <q:require condition="{quest_done(me)}" else="It is not done." />
      <q:reward to="{me}" quest="{me.quest.name}" />
      <q:set name="me.quest" value="{ {} }" />
    </q:command>

    <!-- three rats in the east, for five seconds -->
    <q:command name="call-rats">
      <q:spawn entity="rat" area="east" count="3" for="5s" />
    </q:command>

    <!-- a blow a second, from each one next to its target -->
    <q:every interval="1s">
      <q:loop items="{fighting()}" var="a">
        <!-- one killed earlier in this second strikes nothing, and is struck by no one -->
        <q:if condition="{entity(a.id) != null and entity(a.target) != null}">
          <q:call function="strike" args="{a}, {entity(a.target)}" />
        </q:if>
      </q:loop>
    </q:every>

    <q:function name="strike" params="a, b">
      <q:set name="hit" value="{max(1, a.attack - b.defense)}" />
      <q:set name="b.hp" value="{b.hp - hit}" />
      <q:emit event="hit" at="{b}" value="{hit}" />
      <q:if condition="{b.hp <= 0}"><q:kill entity="{b}" by="{a}" /></q:if>
    </q:function>

    <q:on-death kind="Rat" as="rat" by="killer">
      <q:loot of="{rat}" to="{killer}" />
      <q:set name="killer.kills" value="{killer.kills + 1}" />
      <q:set name="killer.target" value="{''}" />
      <q:if condition="{quest_goal(killer) == 'kill:Rat'}">
        <q:set name="killer.quest.done" value="{killer.quest.done + 1}" />
      </q:if>
    </q:on-death>

    <!-- a hero who falls wakes at the west, whole -->
    <q:on-death kind="Hero" as="hero">
      <q:set name="hero.hp" value="{hero.max_hp}" />
      <q:set name="hero.target" value="{''}" />
      <q:move entity="{hero}" to="west" />
      <q:emit event="fallen" at="{hero}" />
    </q:on-death>

    <q:on-join>
      <q:if condition="{me.at == null}"><q:move entity="{me}" to="west" /></q:if>
      <q:say to="{me}" text="Welcome to the den, {me.name}." />
    </q:on-join>
  </q:gameserver>
</q:application>
