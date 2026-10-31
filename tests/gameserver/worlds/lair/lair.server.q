<q:application id="lair-server" type="gameserver">

  <!-- The lair: the den's life with nothing else (PLAN_WORLD_ENGINE.md, E3b's world), on the den's map. Rats roam
       the square, bite a hero near, flee when hurt, die of a few blows, leave cheese and gold in the killer's own
       fields (no ledger), and come back; at night there are two. A hero walks there by a click (q:travel), calls a
       pack for a few seconds (q:spawn for=), and wakes at the west when it falls. Rats far from every hero sleep. -->

  <q:gameserver name="lair" tick="10" players="10">
    <q:map name="den" tiled="../den/den.tmx" />
    <q:clock day="1m" night="0.25" />

    <q:entity name="hero" kind="Hero" per-player="true" speed="10/s" hp="30" attack="5" defense="1">
      <q:field name="name" value="{account.name}" />
      <q:field name="kills" value="0" />
      <q:field name="gold" value="10" />
      <q:field name="bag" value="{ {} }" />
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
      <q:loot><q:drop item="cheese" /><q:drop gold="1-3" chance="0.5" /></q:loot>
    </q:entity>

    <q:spawn entity="rat" area="square" count="2" night-count="4" respawn="5s" />

    <q:view name="around" where="{near(it, me, 8)}" />

    <q:command name="step" params="dir">
      <q:require condition="{walkable(ahead(me, dir))}" else="A wall." />
      <q:move entity="{me}" to="{ahead(me, dir)}" />
    </q:command>

    <q:command name="go" params="to">
      <q:travel entity="{me}" to="{to}" />
    </q:command>

    <q:command name="attack" params="who">
      <q:require condition="{entity(who) != null and sees(me, who)}" else="You cannot see it." />
      <q:set name="me.target" value="{who}" />
    </q:command>

    <q:command name="call-rats">
      <q:spawn entity="rat" area="east" count="3" for="2s" />
    </q:command>

    <q:command name="smite" params="who">
      <q:require condition="{entity(who) != null}" else="Nothing there." />
      <q:kill entity="{entity(who)}" by="{me}" />
    </q:command>

    <q:every interval="1s">
      <q:loop items="{fighting()}" var="a">
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
      <q:if condition="{killer != null and killer.kind == 'Hero'}">
        <q:loot of="{rat}" to="{killer}" />
        <q:set name="killer.kills" value="{killer.kills + 1}" />
        <q:set name="killer.target" value="{''}" />
      </q:if>
    </q:on-death>

    <q:on-death kind="Hero" as="hero">
      <q:set name="hero.hp" value="{hero.max_hp}" />
      <q:set name="hero.target" value="{''}" />
      <q:move entity="{hero}" to="west" />
      <q:emit event="fallen" at="{hero}" />
    </q:on-death>

    <q:on-join>
      <q:if condition="{me.at == null}"><q:move entity="{me}" to="west" /></q:if>
    </q:on-join>
  </q:gameserver>
</q:application>
