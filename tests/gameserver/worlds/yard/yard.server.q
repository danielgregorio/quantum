<q:application id="yard-server" type="gameserver">

  <!-- The yard: the world of the game server's Phase 1 tests (PLAN_GAME_SERVER.md). A walled yard of 12 by 8 with a
       pillar, the gate where a player comes in, a pen. A hero steps a tile at a time, at four steps a second, never
       into a wall; a coin counter shows a private field and a rule every second; a player leaving is kept. -->

  <q:gameserver name="yard" tick="10" players="3">
    <q:map name="yard" tiled="yard.tmx" />

    <q:set name="visits" value="0" />

    <q:entity name="hero" kind="Hero" per-player="true" persist="true" speed="4/s">
      <q:field name="name" value="{account.name}" />
      <q:field name="steps" value="0" />
      <q:field name="coins" value="0" private="true" />
    </q:entity>

    <q:command name="step" params="dir" limit="8/s">
      <q:require condition="{walkable(ahead(me, dir))}" else="A wall." />
      <q:move entity="{me}" to="{ahead(me, dir)}" />
      <q:set name="me.steps" value="{me.steps + 1}" />
    </q:command>

    <!-- to the pen and back: a move of more than a tile is not a step -->
    <q:command name="go" params="to">
      <q:move entity="{me}" to="{to}" />
    </q:command>

    <!-- a coin for a step taken in the pen; none, and the command is undone whole -->
    <q:command name="pick" limit="1/s">
      <q:set name="me.coins" value="{me.coins + 1}" />
      <q:require condition="{in_area(me, 'pen')}" else="No coin here." />
    </q:command>

    <q:command name="tally" params="n">
      <q:set name="me.coins" value="{me.coins + count_to(n)}" />
    </q:command>

    <q:function name="count_to" params="n">
      <q:set name="total" value="0" />
      <q:loop var="k" from="1" to="{n}"><q:set name="total" value="{total + k}" /></q:loop>
      <q:return value="{total}" />
    </q:function>

    <!-- every second, a coin for whoever stands in the pen -->
    <q:every interval="1s">
      <q:loop items="{heroes()}" var="h">
        <q:if condition="{in_area(h, 'pen')}"><q:set name="h.coins" value="{h.coins + 1}" /></q:if>
      </q:loop>
    </q:every>

    <q:on-join>
      <q:set name="visits" value="{visits + 1}" />
      <q:if condition="{me.at == null}"><q:move entity="{me}" to="gate" /></q:if>
    </q:on-join>
  </q:gameserver>
</q:application>
