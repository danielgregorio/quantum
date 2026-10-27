<q:application id="meadow-server" type="gameserver">

  <!-- The meadow: the world of the game server's Phase 2 tests (PLAN_GAME_SERVER.md). A field of 48 by 32 with a
       wall across it, three areas far apart (west, east, the square), a view of the tiles within five of a hero and
       one of the heroes who shout, wherever they are. A purse is private; a shout, a whisper and the bell are
       events: to whoever sees where, to one player, to everyone. -->

  <q:gameserver name="meadow" tick="10" players="200" client="meadow.q">
    <q:map name="meadow" tiled="meadow.tmx" />

    <q:entity name="hero" kind="Hero" per-player="true" speed="10/s">
      <q:field name="name" value="{account.name}" />
      <q:field name="mood" value="calm" />
      <q:field name="purse" value="0" private="true" />
    </q:entity>

    <q:view name="around" where="{near(it, me, 5)}" />
    <q:view name="loud" where="{it.kind == 'Hero' and it.mood == 'loud'}" />

    <q:command name="step" params="dir">
      <q:require condition="{walkable(ahead(me, dir))}" else="A wall." />
      <q:move entity="{me}" to="{ahead(me, dir)}" />
    </q:command>

    <q:command name="go" params="to">
      <q:move entity="{me}" to="{to}" />
    </q:command>

    <q:command name="earn">
      <q:set name="me.purse" value="{me.purse + 1}" />
    </q:command>

    <q:command name="shout" params="text">
      <q:set name="me.mood" value="loud" />
      <q:emit event="shout" at="{me}" value="{me.name}: {text}" />
    </q:command>

    <q:command name="hush">
      <q:set name="me.mood" value="calm" />
    </q:command>

    <q:command name="whisper" params="to, text">
      <q:require condition="{entity(to) != null}" else="Nobody of that name." />
      <q:emit event="whisper" to="{to}" value="{ {'from': me.name, 'text': text} }" />
    </q:command>

    <q:command name="ring">
      <q:emit event="bell" value="{tick()}" />
    </q:command>

    <!-- an event of a command refused is never heard -->
    <q:command name="boast">
      <q:emit event="shout" at="{me}" value="I have {me.purse}" />
      <q:require condition="{me.purse >= 100}" else="Not rich enough." />
    </q:command>

    <q:on-join>
      <q:if condition="{me.at == null}"><q:move entity="{me}" to="west" /></q:if>
    </q:on-join>
  </q:gameserver>
</q:application>
