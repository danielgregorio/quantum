# Changelog

From 1.0, the Core and AI tiers follow semantic versioning: a 1.x release does
not break a program that uses only them, and a break waits for 2.0.
Experimental and Laboratory may change in any release (`SUPPORT_TIERS.md`).
Before 1.0, minor versions could break compatibility. Every change that can
alter the behaviour of an existing app is listed under **Breaking**.

## Unreleased

### Added

- Laboratory: Bricks (`projects/bricks/bricks.q`), a brick breaker for one,
  or two to four over the network, written for the tags below: three levels
  written as lines of letters and built by a `q:loop`, steel bricks of two
  hits, bombs that break the bricks around them, the serve as jump is let go,
  a ball lost off the bottom, the last brick in slow motion and a sequence of
  tweens after it. Its art is drawn by `scripts/art/bricks.py` (CC0). On the
  games page, and replayed in CI (`tests/godot/test_godot_bricks.py`).
- Laboratory: what a contact ending does. `<qg:on-separate with=>` on a
  character or a prefab runs when it stops touching something of that tag (a
  plate stepped off, a door that closes behind); not when the other is
  destroyed, nor because the scene was paused.
- Laboratory: the screen's edges. `<qg:on-screen-exit side=>` and
  `<qg:on-screen-enter side=>` on a character or a prefab, or in a scene with
  `of=` a tag, run when it leaves the screen or comes onto it, by any edge or
  one (`top`, `bottom`, `left`, `right`). The screen is the camera's view,
  worked out in the game's ticks, or the scene without a camera; a thing
  placed off the screen has not left it. A `screen` event reaches the play
  protocol.
- Laboratory: `<qg:on-input action= on="release">` runs as the action is let
  go (`on="press"`, the default, as it goes down).
- Laboratory: `<qg:for-each tag= var=>` runs what it holds for every thing of
  a tag in the scene, `var=` naming each in turn; one destroyed meanwhile is
  skipped.
- Laboratory: slow motion. `<qg:time-scale scale= seconds=>` runs the whole
  game slower (or faster, up to 4) for `seconds=` as the player sees them, or
  until the next one; a new scene starts at 1. The ticks come further apart
  and each is the same tick as ever (the engine runs fewer ticks a second and
  slows its clock as much, as the lockstep's catching up already did, which
  now multiplies in), so a replay and every peer see the same game.
- Laboratory: `<qg:quit>` closes the game; in a browser it does nothing, and
  `can_quit()` says whether it would (a Quit button with `if="{can_quit()}"`).
  In a replay or a play session it is a `quit` event and the game goes on.
- Laboratory: a tween's end. `<qg:on-end>` inside a `qg:tween` runs when it is
  done (the last of its repeats), with `me` the thing it moved; a tween in it
  plays next, so tweens make sequences. `property="tint"` eases the colour a
  picture is multiplied by (`from="#ff4040" to="#ffffff"`), reported as
  `tint` in the state while it is not white.
- Laboratory: up to four players, or fewer. `<qg:multiplayer min-players=>`
  lets the host start before every seat is taken: `<qg:start-now>`, the
  lobby's **Start now** (and how many are there), or `--q-players=N` on the
  command line. Every peer learns how many play as the game starts, and
  `net_players()` says it.
- Laboratory: watching a networked game. `<qg:watch address=>`, the lobby's
  **Watch** button and `--q-watch=HOST:PORT` join with no seat: the players'
  inputs reach this machine too and it runs the same game, its keys doing
  nothing; one who comes after the start catches up on the game so far, as a
  rejoining player does. `net_status()` is then `watching`. Up to eight watch
  a game; not under `rollback=`.
- Laboratory: tweens and `qg:set-tile` under rollback. A scene's tweens are
  now records in one node per scene (`Tweens`), which the rollback saves and
  runs again with the rest, the looks they touched included; a tilemap saves
  the cells `qg:set-tile` changed. A rollback scene may hold a tilemap.
- Laboratory: in expressions, `a.x` and `a.y` read where a thing or a
  character is (`other.x - me.x`); before, `hero.x` compiled and stopped the
  game in Godot. `me.on_wall` and `me.on_ceiling` read what a body touched as
  it last moved, as `me.on_floor` does, for every controller.
- Laboratory: a prefab that does not move (an item, a solid block) has
  health, `qg:on-damage`, `qg:on-death` and `qg:state`s as one that moves
  does; before, `qg:damage` and `qg:become` did nothing to it.
- Laboratory: a thing's name where a target goes. `target=` of `qg:damage`,
  `qg:become` and `qg:deflect`, `at=` of `qg:burst`, `qg:shake` and
  `qg:spawn` take a parameter, a loop variable or a q:set holding a thing, and
  `qg:spawn at=` a character's id, as `qg:destroy` and `qg:tween` already did.
- Laboratory: to ship a game, Phase 4 of `PLAN_GAMES_3.md`, in every game of
  `projects/`. An options screen: `bus=` on `qg:sound` puts it on a bus
  (music, effects); `<qg:slider>` in a menu changes, with left and right, how
  loud a bus is (`bus=`) or a number of the state (`bind= min= max= step=`);
  `<qg:volume bus= value=>` and `volume('music')` set and read a bus;
  `<qg:fullscreen on=>` and `fullscreen()`; `<qg:rebind action=>` in a menu
  takes the next key, mouse button or joypad button pressed for the action
  (Escape keeps the old one). What the player chose there is kept between
  runs (`quantum-settings.json`, next to the saves), and the replay and the
  lockstep, which carry actions, are as before. Save slots: `slot=` on
  `qg:save` and `qg:continue`, `has_save(2)`; the scenes with `save="true"`
  save into the slot last used (Keep keeps three games). A HUD takes
  `<qg:icon sheet= frame= scale=>` (the item after it shares its line),
  `color=` on its texts and counters, `if=`, and the bottom corners. A menu
  takes `columns=` (left and right move along a row) and `rows=` (the rest
  scroll into view with the focus). `<qg:touch-button action=>` and
  `<qg:touch-stick>`, in the application or a scene, press the game's actions
  on a touch screen as keys would (`show="always"` everywhere); a lobby's
  `options=` adds an Options button. `scripts/export-games.py` builds a Mac
  app (`--preset macOS`, checked here), an `.apk` with the Android SDK
  (`--preset Android`) and an Xcode project (`--preset iOS`); the site still
  builds Web, Linux and Windows. Every game has options (on its title, or in
  the pause menu of Robot, Drift and the RPG) and touch controls. Tested in
  Godot (`tests/godot/test_godot_shipping.py`); the feature's dataset has
  seven games and six refusals more.
- Laboratory: hot reload, from Phase 6 of `PLAN_GAMES_3.md`. `quantum run
  game.q --watch` plays the game in Godot and records what is pressed; each
  save of the .q (or of a file beside it) builds it again, and the game
  comes back on the new build at the same tick, by playing the session's
  inputs again quickly. A build the compiler refuses is printed and the game
  plays on. Tested in Godot (`tests/godot/test_godot_hot_reload.py`).
- Laboratory: Marches (`projects/marches/marches.q`), a skirmish on a map of
  hexes, turn by turn: three riders hold a keep by a river against four
  raiders. Written for Phase 6 of `PLAN_GAMES_3.md`: `shape="hex"` (or
  `"iso"`) on `qg:tileset` with `tile="WxH"`, the rows of the .q the rows
  seen; a grid walker, a pointer and a cursor (`cells="true"`) on hexes;
  `cost=` on `qg:tile`, so the way found by `ai="pathfind"`, a pointer's
  click and the new `<qg:travel target= to= budget= step=>` is the cheapest;
  `cost(a, b)` in expressions. Its art is drawn by `scripts/art/marches.py`
  (CC0). On the games page, and played in CI
  (`tests/godot/test_godot_marches.py`, `tests/godot/test_godot_hexes.py`).
- Laboratory: lights and shadows, from Phase 6 of `PLAN_GAMES_3.md`, for
  Delve. `ambient=` on `qg:scene` makes it dark; `<qg:light radius= color=
  energy= flicker=>` lights it, at a place of the scene or carried by a
  character or a prefab; with `shadows="true"` the scene's solid tiles stop
  it, lit on their side and casting their shadow past it, and a wall opened
  lets it through. The flicker follows the ticks: a replay's frames are the
  same every time. Delve's vault is dark, lit by its torches, the delvers'
  lanterns and its treasure. Only seen. Tested in Godot
  (`tests/godot/test_godot_lights.py`, with rendered frames).
- Laboratory: the RPG in Russian, from Phase 6 of `PLAN_GAMES_3.md`. A
  count's word takes the forms its language has: `tr_n(one, other, n)`, and
  `one=`, `few=`, `many=` on a `qg:phrase` (1 зелье, 2 зелья, 5 зелий, 21
  зелье; Polish, Czech and Slovak counted as they count, 0 singular in
  French). `<qg:asset name= src=>` in a `qg:language` gives a sheet or a
  sound its file in that language: the RPG's "FIGHT!" banner is drawn in each
  of its four. `font=` on `qg:language` is a font with the letters of its
  alphabet the game's fonts lack: every font draws them from it (the RPG's
  Cyrillic, from Xolonium; its Latin letters stay Montserrat's). `slice=` on
  a `qg:spritesheet` makes its first frame a frame that stretches to a box,
  its edges as drawn: `box=` on `qg:dialogue` and `qg:menu` (the RPG's
  dialogues and fight menu, `scripts/art/rpg_extra.py`, CC0). The RPG's HUD
  counts "2 potions" instead of "Potions 2". Tested in Godot
  (`tests/godot/test_godot_localized.py`, with rendered frames).
- Laboratory: positional sound, from Phase 6 of `PLAN_GAMES_3.md`, for
  Hopper. `at=` on `qg:play` plays a sound from where a thing is: softer and
  to one side the farther it is from the middle of the screen, silent two
  screens away. A thing's own sounds (its `fire-sound=`, a leap's or a
  shot's `sound=`) now come from where it is. Hopper's bouncer hops with a
  sound, heard from its side before it is seen. The `sound` event says where
  a sound came from.
- Laboratory: music and sounds within a scene, from Phase 6 of
  `PLAN_GAMES_3.md`, for Delve. `qg:music` in a handler changes the music
  there and then, crossfading over `fade=`; Delve's vault has a warden, the
  skeleton archer, whose fight has a theme of its own from when it first sees
  a delver until it falls. `sounds="a, b, c"` on `qg:play` plays one of
  several each time (Delve's skeletons fall apart in one of three ways); the
  state records the list as written. The music and the bones are synthesized
  by `scripts/art/delve_music.py` (CC0).
- Laboratory: the mouse's other buttons and hover, from Phase 6 of
  `PLAN_GAMES_3.md`, for Towers. `<qg:on-select action=>` chooses with
  another of the player's actions (a `qg:input` of `MouseRight` is a right
  click on a thing); `WheelUp` and `WheelDown` in `keys=` turn the wheel into
  an action; `hovered()` is the thing under a player's cursor. Towers sells a
  tower with a right click, changes the tower to build with the wheel, and
  says what the tower under the mouse sells for. Characters blocking each
  other, the first item of the phase, needed nothing: they already stop at
  each other and stand on each other's heads, now in a test
  (`tests/godot/test_godot_bodies.py`), and Rally's cars bump.
- Laboratory: multiplayer and the play protocol, Phase 5 of
  `PLAN_GAMES_3.md`. Choosing the seat: `--q-seat=N` on joining (taken, the
  joiner is turned away, and the game goes on), `seat=` on the play
  protocol's `play_start` with `join=` and `quantum play --seat`; the replay
  harness's peers ask for their seats, so they join all at once. `player=N` on
  `play_act` and `play_until` presses player N's keys by player 1's names in a
  game for several on one machine; `text=` types into the text box chosen
  (`"\n"` is Enter), and a tape keeps what was typed (`["type", text]`, for the
  replay too). Shared fields: `<qg:field shared="true">` is a draft until Enter
  sends it with the player's input, like a key, and on that tick every machine
  sets the bound state and runs what the field holds, with `sender` and `text`
  (`sent` and `message` events); the menu waits for it on every machine.
  `<qg:menu local="true">` is the menu of whoever plays at this machine, of
  shared fields only. While a field is typed in, the keys type and play
  nothing. Split screen: `player=` on `qg:camera` gives each player a view; on
  one machine the screen splits (side by side, or in quarters for three or
  four), over the network each machine shows its own player's, and the screen
  of `qg:on-screen-exit` is every player's view. Special moves:
  `<qg:on-input sequence="down, forward, punch" within= player=>` holds when
  the presses come in order within so many ticks, `forward` and `back` the way
  the player's character faces; the presses are kept with the input, so the
  rollback replays them. `<qg:rumble player= strength= seconds=>` shakes a
  joypad (a phone, in the hand), felt only on that player's machine. A fighter
  takes `qg:damage` as a hit, blocked by holding away. Bricks over the network
  starts with who is who (each player's name, sent from their own machine);
  Arena has the blast (down, forward, punch), felt on the joypad of the one it
  hits. Tested in Godot (`tests/godot/test_godot_shared.py`,
  `test_godot_split.py`, the Arena's and the play protocol's tests, an agent in
  each seat of a four-machine Bricks); the feature's dataset has seven games
  and six refusals more.
- Laboratory: Rally (`projects/rally/rally.q`), two cars round a circuit seen
  from above, wider and taller than the screen, written for the split screen:
  on one keyboard the screen splits in two, a view for each car; over the
  network each machine follows its own. The circuit is a Tiled map, the laps
  are counted at the line after halfway round (its zones), and a barrier lifts
  at the green light. Its art and circuit are drawn by `scripts/art/rally.py`
  (CC0). On the games page, and raced in CI, alone and over the network
  (`tests/godot/test_godot_rally.py`).
- Laboratory: Crates (`projects/crates/crates.q`), a box-pushing puzzle on a
  dockside, written for Phase 3 of `PLAN_GAMES_3.md`: three rooms drawn in
  Tiled (`projects/crates/rooms/`: two tilesets, flipped walls, animated
  water, the doors, a sign by each, a gull's way over the harbour and each
  room's title and hint), a worker who steps or walks where it is clicked and
  pushes crates and barrels onto the pads, a foreman who talks and offers a
  choice, a gate the camera goes to show open, and a key carried over the
  worker's head to a locked gate. Its art is drawn by `scripts/art/crates.py`
  (CC0). On the games page, and played through in CI with a solver's moves
  (`tests/godot/test_godot_crates.py`).
- Laboratory: puzzle and adventure, Phase 3 of `PLAN_GAMES_3.md`.
  `pushable="true"` on a solid prefab: a grid walker's step pushes it a cell
  on when the cell beyond is free (a `push` event), and runs the walker's
  `qg:on-collision` with it. `controller="pointer"`: a grid walker that its
  player's click also walks, by the shortest way round the walls and things
  (a `route` event); a click on a thing walks up to it and steps into it, a
  crate only when it is beside the walker (further off, the walk ends beside
  it); the click and the cursor travel in the lockstep. `extends=` on
  `qg:prefab` makes one prefab from another: all of it (attributes,
  animations, states, handlers, behavior) but what it says itself. `<qg:attach
  target= to= dx= dy=>` makes a thing carried by another, following it and
  touching nothing; `<qg:detach target=>` (or `from= tag=`) puts it down;
  `carrying(me, 'key')` finds it. `<qg:camera-to target= | x= y= zoom=
  seconds= hold= pause=>` sends the camera to a thing or a point and back to
  what it follows, the scene waiting meanwhile unless `pause="false"`.
  `<qg:choice label= if=>` in a `qg:line` offers answers (up, down, select);
  `speed=` on `qg:dialogue` types each line in, `sheet=` and a line's
  `portrait=` put a face beside it. `frames=` and `fps=` on `qg:tile` animate
  a tile. A Tiled map may use several tilesets (each the game's `qg:tileset`
  with the same image), flipped and turned tiles, objects of class `zone`,
  `exit` and `path`, an object's `state` property, and properties of its own
  that `tiled('name')` reads. `tile_at(col, row, 'layer')` reads a layer by
  name, and `a.col`, `a.row` the cell of any thing or character. Keep's end
  asks what now (a dialogue with choices), Delve's lever sends the camera to
  the wall it opened, and Siege's brute is made from its raider. Tested in
  Godot (`tests/godot/test_godot_puzzle.py`, over the network too); the
  feature's dataset has seven games and seven refusals more.
- Laboratory: Siege (`projects/siege/siege.q`), a keep under siege seen from
  above, for one, or two over the network, written for Phase 2 of
  `PLAN_GAMES_3.md`: raiders in waves from the edges make for the tower, the
  archer aims at the pointer (or with the right stick) and charges a bolt
  that glances off the walls, a tower zaps the nearest, and the second player
  is a knight who steers a horse. Its art is drawn by `scripts/art/siege.py`
  (CC0). On the games page, and replayed in CI
  (`tests/godot/test_godot_siege.py`).
- Laboratory: action and aiming, Phase 2 of `PLAN_GAMES_3.md`. `heading=`
  on `qg:spawn` sends a flying prefab where two expressions say (at the
  pointer: a `qg:cursor id="aim"` is read as `aim.x`, `aim.y`). `<qg:steer
  turn= thrust= drag= max=>`, a part of `qg:behavior`: left and right turn
  the body, up pushes it the way it points. `<qg:label value=>` is text in
  the world, over a character or a prefab or at a place of a scene, read
  every tick (and in the play protocol's screen); `qg:emit text=` floats a
  number (or a word, in the player's language) up. `<qg:beam from= to= seconds=>` draws a line between two things;
  `trail=` on a prefab leaves a streak; `particles=` on a prefab or a
  character keeps an effect going on it. `qg:tween` eases `scale-x` and
  `scale-y` (a scale is now from the thing's own size), and a prefab or a
  character takes `visible="{...}"` (read every tick), `flip-v=` and
  `layer=`; a scene takes `y-sort="true"`. A flying prefab's `walls="bounce"`
  turns off the tiles; `side="left"` and `side="right"` join top and bottom
  on `qg:on-collision`, for prefabs too; `buffer-frames=` (the platformer)
  and `buffer=` (`qg:jump`) jump on landing for a press just before it
  (Hopper has it); `spacing=` keeps things of a tag apart as they move.
  `qg:damage amount=` takes an expression. Tested in Godot
  (`tests/godot/test_godot_action.py`); the feature's dataset has six games
  and five refusals more. `GAMES_PARITY.md` counts 166 rows covered.
- Laboratory: game logic, Phase 1 of `PLAN_GAMES_3.md` (the plan approved
  on 2026-10-21 for the language's next 34 features, and ten more as a game
  asks for them). `<qg:after ticks= | seconds= name=>` in a handler runs what
  it holds later, with the names of its handler as they were (`me`, a loop's
  thing, a parameter; a thing gone by then is null); one of the same name
  still waiting starts its count again. `<qg:when condition=>` in a scene runs
  its handler as the condition turns true, read at the start of every tick,
  and again only after it has been false. Both live in the scene's clock (one
  `Clock` node a scene), which counts `ticks()`, stops while the scene is
  paused, and rolls back. A `q:function` directly in `q:application` is every
  scene's and the prefabs': it reads the game's state, its parameters and its
  own variables; Delve's and Keep's `hurt`, once in every room, is one now,
  and Bricks' last brick is a `qg:when`. In expressions, `pressing('run')`,
  `pressed_for('fire')` (ticks; on the tick it is let go, how long it was)
  and `strength('right')`, for player 1 or another (`pressing('run', 2)`);
  `sin()`, `cos()` and `atan2(y, x)` in degrees, as a picture's rotation; and
  the Core's `sort(list)`, `sort(list, true)`. A field a thing does not have
  (`hero.health` on a platformer) is a compile error that lists the fields it
  has, by its controller; a `q:set` may still hold a dictionary (`bag.a`).
  Tested in Godot (`tests/godot/test_godot_logic.py`, and under rollback in
  `tests/godot/test_godot_rollback_tweens.py`); the feature's dataset has six
  games and five refusals more. `GAMES_PARITY.md` counts 154 rows covered.
- The games page (`/games/`) shows each game's source: **View the source**
  opens `/games/<name>/source/`, the whole `.q` (and a level drawn in Tiled,
  in a tab of its own) highlighted, every line numbered and a link
  (`source/#L42`). Each `qg:` tag links to its entry in the language's
  reference, a tag or an attribute shows what it does when pointed at (the
  schema's own words), and each file can be copied, downloaded or opened on
  GitHub. `scripts/export-games.py` writes the pages with the games; the
  Source column of the Play page links them.
- `<ui:tabpanel open="Title">` opens on the tab with that title, in the
  browser, the console and on the Hive's screen (UI-17); `open="{tab}"` with
  `<q:set name="tab" value="{query.tab}" default="...">` lets a page that
  comes back after an action open where the user was. A literal that names no
  tab is a parse error that lists the tabs. The Settings app of Quantum OS
  comes back on the tab a request was made from.
- Laboratory: the game language is a feature of its own,
  `quantum/core/features/game_engine/`, like the others: a manifest, three
  intentions (`primary`, with a line for every `qg:` tag, statement and
  expression function; `variants`; `edge_cases`) and a dataset of 39 whole
  games and 24 refusals with their messages. Each game compiles and each
  refusal says what it says (`tests/dataset/test_dataset_features.py`), and
  a tag added to the schema without its line in the primary intention and a
  game that uses it fails `tests/dataset/test_game_engine_feature.py`.
- Laboratory: the new tags in the games. In Delve, hearts and gems are
  items: the inventory is in the HUD, a hit takes a heart, and a new game
  starts with `qg:reset-items`. A skeleton archer, made of parts, keeps its
  distance and shoots arrows; the bats are made of parts too and flutter
  until they see a delver. Hopper has a fourth level, the falls, with water
  to swim in, snow to slide on, a ladder, spike tiles and a hopping enemy
  made of parts.
- Editors: the game tags (`qg:`). The language server and the VS Code
  extension read them from the game compiler's own schema
  (`quantum/runtime/godot/schema.py`): completion, hover, required
  attributes and the values an attribute takes, for every `qg:` tag the
  compiler accepts, and highlighting for all of them. VS Code no longer
  warns "Unknown tag" on every tag of a game, nor on its `gd:` attributes.
  A conformance test checks that every game in `projects/` is clean in the
  editor.
- Laboratory: enemies of parts that walk on floors. `<qg:gravity>` in a
  prefab's `qg:behavior` (as in a character's) makes it fall and stand:
  its parts then move it left and right only, a seek goes straight at its
  target, and the prefab's `turns-at="edge"` keeps it on its ledge (a
  patrol turns, the other parts wait). `<qg:leap height= every= at-wall=
  when= sound=>` jumps from the floor on bumping a wall as it walks (a step
  to climb) or while `when=` holds. `me.on_floor` reads whether it stands.
- Laboratory: enemies made of parts. A `<qg:prefab ai="behavior">` lists
  its parts in a `<qg:behavior>`: `qg:seek` (around the walls, or
  `way="straight"`), `qg:flee`, `qg:keep-distance min= max=`, `qg:patrol`
  (to and fro, turning at walls or after `distance=`), `qg:wander` and
  `qg:stand`. The first one in order whose `when=` holds and that has
  something to do moves it; `qg:shoot` parts fire besides. A part notices
  only what it sees (no solid tile between) unless `through-walls="true"`,
  and looks for a character by id or a thing by tag. `me.doing` reads the
  part that moved it. Expressions gain `distance(a, b)`, `nearest(a, who)`
  and `sees(a, b)`.
- Laboratory: what the players carry. `<qg:item name= label= sheet= frame=
  max= start= sound= particles=>` declares a kind of item; how many are
  held is the game's state (kept across scenes, saved with `qg:save`, in
  every replay and peer's hash). A prefab with `gives="key"` (and
  `amount=`) is picked up by a character's touch, unless they hold the
  most; a solid one with `opens-with="key"` opens for one, spending it
  unless `keeps="true"`, and runs its `<qg:on-locked>` without one. A named
  instance picked up or opened stays gone when its scene is entered again,
  with no `taken` list and `if=` to write. `<qg:give item= amount=>` and
  `<qg:take item= amount=>` add and spend them, `<qg:reset-items>` starts a
  new game (each item back to its `start=`, the gone things back), `held('key')` reads them,
  `<qg:counter item=>` counts one in the HUD and `<qg:inventory>` shows
  what is held, each its picture and how many. `pickup`, `open`, `locked`
  and `item` events reach the play protocol.
- Laboratory: tile kinds. `<qg:tile kind=>` makes a tile a `ladder`
  (passed through; up and down climb it, jump lets go), `water` (passed
  through; slow to sink in, a jump is a stroke, slower to walk), `ice`
  (slid on, in a platformer and on a top-down floor) or `hurt`. In a Tiled
  map, a tileset tile's class or `kind` property does the same, in the
  map's own tileset or an external `.tsx`. The platformer, top-down and
  behavior controllers feel them. `<qg:on-tile kind= cooldown=>` on a
  character runs as it comes to touch a tile of that kind (stands on it, is
  in it or bumps it), and again each cooldown while it still does; a
  `tile-touch` event reaches the play protocol.
- Laboratory: `<qg:play sound= volume= pitch= vary=>`: decibels added, a
  pitch (2: an octave up), and a random spread of pitch each time, so twenty
  hits do not sound the same. Such a play is a voice of its own, so the
  sound can overlap itself. Only heard: the state records the sound's name,
  and the random pitch comes from a generator of its own.
- Laboratory: Delve has music of its own, written and synthesized by
  `scripts/art/delve_music.py` (CC0, with `scripts/art/rpg_music.py`'s
  voices): `torchlight` for the title and the end, `crypt`, darker and
  slower, for the three crypts. Its hits vary in pitch, its gems ring a
  little higher, and the wall a lever opens sounds deeper.
- Laboratory: `qg:camera` has `zoom=`, `dead-zone="WxH"` (the box the
  followed one moves in before the camera does), `lead=` (pixels it looks
  ahead, the way the followed one goes), `smooth=`, and follows several
  characters (`follow="p1, p2"`: their middle), with `fit="true"` zooming
  out to keep them all on the screen (down to `zoom-min=`). It runs in the
  game's ticks and is only seen; the play protocol reports it as a screen
  view (`kind: camera`, where it looks and how close). Hopper's camera
  looks ahead and lets a jump rise before it follows.
- Laboratory: animations with an end. `<qg:animation loop="false">` plays
  once and stays on its last frame; `<qg:on-animation-end name=>` on a
  character or a prefab runs as it ends (`me` is whose it is), and an
  `animation-end` event says so; `<qg:play-animation target= name=>` plays
  one from its first frame, the body's own animations (idle, walk...)
  waiting until it ends (`name=""` gives them back after a looping one).
  In Delve a slain skeleton falls to a heap of bones before it goes.
- Laboratory: Delve (`projects/delve/delve.q`), a dungeon crawl that shows
  the new tags together: three crypts, a wall a lever opens
  (`qg:set-tile`) and the skeletons behind it that find their way through
  it (`ai="pathfind"`), crushers that slide to and fro (`qg:tween`), a
  vault two levers keep shut, torches and gems (`qg:particles`), each crypt
  entered saved (Continue on the title), English, Portuguese and Spanish,
  and a second delver over the network. Its art is drawn by
  `scripts/art/delve.py` (CC0). A scripted run down to the vault is a
  playtest tape (`tests/godot/playtests/delve.json`).
- Laboratory: `if=` on `qg:character`, as on `qg:instance`: placed only when
  it is true as the scene is built. Delve's second delver is there only in a
  networked game: `if="{net_status() != 'offline'}"`.
- Laboratory: `controller="behavior"`, a character made of parts: its
  `<qg:behavior>` lists them, and the body is what they add up to.
  `qg:gravity` (strength=, max-fall=), `qg:walk` (speed=, accel=,
  axis="x|both"), `qg:jump` (action=, height= or speed=, coyote=, air=,
  variable=, cut=, sound=), `qg:keep-inside`, `qg:wrap` and `qg:face`
  (by="velocity|input"). Gravity, walk and jump with the platformer's
  numbers make the platformer, to the pixel; walk on both axes is a
  top-down walker; walk and wrap, a ship that comes back round the screen.
  `<qg:velocity target="me" x="..." y="...">` sets its speed from the game's
  rules (a dash, a knock-back, a spring), and `me.vx`, `me.vy`, `me.on_floor`
  read it.
- Laboratory: `<qg:set-tile col= row= tile= layer=>` puts a tile in a cell
  of the scene's tilemap, or empties it (`tile="0"`): a block that breaks,
  a door drawn as tiles. Its collision changes from the next tick (the
  same on every peer, however many ticks a frame runs; a collision handler
  may set one too), monsters that pathfind
  find their way again, and the cells changed are in the game's state
  (`tiles`), so a replay and the lockstep's check see them. `tile_at(col,
  row)` reads a cell. Not under `rollback=` yet.
- Laboratory: a networked game says on the screen when it cannot go on as
  usual: waiting for the other player to come back, catching up, the
  other player left, or the games differ. The notice is over the scene, in
  the player's language (pt and es come with it), in the play protocol's
  screen (`kind: notice`) and in a web page's `window.quantumNotice`. In
  CI the waiting page of the relay check is asked for it.
- Laboratory: `<qg:particles name="sparkle" preset="stars" color="#ffe060">`,
  a particle effect from a preset (puff, sparks, smoke, dust, fire, rain,
  snow, confetti, stars) and a few overrides (color, amount, lifetime,
  speed, size), never the 68 knobs of `CPUParticles2D`. `<qg:emit
  particles= at= dx= dy=>` plays one once where a thing is;
  `<qg:emitter particles= x= y= width=>` keeps one going in a scene (rain
  across its width, a fire on a spot). Only seen: a test plays a game with
  and without its effects and gets the same state. Hopper's coins sparkle,
  a stomped walker goes in a puff; Keep's key and heart twinkle, a slain
  monster smokes and the chest bursts into confetti.
- Laboratory: `ai="pathfind"` on a prefab: as `chase`, it goes for the
  character within `sight=`, but around the walls, by the shortest way over
  the tilemap's free cells (breadth first, its neighbours always in the
  same order, so every replay and every peer finds the same way). The way
  is found again when the quarry changes cell; walled off, it waits.
- Laboratory: `<qg:tween target="coin" property="y" to="100" seconds="1"
  trans="back" ease="out" repeat="-1" yoyo="true">`, a property of a thing
  eased to a value: its position (`x`, `y`, which collisions see), or its
  picture's `rotation`, `scale` and `alpha`. It runs in the game's ticks,
  so a replay and every peer of a networked game see the same; it stops
  while the scene is paused, and a new tween of the same property replaces
  the old one. Not under `rollback=` yet. Keep's key and heart breathe and
  its chest wobbles.
- Laboratory: the relay, ready to deploy. `deploy/relay/Dockerfile` builds an
  image with Godot and the networked games compiled in, and
  `deploy/relay/fly.toml` runs it on Fly.io. `quantum relay` adds
  `--builds` (keep the compiled games between runs) and `--prebuild` /
  `--prebuild-only`. A plain HTTP request is a health check that answers
  in JSON. With a relay address (`QUANTUM_RELAY_URL`, or `relay` in
  `projects/games.json`), the games page gives each networked game a
  **Play online** button that makes a room and a link to send to a friend.
  CI builds the image and checks its health.
- Laboratory: `<qg:music sound="theme" fade="1" volume="-4">`, a scene's
  music. Going to a scene with other music crossfades from one to the
  other, a scene with the same music lets it play on, and a scene with none
  fades it out. Only what is heard changes, so replays are as before. The
  play protocol says what is heard (`music` in an observation, a `music`
  event). The RPG has music of its own, written and synthesized by
  `scripts/art/rpg_music.py` (CC0): a calm loop on the map, a driving one
  in the fight.
- Laboratory: `quantum relay`, where two browsers meet to play a
  networked game. A web page cannot host, so each room
  (`wss://relay.example/pong/ROOM`) runs the game in a headless Godot that
  hosts without a seat (`--q-relay=PORT`) and passes the players' inputs
  on. The relay carries WebSocket messages unchanged, and is `wss://` with
  `--cert` and `--key`. A `qg:join` address (and `--q-join=`) may now be a
  URL. `url_param("join", default)` reads a web page's `?join=`, and
  `qg:lobby`'s address field starts with it, so a link carries the room.
  A web page reports `window.quantumNet`. In CI, two Chromium pages play
  Pong through a relay (`scripts/check-relay-in-browser.py`).
- Laboratory: the play protocol's browser bridge. A web build publishes
  `window.quantumPlay` (`observe`, `press`, `release`, `trace`), and
  `WebPlaySession` (`quantum/runtime/web_play.py`) plays the exported game
  from Playwright in real time. It offers `observe`, `act`, and `until`
  with the same conditions as `PlaySession`, read in Python since the game
  does not wait. In CI an agent wins the RPG's web build through it
  (`scripts/check-play-in-browser.py`).
- Laboratory: a game in several languages. `<qg:language lang="pt">` holds
  `qg:phrase`s (`text="Attack" as="Atacar"`), and `tr(text)` translates a
  text an expression puts together. Labels, buttons and the dialogue show
  the player's language through Godot's own translation. The language is
  the web page's `?lang=`, `--q-lang=`, or the system's when the game has
  it, and the game's own texts otherwise. The play protocol's observations
  say what the screen shows in the language it shows it in, with `lang`;
  a session picks one (`lang=`, `quantum play --lang`, `play_start`), and
  the game's own texts are the default. The RPG is in Portuguese and
  Spanish too.
- Laboratory: `<qg:next-language>` shows the game in its next language,
  after its own, and the choice is kept for the next run; `language()` is
  the name of the one shown. A `qg:lobby` of a game in several languages
  has a button for it, and Hopper's and Keep's titles too
  (`label="{tr('Language') + ': ' + language()}"`).
- Laboratory: a player who leaves a networked game can come back. The
  host (or `quantum relay`) keeps every input of the game; the others wait
  (`net_status()` is `waiting`), and the next to join, from the same
  address or room link, takes the free seat: they get the inputs so far and
  run the game from its start 16 times faster (`catching up`), checking
  the state the players agreed on, then play on. Running faster keeps
  every tick the same: the engine runs more ticks a second and slows its
  clock as much. Not under `rollback=`, where the game still ends. In CI a
  third Chromium page takes a free seat in Pong through the relay.
- Laboratory: `<qg:scene save="true">`: entering the scene saves the game,
  to continue there, as the rooms of an adventure do. Keep opens on a
  title (New game, Continue), and each room entered saves it. In CI, the
  save survives a page reload in Chromium (`scripts/check-save-in-browser.py`).
- Laboratory: `<qg:save scene="map">` and `<qg:continue>`: a game saved
  to continue later. A save is the game state (every `q:set` of
  `q:application`) and the scene to come back to, which starts over; one
  per game, kept between runs (in a browser, by the browser). `has_save()`
  says whether there is one, for a Continue button. A networked game is
  not saved. Hopper opens on a title now (New game, Continue), and each
  level cleared saves it.
- Laboratory: every game is in Portuguese and Spanish too: Pong, Chess,
  Arena, Towers, Hopper, Keep, Drift, Creeps and Robot. A `qg:lobby`
  brings its own phrases in both (its buttons and its status line), and a
  game's `qg:phrase` wins over them. Only what is shown is translated: the
  game's state stays as written, so networked players in different
  languages still play the same game.
- Laboratory: the play protocol, phase 7: `quantum playtest`. An agent tries
  to finish each game toward the `goal` it has in `projects/games.json`
  (what it is told, a condition the job checks after every call, and a
  budget of calls). The report says reached, not reached, stuck (ten calls
  that changed nothing) or error, with each session's tape. A reached
  goal's tape, kept in `tests/godot/playtests/`, is replayed as a test.
  The agent that plays is Claude (`claude-opus-5-5` by default, through the
  Claude API; the `play` extra now brings `anthropic`). The `Playtest`
  workflow runs it only when started by hand, and says so and stops when
  there is no `ANTHROPIC_API_KEY` secret. Goals for now: the RPG, Keep,
  Drift and Hopper.
- Laboratory: the play protocol, phase 6: live, and playing with people.
  `PlaySession(live=True)` (`quantum play --live`, `play_start(live=...)`)
  runs the game at its own speed, 60 ticks a second, and serves requests
  without stopping it; the reflexes play between them. `host=PORT` and
  `join="host:port"` take a seat in a `qg:multiplayer` game, which is
  always live, and each observation says the seat and the lockstep's state
  under `net`. A live game has no tape and cannot be restored. In the
  tests, an agent takes the second seat of a person's Pong and never lets
  the ball past. In CI, an agent hosts Pong and the web build joins it from
  Chromium (`scripts/check-agent-in-browser.py`).
- Laboratory: the play protocol, phase 5: reflexes. `act` and `until` may
  carry `reflex` rules, `[{"when": a condition, "hold": [actions]}]`, which
  the driver checks before every tick until they are replaced (`[]` clears
  them). The actions of the rules that hold are held for that tick and let
  go when no rule wants them. What they press goes into the tape, so a
  session played with reflexes replays the same, and a snapshot brings them
  back. A comparison's right side may now be another path with a number
  added (`"ball.y < left.y - 8"`), and a path reaches a scene's named things
  (`ball`). The console has `reflex up if ..., down if ...`, `reflex off`
  and `wait 60`; the MCP tools `play_act` and `play_until` take `reflex`. In
  the tests, an agent works out where Pong's ball will arrive and leaves
  the paddles to the reflexes (20 returns in a row), and clears Drift's
  first wave without losing a life.
- Laboratory: the play protocol's answers are quieter. A number that
  changes tick after tick (the RPG's `wait`, `hurt`) is told as one `set`,
  from its first value to its last, with `times` and `until`, instead of a
  line a tick. A text (whose turn it is) is still told at each change, and
  any other event between keeps the changes apart.
- Laboratory: `<qg:sprite frame="{1 if hurt > 0 else 0}">`: a picture whose
  frame follows an expression, tick by tick (a number stays a fixed frame).
  In the RPG, a fighter just hit makes a surprised face for half a second,
  with the faces already in `fighters.png`.
- Laboratory: `<qg:goto-scene fade="0.4">`: the new scene comes out of black
  over that many seconds. Only the picture fades. The tween counts physics
  ticks, so a frame at a given tick always shows the same shade, and the
  game runs exactly as it would without the fade. Under rollback the fade
  waits for the scene change, as the change does. The play protocol sees the
  fade as a `screen` view (`{"kind": "fade", "dark": 0.5}`). The RPG fades
  into and out of its fights.
- Laboratory: the play protocol, phase 4: the console and the MCP server.
  - `quantum play rpg` plays a game a request at a time in the terminal.
    Typed words are the requests: `right 32`, `tap select`,
    `until talking with right`, `view`, `snap`, `back`, `tape won.json`.
    The answers are printed short: where, what happened, what the screen
    says.
  - `quantum play --mcp` serves the same as MCP tools: `play_games`,
    `play_start`, `play_act`, `play_until`, `play_view`, `play_snapshot`,
    `play_restore`, `play_tape` and more. With `.mcp.json` at the
    repository's root, a Claude Code session opened on it can play the
    games directly. The server needs the `play` extra
    (`pip install quantum[play]`, the `mcp` package).
  - An event repeated in a row (a walker bumping a wall) is told once, with
    `times`.
  - In the tests, an MCP client wins the RPG through the tools alone.

- Laboratory: the play protocol, phase 3: branching, and every session is a
  tape. The driver records every input it applies, with its tick, in the
  replay's format. `snapshot()` marks a point of the game. `restore()` comes
  back to it in a fresh game replayed to that tick, with the saved state
  the session began with and the actions it held still held. `tape()` and
  `save_tape()` give the session as a replay tape: a game played by
  looking is a regression test as it is. In the tests, a fight branches
  from a snapshot (Attack, then Defend, then Attack again, the same to the
  tick), and a won fight saved as a tape replays to the same state.

- Laboratory: the play protocol, phase 2: perception. An answer to an act
  or an until now carries the events of its ticks: what the runtime reports
  through `Q.event()` (a touch, a hit, a step or a bump, a thing spawned or
  destroyed, damage, a death, a sound, a scene, a line said, a button
  chosen, a pause) and every variable of the scene or the game that changed
  (`set`, from, to). `Q.event()` records nothing outside a play session.
  `until` stops on an event (`"event:say"`, `"event:touch with=key"`). The
  first answer in a scene carries its `map`: the tilemap as rows of `#`
  (stops), `-` (one-way) and `.` (open). `view()` draws the screen as
  text, with a legend of the characters and things on it, and `frame()`
  saves the real picture in a session opened with `frames=True`. In the
  tests, an agent leaves Keep's first room by the map and the view alone.

- Laboratory: the play protocol, phase 1 (`PLAN_PLAY_PROTOCOL.md`): a game
  an agent plays step by step. `PlaySession` (`quantum/runtime/godot_play.py`)
  runs a built game headless through a driver (`godot_play.gd`) that waits
  for each request and runs exactly the ticks it asks for. `act` presses,
  holds or taps the game's own actions and points its cursor; `until` runs
  until a condition holds ("talking", "player.row == 7", "changed scene").
  Each answer is what a player would know by looking: the scene, its state,
  and what the screen shows to read and choose (the HUD's texts, the menus'
  buttons and focus, the dialogue's line), which the HUD, menus and dialogue
  now report through `quantum_view()`. The same requests give the same game
  as a replay. In the tests, an agent wins the RPG in 16 requests, deciding
  each from the last answer, and plays Chess with the cursor.

- Laboratory: the RPG has an inventory, beyond the demo it transcribes. The
  key is taken and stays taken; two potions lie on the map; a HUD shows what
  the player carries, and a Potion button in the fight gives back 5 life, up
  to 10. All of it is written with the language as it was (game state,
  `qg:instance if=`, `qg:destroy`, `qg:button if=`).

- Laboratory: `qg:parallax`, a backdrop that the camera scrolls slower than
  the level (`scroll=`, from 0, still, to 1, with the level), repeating
  across. Robot has the demo's sky again: its clouds and distant platforms,
  composed by `scripts/art/robot_sky.py`.

- Laboratory: a tenth game, `projects/rpg/rpg.q`: Godot's "JRPG" demo
  (`2d/role_playing_game`), transcribed with its own art and font. A slime
  walks the demo's map cell by cell, reads a key, talks to another slime and
  fights it turn by turn (Attack, Defend, Flee). The language grew three
  things for it:
  - `controller="grid"`: a character that steps from cell to cell of the
    tilemap in `step-frames=` ticks. Walls bump it, and stepping into a thing
    runs its `qg:on-collision`; `me.col` and `me.row` are its cell.
  - `qg:dialogue` with `qg:line who= text=` and `qg:on-end`, opened by
    `qg:say`. The scene pauses until the last line; `talking()` says when.
  - Several `qg:tilemap`s in a scene are layers of one map.

  A HUD at `top-right` now ends at the right edge of the screen; it began 84
  px from it, and a wide bar was cut off (Arena's).

- Laboratory: CI plays the games in a browser. A new job, `games-in-browser`,
  exports every game for the web and opens each one in a headless Chromium
  (`scripts/check-games-in-browser.py`). The game must start on its first
  scene, print no error to the console (a picture, sound or font it cannot
  load, a script error) and react to its keys. What it expects of each game
  is the `check` of `projects/games.json`. In a browser the runtime reports
  the scene being played in `window.quantumScene`, and every action pressed so
  far in `window.quantumActions`. A screenshot of each game is kept with the
  run. This is the check that would have caught the games that lost their
  pictures, and the quick clicks that were lost, on the site.

- Laboratory: https://quantumframework.net/games/ is a page of its own: every
  game with a screenshot, what it is, its keys, and its links (play in the
  browser, the Linux and Windows downloads, the `.q`). `scripts/export-games.py`
  writes it after the builds, from `projects/games.json` and each game's
  `projects/<name>/screenshot.png`.

- Laboratory: the games are drawn. Drift has a ship, drones, tanks, a crab
  boss that turns red when angry and a starfield; Keep a stone dungeon seen
  from above, a hero who walks and swings a visible sword in four
  directions, a slime and a bat; Arena two martial artists in fourteen poses
  and a dojo yard at dusk; Chess the picked square, a dot on every square the
  picked piece may go to (a ring round a piece it may take), the last move,
  the king in check and a cursor for the keyboard. The art is drawn by
  scripts in `scripts/art/` (CC0). The top-down controller plays "attack"
  ("attack-up", "attack-down") while it swings; `qg:spawn` takes `x=` and
  `y=`, a point of the scene.

- Laboratory: a ninth game, `projects/robot/robot.q` — Godot's "Platformer 2D"
  demo (godot-demo-projects, `2d/platformer`, MIT) transcribed: its level,
  the robot that runs, jumps twice and shoots, the crawling enemies, the
  coins, the lifts, the tilted ledge and the pause menu, with the demo's art
  and sounds (`projects/robot/README.md` maps it, piece by piece). What it
  asked of the language: `qg:tile` gives a tileset's tile a shape of its own
  (a lower top, a thin ledge, a one-way slope) or none, and a negative number
  in a tilemap is the tile flipped; the platformer controller takes
  `accel=`, `jump-speed=`, `air-jumps=`, `air-jump-boost=`, `jump-cut=`,
  `fire-action=`/`fire-prefab=` (a shot the way it faces) and a "fall"
  animation; a solid prefab takes `shape=` (a polygon, concave or not); a
  flying one `walls="stop"`; prefabs and characters `scale=` (the picture
  only); a coin-like prefab plays its animation; `qg:pause`, `qg:resume`,
  `paused()` and `qg:menu if=` make a pause menu.

- Laboratory: rollback. `<qg:multiplayer rollback="8" />` runs each tick at
  once with the other players' input guessed, keeps a snapshot before every
  tick, and when a guess was wrong goes back and runs the ticks since again
  inside one frame — no waiting on the network, the same end state as the
  lockstep. The compiler allows it when every scene the networked game
  reaches holds only nodes that save and load their whole state and never
  go through Godot's physics (fighters, timers, menus, the HUD, pictures, a
  camera); a scene change waits until the tick that asked is certain.
  Arena plays with it. `replay_peers(latency_ms=..., net_report=True)`
  injects latency and reports each peer's rollbacks.

- Laboratory: the lobby in the language. `qg:host port=`, `qg:join
  address=` and `qg:leave` start and stop the networked game from a scene;
  `net_status()`, `net_players()` and `net_player()` say where things are;
  `qg:multiplayer start=` names the scene the networked game begins in on
  every peer (the title and the lobby before it run on each machine
  alone), and `transport="websocket"` lets a desktop host take players over
  WebSocket. `qg:lobby` is the usual menu — play here, host, an address
  field, join, cancel, a status line — written by the compiler. `qg:text`
  takes `value=`, an expression read every frame. Pong, Arena, Chess and
  Towers start on a title with a lobby; `replay_peers(lobby_tapes=...)`
  plays two machines through the menus, over ENet and WebSocket, and checks
  the game is the one the command line gives.
- Laboratory: menus. `qg:menu` holds `qg:button`s (each runs what it holds
  when chosen; `label=` may be an expression read every frame, `if=` shows
  it only while true) and `qg:field`s (a text box bound to a string state).
  A player moves with up/down and chooses with select (Enter, a click, the
  joypad's A); the pointer is the player's `qg:cursor`, so a click is
  replayed and travels in the lockstep like a key. Creeps' title now has
  the demo's Start button. `tests/godot/test_godot_menu.py` drives a menu
  by keys and by the pointer.

- Laboratory: PandaFoot (`projects/pandafoot/pandafoot.q`), a football
  manager after Elifoot 2, Phase 1 of `PLAN_PANDAFOOT.md`: one league of ten
  clubs home and away, for one manager or two to four taking turns at one
  machine, drawn as an 80×25 text screen of the DOS days, in English,
  Portuguese and Spanish. A world is made from its number (squads of 22 by
  `GAME_DESIGN.md` v0.2 of danielgregorio/pandafoot: strength, positions,
  traits by band of strength, a genius hidden in a small club); the
  dashboard, the squad (F3), the line-up (F1),
  tactics (F2), the table (F7) and finances (F5) are a key away; the live
  round plays the five matches in the same minute at 1x to 16x, the table
  moving with each goal, with time-outs, and reactions that change tactics at
  their minute with three seconds to undo them; gates, wages, TV and
  sponsorship after it; saves in three slots. Its box and sounds are drawn
  and synthesized by `scripts/art/pandafoot.py` (CC0), its font is DejaVu
  Sans Mono (its licence beside it). On the games page, and played in CI
  (`tests/godot/test_godot_pandafoot.py`).
- Laboratory: tables, from what PandaFoot asked. `<qg:table source= as=
  rows=>` in a `qg:hud` shows rows of the state, a line each, in
  `<qg:column label= value= width= align= color=>`s: each cell is the
  column's expression of the row, cut or padded to its width, a space
  between the columns; `color=` is a colour or an expression of the row.
  The play protocol reads a table as its headings and the rows' cells as
  shown.
- Laboratory: a menu of rows. `<qg:menu source= as=>` holds one
  `qg:button`, shown for each row of a list read every tick (a squad, the
  clubs, a shop's goods); its `label=`, `if=` and what it runs read the row
  by the name `as=` gives. Its rows are lines of text, the focused one lit.
- Laboratory: menus shown together. Menus of the same player shown at once
  are one column for the keys, in the scene's order: down from one's last
  item goes to the next one's first, up from its first to the previous
  one's last, and the pointer moving onto an item (or a click) brings the
  keys to its menu. The play protocol says `keys: false` of a menu without
  them.
- Laboratory: screens laid out by hand. `x=` and `y=` on `qg:hud` and
  `qg:menu` put their top-left corner on the screen (in place of
  `position=`); `box=` on `qg:hud` frames it as `qg:menu`'s does. `color=`
  on `qg:text` may be an expression, read every frame (red when a balance
  is below zero).
- Laboratory: text formatting and chance in expressions: `fit(v, width)`
  and `fit(v, width, 'right')` cut or pad a text to a column, `thousands(n)`
  and `thousands(n, '.')` write 1,500,000 or 1.500.000, `repeat(text, n)`
  (a bar of blocks), `join(list)` and `join(list, sep)`, `pick(list)` and
  `chance(p)` (as the Core's, from the scene's seeded source).
- Laboratory: records changed in place. `<q:set name="team.points">` sets a
  field of a record (a dictionary in a list sets it there); `index=` sets a
  key of a dictionary as well as an item of a list.
- Laboratory: a world's number. `seed=` on `qg:scene` may be an expression of
  the game's state, read as the scene is entered: the same number, the same
  world. A scene entered again and again with the same seed draws the same
  each time; PandaFoot's round is seeded by the world, the season and the
  round, so each round has its own luck and a replay the same.

### Fixed

- Laboratory: a `qg:state` without `frame=` showed frame 0 of the sheet; it
  keeps the prefab's (or the character's) own frame.
- Laboratory: a character placed in a `qg:exit` as its scene starts (a door
  the room starts at) left by it at once; it is disarmed until the character
  has stepped out, as one arrived at is.
- Laboratory: `count()` and `thing_at()` read as a scene was being built (a
  HUD's first value) stopped the game.
- Laboratory: the tile kinds of a Tiled map's layer were read from the
  scene's tileset, not from the layer's own.
- Laboratory: a scene's `q:set` whose first value read `tiled('name')` was
  null; a property the map has is known as the game compiles.
- Laboratory: `qg:become target="me"` in a prefab's handler was checked
  against the states of every prefab declared after it, so a second prefab
  without that state failed to compile.
- Laboratory: a player rejoining a networked game could wait for good at the
  tick it caught up to: a frame another player sent as it joined reached it
  before the host's inputs so far, which replaced it, or never reached it at
  all. The inputs so far are merged with what has come, and the host hands
  on every frame to whoever came late.
- Laboratory: `count()` and `qg:for-each` leave out a thing whose health has
  reached 0 while its `qg:on-death` runs, so the last brick's handler sees
  none left.
- Laboratory: in a prefab's handler (and a function of the game called from
  one), `qg:goto-scene`, `qg:spawn`, `qg:swap`, `qg:set-tile`, `qg:save` and
  `qg:continue` did nothing, or stopped the game: they looked for the scene
  where the prefabs' handlers live. They find the scene the game is in.
- Laboratory: a prefab that does not move (an item, a solid) accepted
  `qg:on-collision`, which never ran; it is refused, naming what to write
  instead. A thing that walks into a solid prefab (a raider into the tower)
  touches it, as a character does. A flying prefab with `walls=` spawned on a
  character no longer sticks in its body.
- Laboratory: `q:call args=` split its arguments at every comma, so a text
  with a comma (`{'a, b'}`), a list or a call with two arguments became two
  arguments; it splits only between them. In a prefab's handler, `count()`,
  `thing_at()` and `tile_at()` read the scene the prefab is in (they read
  nothing there before).
- A `ui:tabpanel` in a served page switches its tabs on a click (UI-7): the
  page got the tabs' markup and CSS but not their script, so the first tab
  was the only one a browser could show. The script is one listener for every
  tabpanel of the page, and a tab's header is a `type="button"`, so a
  tabpanel inside a form no longer sends it.
- The flash shows once on the console and the Hive's screen (UI-16): both drew
  it on a line of their own, and the page's `<ui:alert>{flash}</ui:alert>`
  drew it again. The view tree says whether the page shows it (`flashShown`).
- A `ui:alert` straight in a `ui:window` is as tall as what it says (UI-7):
  the window's CSS made every `<div>` in it grow, and `examples/form-rules.q`
  drew its message half a window tall.
- `grow="true"` on a `ui:input` with rules takes what is left of its row
  (UI-2): the class went on the `<input>`, not on the box that holds it with
  its error. A `ui:select` in a row is as wide as its options unless it
  grows; it took the row before. `projects/tasks` shows it: a wide title, a
  narrow priority.
- `projects/tasks` (and the tutorial that builds it) draws a refused task's
  flash in red, not in green.
- Quantum OS: the screen's bottom bar says `offers: 1 · F1`, not `1 offers · F1`.
- Quantum OS: the VM lab's `settings` tape goes through the tabs with the real
  keyboard and sends a level from the Screen tab; it pressed the arrows while
  the name field had the focus, and only checked a colour.

- Laboratory: a game that adds to a name nobody declared, in a handler or a
  `q:function` (`<q:set name="score" value="{score + 1}" />` without a
  `q:set` of `score` in the scene or the game), is refused at compile time:
  its first `q:set` reads it before it has a value. It compiled to a
  variable of the handler that started as nothing, and the game stopped
  with a script error when the handler ran.
- Laboratory: `ai="pathfind"` lines up with the middle of its cell before
  it steps into the next one, and does not overshoot where it aims. Cutting
  the corner into a gap's row, a monster was a little off its middle and
  hung on the corner of the wall beside the gap for seconds.
- Laboratory: under `qg:multiplayer`, a peer waiting for the others' input
  froze its scene in a way that took the scene's collision objects out of the
  physics. When they came back, every overlap counted as a new touch, on
  that peer alone. A paddle moving along the ball "hit" it again and drew
  another random slant, and the two games diverged (a desync). The
  lockstep and the rollback now keep the collision objects in the physics
  while they wait. Two browsers playing through a relay wait often, and
  that is how it showed.

- Laboratory: a web build could not join a networked game. A browser has
  no ENet, which `qg:multiplayer` uses unless told otherwise, so the
  title's Join in Pong's web build never reached anyone. In a browser the
  lockstep now always joins over WebSocket; the host must offer it
  (`transport="websocket"`, or `--q-transport=websocket`).
- `scripts/export-games.py` exports on Windows: the templates go where
  Godot looks for them there (and on macOS), and the export path is
  written with forward slashes.
- Laboratory: Hopper was over in seconds for a player who stood still: a
  death put the character back at the start while the walker that killed it
  walked on, into it again. A death now starts the level again — the
  enemies, the coins and the clock as they were — from its checkpoint when
  one was reached (the game's `check_at`, `check_x`, `check_y`).

- Laboratory: a quick click or tap was lost: the game reads its keys once a
  tick, and a press released before the next tick was never seen — on the
  site, Chess picked no piece and Towers built nothing for a brisk click.
  `Q` keeps the presses that come between two ticks for the next one, the
  lockstep and the rollback send them too (`Q.sample_local()`).
- Laboratory: a menu chose nothing on Enter while the mouse rested off its
  buttons (clicking the game to give it the keyboard leaves it there). A
  new default action, `click` (the mouse button alone), tells a click from
  Enter: a click chooses what is under the pointer, or nothing; Enter, or
  the joypad's A, chooses the focused button.
- Laboratory: Arena's fighters are drawn again, as one silhouette each
  instead of separately outlined bones, in a guard with the fists up: they
  read as fighters, and which way each faces.

- Laboratory: Chess on one machine: black could not move. The board took
  black's click only from player 2's select, which no key presses on a
  single machine; now on one machine the same pointer plays both colours,
  and over the network each machine its own.

- Laboratory: the games on the site drew no pictures, played no sounds and
  had no tilemap: the runtime read the image, sound and font files
  themselves, and an exported game (the browser, the desktop zips) carries
  only Godot's imports of them. Every picture was a magenta square and a
  platformer's character fell through a level it could not see. The runtime
  now loads the imports when the files are not there
  (`Q.texture`, `Q.audio`, `Q.font`); `test_godot_exported_files.py` deletes
  a project's files after the import and plays it.

- Laboratory: `qg:shake` drew its jolt from the scene's random source once
  per drawn frame, so two machines drawing at different rates would have
  drawn different random numbers afterwards; it has its own source now.

- Laboratory: the replay dump's `named` listed every second instance of a
  prefab under a name Godot made up (`@Area2D@10`); it lists only the
  things a `qg:instance name=` names.

- Laboratory: a key tapped while a networked game waited for another player
  was lost: the lockstep and the rollback took the keys every frame, and
  what they took while the next tick's input was already recorded was
  dropped. They take the keys once a tick, as they record its input, so the
  tap goes with the next tick. The play protocol lets a `tap` go once the
  game has taken it, not after a frame.

- Laboratory: a game with two fonts or more (the RPG since it speaks
  Russian) sometimes crashed Godot's import, or hung it: the editor imports
  the files of one importer together on several threads. A compiled project
  imports one file at a time (`editor/import/use_multiple_threads=false`).

- Laboratory: a `q:loop` whose variable had the name of a variable of the
  function stopped Godot from loading the script; the compiler refuses it
  with the line. A variable read as a field of another (`m.luck`) is not
  the variable `luck`, which a first `q:set` may now read. An expression
  that reads a field named like a word of the language (`side.def`) says so,
  and a variable named like a property of every node gives its line.
- Laboratory: a HUD hidden by its `if=` still read what it shows every
  frame (an `if="{len(live) > 0}"` did not keep `live[0]` from being read).
- Laboratory: the play protocol wrote every variable of the scene and the game
  out as JSON twice a tick, to see what changed: a league of 220 players
  played a round at 16x in tens of seconds. Each variable is hashed a tick
  and written only when it changed, and a list or a record changed in place
  (a player's goals) is a `set` event too, which it was not.

### Changed

- Laboratory: a scene's `q:set` whose value is computed (it calls a
  function, reads the game's state or draws at random) is set as the scene
  is entered, after its random source is seeded and before what the scene
  runs, in the order written; it read an unseeded source before, and could
  not call a q:function. A constant (`{3}`, `{[]}`) is the value from the
  start, as before. The game's q:functions may be written after the scenes
  that use them.
- The repository is English everywhere, with no exception for Portuguese
  (`CODING.md`): the example app `projects/tarefas` is `projects/tasks`, the
  same app the tutorial builds (`components/sheet.q`, `components/task/[id].q`,
  `tests/tasks.test.q`; its Python tests are `tests/apps/test_tasks*.py`; the
  showcase's screenshot is `tasks.png`). The rest followed: the sign-up form
  of `examples/form-rules.q`, the suggestions of
  `examples/quantum-assistant.q`, the books of the search-as-you-type recipe,
  comments and identifiers in the runtime, the admin and the tests, the
  phase demos of the AS4 compiler (`phase1-mvp-demo` and the others), the
  tile factory's messages and `benchmarks/README.md`. The site's pages in
  Portuguese, Spanish and Chinese, and the games' `qg:language` phrases, are
  translations of English sources and stay.
- An action's parameter named `senha` is no longer treated as a password
  (kept out of the form refilled after an error) by its name alone: declare
  it `type="password"`, or name it `password`.

- Laboratory: the game runtime reads input through `Q` (`Q.held`,
  `Q.tapped`, `Q.strength`), sampled once per physics tick before any
  node runs, instead of asking Godot's `Input` from each node. A tick's
  input is a value the lockstep sets directly (no more `raw_` shadow
  actions), and the base for rollback. One visible effect: a press is
  seen on the tick it happens; Godot's `is_action_just_pressed`, called
  from a replay's main loop, saw it a tick later.

### Removed

- Laboratory: the old game parser (`quantum/core/features/game_engine_2d`)
  and Godot generator (`godot_code_generator.py`, `godot_templates.py`)
  with their tests: the new compiler reads the elements itself, and the
  old parser rejected every tag it did not know.
- Laboratory: the HTML game backend (PixiJS + Matter.js) is gone. A
  `q:application type="game"` builds a Godot 4 project, the only backend;
  `quantum run game.q` no longer takes `--engine`.
- Laboratory: the games written for that backend are gone with it —
  `projects/quantum-snake`, `quantum-tictactoe`, `kenney-platformer` and
  the game examples (`snake.q`, `tictactoe.q`, `platformer.q`, `fighter.q`,
  `adventure.q`, `kenney_platformer.q`), whose logic was JavaScript against
  its runtime. The language is being redesigned (`PLAN_GAMES_2.md`) and
  owes them no compatibility; the three games of that plan replace them.
  The Kenney CC0 art and sounds they used stay, in `assets/kenney/`.

### Added

- Laboratory: the games on the site — `docs/targets/play.md` lists the
  eight games with a browser build, Linux and Windows downloads, controls
  and the network commands. `scripts/export-games.py` exports every
  `projects/<name>/<name>.q` with Godot's templates (the web build without
  threads, so it runs on a static host) and installs the templates itself
  (`--install-templates`); the Deploy Docs workflow runs it, with the
  templates cached, before the site is built. Nothing exported is committed.
- Laboratory: an eighth game, `projects/chess/chess.q` — chess, its rules
  written in `q:function`s over an array of 64 squares (the rules of
  github.com/Prashanna135/chess, MIT; `projects/chess/README.md` maps it),
  white and black over the network. What it made the language grow:
  **local variables** — a `q:set` of an undeclared name inside a
  `q:function` or a handler is the call's own (the first recursion the
  language met); `<q:set name="board" index="{i}" />` for one element of
  an array; `qg:put target= x= y=`; `qg:destroy`, `qg:swap`, `qg:put` on
  any name holding a thing, and a named `qg:instance` as a name in its
  scene; `qg:hud position="bottom-center"`.
- Laboratory: a seventh game, `projects/arena/arena.q` — a one-on-one
  fighting game (`projects/arena/README.md`), two players over the network.
  What it made the language grow: `controller="fighter"` (walk, jump,
  crouch, block by holding away, hit stun and push back, KO) with
  `health=` and `facing=`; `qg:move` — an attack on an action with frame
  data: `frames`, `active`, `reach`, `at`, `damage`, `stun`, `push`;
  `qg:on-ko`; `qg:bar` in the HUD bound to a q:set or a fighter's
  `id.health`; a character's id as a name in its scene's expressions
  (`p1.health`) and as an action target (`qg:respawn target="p1"`).
- Laboratory: a sixth game, `projects/towers/towers.q` — the MIT "Godot 4
  Tower Defense Template" transcribed (`projects/towers/README.md` maps it),
  playable by two over the network. What it made the language grow: named
  actions (`qg:input action="buy-gatling"`, `qg:on-input` on any declared
  action), `MouseLeft`/`MouseRight` keys and the default `select`/`cancel`
  actions; `qg:cursor` (the mouse, or a player's directions, snapped to
  `grid=`) and `qg:on-select` with `cursor` and `other` — under
  `qg:multiplayer` the cursor travels in the input frame; `count(tag)` and
  `thing_at(tag, x, y)` in expressions; `qg:path points=` with `ai="path"`
  and `qg:spawn at="path"`; `ai="turret" targets= range= attack= damage=`
  firing `fire-prefab` at the nearest target, `fire-prefab`/`range` on a
  `qg:state`, `qg:become target="other"`, `qg:spawn at="cursor"`. The
  replay tape takes `cursor` events (`cursor_at()`).
- Laboratory: declarative multiplayer. `<qg:multiplayer players="2" />` in
  a game: every peer runs the whole game in lockstep — a tick runs when
  every player's input for it has arrived, `delay=` ticks after the press;
  the peers compare a hash of the whole state every `check-every=` ticks
  and a difference is a reported, fatal desync. One peer hosts
  (`--q-host=PORT`, player 1), the others join (`--q-join=HOST:PORT`);
  `player=` on the characters says whose is whose, as it did on one
  keyboard. Nothing else in the game knows. `replay_peers()` runs N
  headless Godots on localhost under tapes; `tests/godot/test_godot_multiplayer.py`
  plays Pong on two and checks they agree with each other and with one
  Godot replaying both tapes. Design and what is left: `PLAN_MULTIPLAYER.md`.
- Laboratory: a fifth game, `projects/creeps/creeps.q` — Godot's "Dodge the
  Creeps" tutorial game transcribed (`projects/creeps/README.md` maps it).
  What it made the language grow: `qg:spawner along="edges" heading="inward"
  spread=`, several prefabs drawn at random and `count="0"`; `speed="150..250"`
  and `rotate=` on a prefab; `bounds="scene"`, `walk-up`/`walk-down` and
  analog strength on the top-down controller; `qg:hud position="center"`,
  `font=`, `size=`; `loop=` on `qg:sound`, `qg:stop`, and `qg:play`/`qg:stop`
  directly in a scene; `from=` on `qg:timer every=`; a `q:set` of a
  game-wide name in a scene sets it as the scene is entered.
  `tests/godot/test_godot_creeps.py` replays it. `scripts/pack-sprites.py`
  packs separate frames into a sheet.
- Laboratory: joypads. `qg:input keys=` takes `JoyA`, `JoyUp`, `JoyLeftStickUp`
  and the rest (the reference lists them); player n reads joypad n-1; the
  defaults include the pad and the left stick; the ship and top-down
  controllers read the stick's strength.
- Laboratory: a scene state named like any member of Godot's `Node2D`
  (`ready`, `draw`, `show`…) is a compile error, from the same generated
  reference `gd:` attributes use; it was a GDScript error at run time.
- Laboratory: a fourth game, `projects/pong/pong.q` — Godot's own "Pong
  with GDScript" demo (godotengine/godot-demo-projects, MIT) transcribed
  tag for node; `projects/pong/README.md` maps each piece of the original
  to its tag. What it made the language grow, each a tag or an attribute:
  `player=` on `qg:input` and `qg:character` (a second player's keys, as
  `p2_up`…); `axis=` on the ship controller; `qg:zone` (an invisible
  tagged rectangle, touched like a prefab); `heading="x,y"` and `accel=`
  on a flying prefab, `qg:deflect` (reflect one axis, or set `dx`/`dy`),
  `qg:respawn target="other"`; `tile="8x32"` on `qg:spritesheet` for frames
  that are not square; `qg:sprite` (a picture with no behaviour); and
  `random(a, b)` in expressions, from the scene's seeded source.
  `tests/godot/test_godot_pong.py` replays it.
- Laboratory: `gd:` attributes on game tags — `<qg:camera gd:zoom="2,2" />`
  sets `Camera2D.zoom`. A pure forward: the compiler checks the name and the
  type against Godot's own class reference (`godot_properties.json`,
  generated from `godot --doctool` by `scripts/generate-godot-properties.py`),
  and the runtime calls `node.set()` once as the scene is built. Properties
  only (float, int, bool, String, Vector2, Vector2i, Color); methods, signals
  and what the runtime sets itself (`position`, `velocity`, the collision
  layers) are not forwarded. A wrong name is a compile error naming the
  properties the class has. `tests/godot/test_godot_gd.py` reads back, in
  Godot, the class and the values of every kind of node.
- Laboratory: a new game compiler and runtime (`quantum/runtime/godot/`),
  rebuilt from scratch on the "thin compiler, fat runtime" design of
  `PLAN_GAMES_2.md`. The `.q` compiles to `game.json` (everything
  declarative), one GDScript per scene (its `q:set`s as properties, its
  `q:function`s and handlers as methods, Quantum expressions compiled to
  GDScript), and a fixed runtime, `addons/quantum/`, that builds the scene
  tree from the JSON. The schema (`schema.py`) is the language: an unknown
  tag or attribute, a name no `q:set` declared, text where statements go
  (the old backend's JavaScript) — each is a compile error with its line.
  Tags so far: `qg:tileset`, `qg:spritesheet`, `qg:prefab`, `qg:scene`,
  `qg:tilemap` (CSV), `qg:character controller="platformer"` (kinematic,
  with `run-speed`, `jump-height` to the pixel, variable jump, coyote
  frames), `qg:on-collision with=`, `qg:destroy`, `qg:instance`,
  `qg:camera`, `qg:hud` with `qg:counter`; and `q:set`, `q:if`/`q:else`/
  `q:elseif`, `q:loop`, `q:function`, `q:return` inside handlers. Then, for
  the platformer: `qg:sound` and `qg:play`; `qg:animation` (frames cycled
  by physics ticks — a character plays idle/walk/jump by what it does);
  `qg:prefab ai="patrol"` (walks, turns at walls or edges, under gravity);
  `qg:on-collision side="top"` (a stomp) with `cooldown=` ticks; `qg:bounce`,
  `qg:respawn`; `qg:on-fall` below the tilemap; `jump-sound=`. Things
  collide with the tiles, not with the characters: touching is the areas'
  job, so a walker hurts instead of blocking. Then: `qg:state` (a form of
  the character — hitbox, frame, animations; `me.state` reads it) and
  `qg:become`; `qg:prefab solid="true"` (a block to stand on and bump) with
  `qg:on-collision side="bottom"`; `qg:spawn`, `qg:swap`, `qg:checkpoint`;
  `qg:text` in the HUD. Then: a `q:set` in `<q:application>` is the game's
  state, kept across scenes (an autoload `G`); `qg:goto-scene`; a world
  map (`qg:character controller="map"`, `qg:map-node`, `qg:map-path
  requires=`); `qg:on-input` in a scene; `q:call` of a `q:function`. And
  `qg:tilemap src="level.tmx"`: a level drawn in Tiled — its tile layers
  (a `collision` property makes one solid) and its object layers, whose
  objects place prefabs by their class. For the top-down game:
  `qg:character controller="topdown"` (eight directions, `speed=`, a swing
  on `attack-action=` with `attack-reach=`/`attack-frames=`), `qg:on-hit`
  for what the swing reaches, `qg:exit` (a rectangle that leads to another
  scene, arriving at the exit named there — disarmed until left),
  `qg:prefab ai="wander"` (headings from the scene's seed) and
  `ai="chase" sight=`, `qg:instance name=` (`other.name` in a handler) and
  `if=` (placed only when true as the scene is built). For the shooter:
  `qg:character controller="ship"` (eight directions, kept in the scene,
  shoots `fire-prefab=` every `fire-every=` ticks while `fire-action=` is
  held); `qg:prefab ai="fly" heading= lifetime=` and `ai="sway"`;
  `health=` with `qg:damage`, `qg:on-damage` and `qg:on-death` (in the
  prefab, or in the scene with `of=` a tag); `qg:on-collision` in a
  prefab (a shot that hits); `qg:state` on a prefab (frame, speed,
  fire-every); `qg:spawner` (so many of a prefab, every so many ticks,
  `x="random"` from the scene's seed); `qg:burst` and `qg:shake`
  (cosmetic); a `q:set` in `<q:application>` with `saved="true"` is kept
  between runs (a file in `user://`; the replay harness gives each run its
  own); `q:if`/`q:loop`/`q:call` directly in a scene run as it is entered.
- `projects/drift/drift.q`, the vertical shooter: three waves of drones
  and tanks that come down and shoot, then a boss with two phases; lives,
  score and a high score kept between runs — zero lines of script.
  `tests/godot/test_godot_drift.py` replays it: the waves come from the
  seed the same way every run, shots kill drones and the score counts,
  drones and their shots cost lives, the boss turns angry below half
  health and its death wins, the high score survives into the next run,
  three lives lost are game over and jump starts again.
- `projects/keep/keep.q`, the top-down adventure: six rooms of a keep, a
  character that walks in eight directions and swings a sword, slimes
  that wander and bats that chase, a sign, hearts, a key and a locked
  door, a switch that opens a gate in another room, a chest at the end, a
  game over — zero lines of script. `tests/godot/test_godot_keep.py`
  replays it: the slime wanders the same way from the same seed, walking
  into an exit changes room and arrives at the matching exit, the bat
  chases within sight and hurts once per cooldown, the swing kills it, the
  key opens the door, the gate blocks until the switch is thrown, the
  chest ends the game, three hurts are game over and jump starts again.
- `projects/hopper/hopper.q`, the platformer: a world map and three
  levels (the second drawn in Tiled). A character that walks and jumps on a tilemap, blocks with a
  power-up in them that makes it big (a hit makes it small again), coins,
  walkers to stomp or be hurt by, pits, checkpoints, spikes, a flag at the
  end of each level that opens the next on the map, a game over after
  three deaths; score, coins, lives and a message in the HUD — zero lines
  of script. `tests/godot/test_godot_hopper.py` replays it in Godot: the
  game starts on the map and a shut path stays shut; jump enters a level;
  the character rests on the ground, runs at its `run-speed`, a held jump
  peaks at `jump-height` within a pixel, a tap is a short hop, a coin
  collected is counted, the block opens from below, the power-up and the
  hit change its state, the walker hurts once (cooldown) and sends it
  back to the start, landing on the walker stomps it, the pit costs a
  life, the spikes send it back to the checkpoint, the flag wins the level
  and opens the next on the map, three deaths are game over and jump
  starts again, and the same tape gives the same game.
- Laboratory, after the plan closed: `qg:input` (a game's own keys for an
  action); `qg:timer after=` / `every=` in a scene (Hopper's clock,
  Drift's "here it comes"); `qg:prefab solid="true" one-way="true"` (a
  ledge jumped through from below) and `ai="shuttle"` (a lift that goes
  `dx`,`dy` and back every `period` ticks, carrying what stands on it);
  slices in expressions (`items[1:3]`, `name[-2:]`); `q:loop` over a
  dictionary iterates its keys, as GDScript does. A `q:set` without
  `type=` is a `Variant` in GDScript, so a number may follow a string as
  in Quantum; a `q:set` named like a Godot node property (`name`,
  `position`...) is refused. `str()` of a whole number is `7`, not `7.0`.
  `tests/godot/test_godot_expressions.py` runs 45 expressions in Godot
  and compares each with the Core evaluator.
- `docs/targets/games.md`, the game language reference, generated from the
  compiler's schema and the three games by `scripts/generate-games-reference.py`
  (a test fails when it is stale); `scripts/export-games.py` exports the
  games for the web with Godot's export templates, when they are installed.
- Laboratory: the real engine checks and replays a game, headless.
  `quantum run game.q --check` opens the built Godot project and fails on
  any script error (Godot exits 0 either way; the check reads its output).
  `quantum/runtime/godot_replay.py` runs a game for N physics ticks under
  an input tape and returns the state every node reports through
  `quantum_state()` — the same tape, the same state, which is how the games
  get tested. The Godot version is pinned in `quantum/runtime/godot_bin.py`;
  `python scripts/godot.py install` downloads it into `~/.cache/quantum/godot`,
  and the Laboratory CI job does the same (cached by version). Without it,
  the tests in `tests/godot/` skip.
- A playground on the site (/playground/): the Cookbook's recipes, editable,
  run in the browser by the real `quantum-framework` from PyPI (Pyodide) —
  with the database built from their migrations, links and forms that work,
  and **Run tests** for their `*.test.q` files. The AI recipes are left out;
  they need a model. It replaces `playground/`, a small interpreter of its
  own that imitated Quantum. `scripts/check-playground.mjs` runs every example
  in Pyodide in CI.

## 1.0.1

### Added

- Screen readers hear the nav, sidebar and pager labels in the page's
  language (VitePress writes them in English): the build writes them into
  each page's HTML, and `theme/aria-labels.js` sets them again after each
  navigation, from `ariaLabels` in `locales.js`.
- The Support page links to Patreon, in the four languages, and
  `.github/FUNDING.yml` puts the Sponsor button on the repository.
- The site counts visits with Cloudflare Web Analytics, which sets no cookies
  and collects no personal data; Google Tag Manager is gone.
- The language switcher goes to the same page in the other language when it
  is translated, and to that language's home otherwise — in every direction.
  The pages it knows come from `TRANSLATED` in `docs/.vitepress/locales.js`
  (and the translated pages under a listed section such as `/cookbook/`);
  `tests/docs/test_language_switch.py` checks that each is a page and that
  every translated page is reachable.
- A translated page records the English page it came from and the hash of its
  text (`source:` / `source_hash:`). When the English changes, the page says
  "this translation may be out of date" with a link to the English, and CI
  lists the stale pages (`scripts/translation-status.py`; `--stamp` after
  updating a translation). `tests/docs/test_translations.py` checks that every
  translation names an English page that exists and is in its language's
  navigation.
- The site speaks four languages: English, and /pt/ (pt-BR), /es/ and
  /zh/ (zh-CN), with a language switcher and each language's interface text;
  the pages are translated next. The top nav is Home · Docs (Guide, Tutorial,
  Reference, SPEC) · Showcase · Blog · Changelog · Status · Sponsor. Search
  splits Chinese into words (it found nothing inside a Chinese sentence), and
  each page carries hreflang alternates and Open Graph tags.

### Documented

- The Examples page in Portuguese, Spanish and Chinese. Every live page now
  has a translation except the generated ones (Reference, SPEC, Changelog),
  which stay in English: their entries in the pt/es/zh navigation say so.

- Every `quantum …` command in a published page's shell block (all four
  languages) is parsed by the real command line in CI
  (`tests/docs/test_docs_commands.py`); the homes, the Sponsor page, the blog
  posts and the Roadmap may hold only imports of tested Cookbook files and
  such commands; the theme's example components may appear only on
  unpublished pages.
- The Blog index and Status page in Spanish and Simplified Chinese, generated
  like the Portuguese ones (`LANGS` in `scripts/generate-site-pages.py`).
- The docs' deprecated-content check caught a removed value only as written
  in code: the q:application page listed `testing` in its table of types and
  `desktop` in a list of targets, and both slipped past. It now also reads
  table rows and lists of values, has patterns for more of the changelog's
  removals (attributes of `q:column`, `q:set`, `q:param`, `q:query` and
  `q:function`, a slice step, the mail mock, upload URLs, removed projects,
  the admin's deploy feature), and each pattern proves it catches a sample.
  `tests/docs/test_quoted_messages.py` checks that a message the site quotes
  in a text block uses only words Quantum prints.
- The Tools pages (the CLI, hot reload, the `/_dev` panel, error pages,
  `quantum check`, the VS Code extension, the LSP server) and Desktop in
  Portuguese, Spanish and Chinese, and Community in Spanish and Chinese, with
  their sidebars. Headings keep the English anchors; the VS Code page is
  generated per language from the extension's manifest. Machine translated
  and marked so.
- More of the guide in Simplified Chinese: AI, files and mail, data import,
  services, sessions, the admin, project structure and `q:application`,
  machine-translated, with the English heading anchors.
- The q:application page no longer lists `type="testing"` (removed in 0.22,
  replaced by `quantum test`) or a `--target desktop` for `type="ui"`
  (removed in 0.16), and quotes the parser's message as it is.
- The Blog index, Status and Community pages in Brazilian Portuguese.
  `scripts/generate-site-pages.py` writes the translated Blog index and Status
  page (`LANGS`) around the same posts and the same measured tables, stamped
  with the English page's hash; the nav's Blog and Status links go to the
  translation when there is one.
- The rest of the guide in Brazilian Portuguese: AI, files and mail, data
  import, services, sessions, the admin, project structure and
  `q:application` — every guide page now has a pt version. The pt guide
  pages keep the English heading anchors, so a link to a section works in
  both.
- Roadmap and Community in the top nav, in every language. The Showcase in
  Portuguese, Spanish and Chinese, written by `scripts/generate-showcase.py`
  with the same measured numbers as the English page; the Roadmap and the
  tutorial in Chinese. All machine translated and marked so.
- The core guide in Brazilian Portuguese (/pt/guide/): getting started,
  components, how a page runs, state, loops, conditionals, functions,
  expressions, actions, queries, authentication, UI and testing,
  machine-translated, with the code and its output identical to the English
  and the same heading anchors; the pt guide sidebar has Portuguese labels.
- The core guide in Spanish and Simplified Chinese: Getting Started,
  Components, How a Page Runs, State Management, Loops, Conditionals,
  Functions, Expressions & Databinding, Actions & Forms, Database Queries,
  Authentication, One App, Many Screens and Testing an App (and, in Spanish,
  the rest of the guide: AI, Files and Mail, Data Import, Declared Services,
  Sessions, Quantum Admin, Project Structure and q:application) — machine
  translated and marked as such. The prose is translated segment by segment
  around the English page's code, which is copied as it is; each heading keeps
  the English anchor, so links to a section work in every language.
- The Cookbook in Spanish (/es/cookbook/) and Simplified Chinese
  (/zh/cookbook/): all 51 recipes, machine translated and marked as such. The
  code and results on each page are the English page's imports of the tested
  files, line for line; the prose follows each language's glossary.
- The repository's front door meets the site's bar. README's Quantum examples
  are files of Cookbook recipes, byte for byte, and its quick start is run as
  shown (`tests/docs/test_readme.py`, which also checks the site and file links
  of README, CONTRIBUTING, SECURITY, SUPPORT_TIERS and the Code of Conduct);
  the deprecated-content check reads those five files too. README's AI
  examples used a model name as if it were a default and an attribute
  (`minRelevance`) its text no longer explained; it now links the Cookbook,
  Tutorial, Reference, Showcase, Stability and Roadmap. CONTRIBUTING pointed to
  Discussions, which are off; SECURITY called 1.0 "experimental" and suggested
  an environment variable nothing reads; SUPPORT_TIERS cited two files that are
  not in the repository.
- The Cookbook in Brazilian Portuguese (/pt/cookbook/), machine-translated:
  the code and the results are the same files the English imports. The
  generator writes each language's Cookbook index (`LANGS` in
  `scripts/generate-cookbook.py`), linking the English page where a recipe is
  not translated yet. All 51 recipes are translated; a test checks that every
  translated page imports the same files as its English page, in order.
- Cookbook, "Screens": a layout that fits the screen, a table edited in
  place, tabs, cards, every kind of field, and the same page in a terminal;
  six tested recipes, two of them also checked in the console
  (`tests/docs/test_cookbook_console.py`).
- Cookbook, "Basics": a first page, variables and expressions, loops,
  conditionals, functions, a page per URL, the query string and reusable
  components with a slot; eight tested recipes.
- Cookbook, "AI": answers with their sources, when the documents do not know
  (`minRelevance`), a streamed answer, an agent over your database, when the
  model fails (`onerror`), sorting messages with JSON answers, and answers
  from a table; seven recipes. In CI they run against a stand-in model server
  (`scripts/generate-cookbook.py`); before a release, against a real one
  (`tests/live_ai/test_cookbook_ai.py`). Their tests check structure, never the
  model's words.
- The CLI and LSP server pages say what exists. The CLI page taught exit
  codes, environment variables and a `quantum pkg uninstall` that do not
  exist, and `quantum start --debug` as debug mode; the LSP page, a
  `pip install quantum-lsp` (it is not on PyPI), rename, code actions,
  options and editor packages the server does not have. The VS Code page no
  longer implies the extension runs the language server. Five old notes
  linked from no menu leave the site: a benchmark nothing reproduces, the
  `q:query` implementation plan and the performance-phase notes.
- The essential pages in Brazilian Portuguese (/pt/): why Quantum,
  installation, quick start, the tutorial, stability, sponsor, the roadmap and
  the 1.0 post, machine-translated until a native speaker reviews them, with a
  glossary (`docs/.vitepress/i18n/glossary.pt.md`) that keeps the terms the same
  on every page.
- Cookbook, "Data & SQL": a query with parameters, a paginated list, search
  as you type, filter and sort, writes that happen together (a transaction
  rolled back when its last write fails), change history, adding a column
  with a migration, reading CSV and JSON, loading a CSV into a table in one
  transaction, and totals computed over a query's result; eleven tested
  recipes.
- Cookbook, "Forms & actions": each error on its field, a refused form that
  keeps what was typed, redirect with a flash (`q:flash` for a warning),
  several forms on one page, a form from the table, edit a row, confirm
  before deleting, numbers and dates, and a choice from a list; nine tested
  recipes.
- Cookbook, "Login & permissions": log in with a hashed password, sign up and
  store a hash, a page for one role only, a guard that redirects (and stops the
  page's actions), and sign out; five tested recipes.
- Every `xml` example of the guide now runs: with the result it shows, or in
  a test that runs the page's code as written (`tests/docs/test_guide_*.py`);
  the docs guard's list of pages that were only parsed is empty. Running them
  fixed what they claimed: the components page said several `q:return`s
  returned a list (the first one ends the component, SPEC RET-1), and the
  home page's example now imports the tested "first test" recipe.
- The site in Spanish (`/es/`, machine translated, reviews welcome): the home,
  Why Quantum, Installation, Quick start, Stability, Sponsor, the Roadmap,
  the tutorial and the "Quantum 1.0" post. Code blocks are the English ones; the terms are in
  `docs/.vitepress/i18n/glossary.es.md`.
- Cookbook recipes: "When the mail server says no" (`onerror="continue"`),
  "Test data with test:given" (and `test:as`) and "Testing what an action
  refuses" (`error=`, `message=`, `flash=`, `table=`). Recipes in a topic
  keep an order (`order:` in the page's front matter).
- Pages that described what does not work are gone: the plugin system
  (nothing loads plugins), the package manager page (pages cannot import a
  component from an installed package; `q:import from=` is a folder under
  `paths.components`), and the HTML, terminal and mobile target pages (what
  is true about them is in the guide's "Standalone builds"). The VS Code
  extension page is generated from its manifest and says how to run it from
  source — it is not on the Marketplace.
- A Stability page (/stability/), generated from SUPPORT_TIERS.md: what 1.0
  promises, tag by tag, and the semver promise for Core and AI.
- Simplified Chinese (zh-CN) for Why Quantum, Installation, Quick start,
  Stability, Support and the "Quantum 1.0" post — machine translated, marked
  as such until a native speaker reviews them. A translated page must show
  the English code, block for block (the docs guard checks it), and the nav
  links to a translation when one exists. The zh glossary is in
  docs/.vitepress/i18n/glossary.zh.md.
- The site no longer publishes the 15 hand-written example and feature pages
  (`docs/examples/*`, `docs/features/*`) whose code did not work with 1.0: they
  taught removed attributes (`persist=`, `maxSize=`, `cache=`) and tags that
  never existed (`q:try`). The Cookbook, the Showcase and the tutorial replace
  them; the files stay in the repository to be rewritten as recipes.
- `tests/docs/test_no_deprecated_content.py`: a published page that shows
  something removed or renamed in the changelog (a tag, an attribute, a CLI
  command, a tier name, a default) as current fails CI. Two pages were fixed:
  the UI guide named `quantum new`, and the CLI reference a retired tier name.
- The hand-written `ui:` component pages (docs/ui/) are gone: they taught
  components that do not exist. The generated [UI tags](/reference/ui)
  reference and the "One App, Many Screens" guide replace them. The Cookbook
  is in the Docs menu in all four languages.
- Tutorial, "Build the tasks app": from `pip install` to the app in
  `projects/tarefas`, in English, in eight steps (validated forms, finish and
  delete, a filter, a table that sorts and edits itself, an edit page with
  history, a `quantum test` suite). Each step's code is built and run as shown
  by `tests/docs/test_tutorial_tasks_app.py`, and the finished app is checked
  against `projects/tarefas`, tag by tag.
- Showcase: the seven proving apps with a screenshot of each running
  (`scripts/showcase-screenshots.py`, the AI apps on a stand-in model server),
  what it demonstrates, the SPEC rules it cites, its size, its tests and its
  source. The numbers are measured by `scripts/generate-showcase.py`, and
  `tests/docs/test_showcase.py` fails when the page and the apps disagree.
- The Cookbook: short recipes for one task each. A recipe is a small app in
  `examples/cookbook/` with a `quantum test` suite; its page imports the tested
  files, and what it shows as a result is written by running it
  (`scripts/generate-cookbook.py`). The first two: a first test with
  `quantum test`, and mail in development with `host: log`.
- Quantum code on the site is tested: CI fails on an `xml` block that is not a
  run guide example, a parsed guide or generated-reference example, or on a
  page marked "Under review"; a `quantum.config.yaml` snippet must load
  without errors or warnings. Two snippets taught keys that do not exist.
- Every `xml` example on the site is checked by the real parser in CI
  (tests/docs/test_docs_xml_blocks.py); the guide's examples with a result
  are also run. 121 of 607 failed: the guide's are fixed, the editor
  illustrations are plain text, and 22 hand-written pages that document tags
  that do not exist (the `ui:` component pages, UI features, some example and
  target pages) say "Under review" at the top until tested examples replace
  them.
- The site has a changelog (one page per version, with stable anchors), a
  status page ("what really works today", from FEATURE_STATUS.md), a blog
  with an RSS feed and the "Quantum 1.0" post, a support page and a community
  page. `scripts/generate-site-pages.py` builds the derived pages, and CI fails
  if they are stale.
- The site has a Reference generated from the code (`docs/reference/`,
  `scripts/generate-reference.py`): the Core and AI tags with every attribute,
  type, value, default and the rules that specify them; the expression
  functions; the command line; the configuration keys; the `ui:*` tags, Core
  (UI-7) and Experimental apart, with every attribute the UI parser reads;
  and the SPEC with an anchor per rule (`reference/spec#EXPR-14`) that lists
  the entries citing it. A test fails when a committed page differs from what
  the generator writes. It replaces the hand-written `api/tags-reference`,
  `api/attributes-reference` and `api/ui-reference` pages.
- The site has a Roadmap (`roadmap/`): what 1.0 promises, and what is next,
  each item with its status (planned, in design, in progress) and no dates.

### Fixed

- The VS Code extension packages: `vsce package` stopped on an icon that
  `package.json` named and the repository never had. The extension carries
  its icon and the MIT LICENSE, and leaves its TypeScript sources out.

- Two pages with an in-memory `q:knowledge` of the same name and different
  sources deleted each other's index: the other page's search failed with
  chromadb's "Collection [...] does not exist", or — at the wrong moment —
  found nothing, which reads as an honest "I don't know". In-memory bases are
  now separate by sources as well as name (IA-2), and a base that was built
  with chunks and has none when searched is an error, never `found` false
  (IA-6). The three most recently built in-memory versions of each base are
  kept; older ones are dropped.

- `python -m quantum.cli.runner` — the installation guide's way to run
  `quantum` without the script on `PATH` — no longer prints a
  `RuntimeWarning` before every command. `quantum start --debug` says what it
  does: it prints the traceback when the server fails to start; debug mode is
  `server.debug` in `quantum.config.yaml`.
- A `q:query` inside a `q:loop` or a `q:if` of a `q:transaction datasource="…"`
  takes the transaction's datasource, like one directly inside it (DB-4); it
  had to repeat `datasource=`, or the page did not parse.
- `q:set name="cart"` is local even when the session has a `cart` (SET-3,
  EXPR-11). It used to overwrite `session.cart` and leave `cart` undefined, so
  the page showed `{len(cart)}` as written.
- `q:set name="session.cart" operation="append"` starts a list when the key
  does not exist yet (SET-3). It was refused as "non-array": a missing scope
  key reads as `''`.
- A page's extracted stylesheet and script (`static/styles-<hash>.css`) are
  written whole or not at all. Written in place, a second request during the
  write linked the file while it was still empty or partial, and its browser
  got an unstyled page, cached under a name that never changes.
- `q:loop type="range"` takes expressions in `from`, `to` and `step`, like any
  other `{...}` attribute (LOOP-5): `to="{count}"` was read as the text
  "{count}" — an error in a statement, zero rows in markup — and `step="{n}"`
  became 1. A bound that is not a whole number is now an error that names it,
  in markup too, where it used to draw zero rows.
- `q:param type="date"` on an action is checked on the server: `2026-02-30`
  or `tomorrow` is refused on its field (ACT-2). Only the browser's date
  input checked it before, and any text reached the action.
- A `q:param` `default=` on an action has the param's type (ACT-2). It was
  used as text, so `type="boolean" default="false"` gave `"false"`, which is
  true: an unchecked box read as checked.
- `quantum run --target desktop` is no longer offered: the command line says
  the target was removed and points to `quantum desktop` (UI-8). It used to
  accept the choice and fail later, in the build.

## 1.0.0

Quantum 1.0: **declarative web applications in XML, with AI and RAG built into
the language. No build chain, no JavaScript, no front-end framework.**

The road from the first public release ([0.9.0](#090)) to here was mostly
about making that sentence true, and only that sentence:

- **What is promised is written down.** `SUPPORT_TIERS.md` splits the
  language into Core (the web framework: components, state, conditions,
  loops, functions, parameterised queries and transactions, actions and
  forms, composition, files, mail, the Core set of `ui:*`, authentication),
  AI (`q:llm`, `q:knowledge`, `q:agent`), Experimental and Laboratory, and the
  engine enforces it: a tag outside Core and AI warns once when it runs
  ([0.10.0](#0100), [0.21.0](#0210)).
- **What a program means is specified.** `SPEC.md` states the Core and AI as
  rules with IDs, frozen at 1.0, and every rule is cited by a conformance
  test that fails if the rule and the runtime disagree
  (`tests/conformance/`, with `test_spec_ids.py` checking both directions).
  Decisions that used to be silent — a missing name, a failed expression, a
  missing key, an attribute that did nothing — are errors that say where
  they are ([0.11.0](#0110) through [1.0](#10-changes-since-0220)).
- **What is claimed is run.** Apps in the repository prove the tiers:
  `projects/tarefas` (the UI engine), `projects/blog` and `projects/helpdesk`
  (Core, files and mail), `projects/bank-transfer` (`q:transaction`),
  `projects/docs-assistant` and `projects/shop-agent` (AI). **`quantum test`**
  ([0.22.0](#0220)) tests an app in its own language, on a fresh database
  built from its migrations; the apps' suites run in CI.
  `FEATURE_STATUS.md` is generated by executing every example, never written
  by hand.
- **AI you can build on.** Answers cite the chunks they came from and say
  when they are grounded, a relevance floor keeps the model from answering
  from nothing, answers can stream, and every AI tag has a failure contract
  (`onerror`, time budgets) instead of an exception in the page
  ([0.20.0](#0200), [0.22.0](#0220)).
- **One page, three renderers.** The same `.q` page with `ui:*` is drawn by
  the browser (`quantum start`), the terminal (`quantum console`) and a
  desktop window (`quantum desktop`), with forms that know their action's
  rules, tables from data and a declared responsive layout ([0.15.0](#0150)
  through [0.18.0](#0180)).
- **Tools around the language.** `quantum check` (pages, SQL and query
  fields against the database), `migrate plan` from a `schema.sql`, change
  history, the `/_dev` panel, errors that point to the line
  ([0.17.0](#0170), [0.19.0](#0190)).
- **In English.** Code, messages, tests, the SPEC and the documentation.

The changes since [0.22.0](#0220) — released as part of 1.0, with no 0.23
of their own — are below.

### 1.0: changes since 0.22.0

#### Added

- `get(x, key, default)` in expressions reads a key that may be missing, or a
  list index that may be out of range, and gives `default` (`null` when left
  out) (EXPR-16).
- `quantum start --hot-reload` (and `--hot-reload-port`): the open pages
  reload when a component or static file is saved, CSS changes restyle
  without reloading, and a `.q` that no longer parses shows its error on the
  page (DEV-4). The watcher, the WebSocket and the page script existed, but
  no command started them.
- `random()`, `random(a, b)`, `chance(p)` and `pick(list)` in expressions
  (EXPR-15).
- The HTML a `.q` accepts is a rule (PARSE-4): boolean attributes, a bare
  `&`, void elements left open, `<` inside a quoted attribute value and named
  HTML entities.

- CI checks the game projects (snake, tictactoe, kenney-platformer)
  build to valid JavaScript, serve their game and are committed up to date
  (Laboratory job).

#### Breaking

- Laboratory (2D game engine and Godot codegen): the game names are neutral.
  A game now writes `death-sequence="classic"`, calls `game.setPatrolAI`, and
  uses the Godot codegen's tags `item_block` and `bonus_coin`, its HUD counter
  `bonus_coins`, its sound trigger `player-died` and its event
  `item-block-hit`; the world map moves the sprite `id="player"`. The 0.22
  names for these are no longer accepted. Behaviour is otherwise the same; the
  games in the repository were migrated and rebuilt.
- Admin: `GET /datasources/{id}/logs` answers failures with an HTTP status and
  a `detail` instead of 200 and an `error` key: 404 for an unknown datasource or
  a container that no longer exists, 409 for a datasource with no container,
  503 when Docker is not available or does not answer. `?tail=` is unchanged;
  the datasource logs dialog reads the status.
- `d['missing']` on an object without that key is an error that names the key
  and suggests a similar one, as `d.missing` already was (EXPR-16, was G19);
  it used to be `null`, so a misspelt key rendered nothing. Read an optional
  key with `get(d, 'key', default)` or test it with `'key' in d`.
- `skip_rows` on `q:data` skips the first lines of the file, before the header,
  as the name says; it used to read the first line as the header and then drop
  data rows (DATA-1).
- Attributes that were accepted and did nothing are parse errors that say so
  (PARSE-3): `model` on `q:knowledge` (the model is chosen on `q:llm`, IA-2),
  `unique` on `q:set` (use `operation="unique"`), every attribute of `q:column`
  but `name` and `type` (`required`, `default`, `validate`, `pattern`, `min`,
  `max`, `minlength`, `maxlength`, `range`, `enum`; filter rows with
  `q:transform`), and `q:flash` outside a `q:action` (ACT-3).
- `in` compares like `==` (EXPR-14): `'5' in [5]` and `5 in ['5']` are true
  — a value from a form now finds its number in a list. `in` on something that
  is not a list, an object or a text is an error.
- `q:set` without `type` keeps the type of a value that is exactly one
  expression, like `q:return` and props (SET-5): `value="{[1, 2]}"` stores the
  list, `value="{len(x)}"` the number, `value="{dateAdd('h', 8)}"` the date.
  It used to store text, so `len()` counted characters and `{n + 1}` on a
  stored number failed. Text with several parts (`"{n} items"`) and literals
  (`"007"`) are still text. To keep the old behaviour, write `type="string"`
  — the blog's and the admin's login pages now do, for the session's expiry.
- A value outside an attribute's list is a parse error with the line
  (PARSE-5): `q:set` `type`, `operation`, `scope` and `validate` (`date`,
  `datetime`, `struct` and `null` were accepted as `q:set` types and did
  nothing); `q:loop` `type`;
  `q:param` `type` (inside `q:query` only the types the query understands —
  `number` there is now reported where it is written, it failed when the query
  ran); `q:invoke` `method` and `authType`. An unknown `authType` used to send
  the request with no credentials; an unknown form-field type was plain text.
- `q:loop items=` over something that is not a list is an error (LOOP-6), in
  a statement and in markup, like a `ui:table` source: `items="{5}"` looped
  once over `"5"`, and in markup a missing value drew zero rows. Give a value
  that may not exist yet a list first: `<q:set name="session.cart"
  type="array" value="{session.cart}" default="[]"/>`.
- `q:invoke responseFormat="json"` on a response that is not JSON is a
  failure (INV-2), with the Content-Type and the start of the body; it used to
  succeed with `{"error", "text"}` as the value.

#### Removed

- `quantum deploy` and `quantum apps`: they talked to a deploy service that was
  never published, so for anyone else they could only fail. Serve an app with
  `quantum start` behind your own server (`DEPLOYMENT.md`).
- The examples built on third-party game art that cannot be redistributed; the
  games that remain use the Kenney assets (CC0).
- The Codecov upload from CI: it needed a repository token and was failing
  (429) without one; the coverage floor is enforced in CI by
  `coverage report --fail-under`.
- The admin's deploy feature, which lived only in the legacy FastAPI backend
  (`quantum_admin/backend`; the `.q` admin that ships never had it) and deployed
  nothing real: DeployService, the deploy pipeline with versions and rollback,
  the per-project CI/CD retry, auto-deploy on a webhook push, the cloud
  integrations (AWS, Kubernetes, Azure, GCP), the deploy-only environment fields
  and the deploy screens. The generic Docker features for datasources stay;
  webhooks still record events; a `global.yaml` with a `deployment:` block and
  an admin database with deploy columns still load.
- `projects/quantum-landing`: a marketing page that promised what does not
  ship (version 1.0.0, one-command deploy, the game engine as a feature) and
  linked to demos that no longer exist.
- `projects/llm-demo`: an LLM chat superseded by `projects/docs-assistant`;
  its script inserted the server's reply into the page with `innerHTML`
  (XSS).
- `projects/quantum-rag`: a RAG demo over a stale copy of the guide,
  superseded by `projects/docs-assistant`.
- `projects/quantum-fighter`: only a prebuilt `game.html`, with no `.q`
  source to build it from.
- `projects/quantum-tower` and its copy `examples/tower_defense.q`: the game
  called runtime functions that do not
  exist (`scheduleOnce`, `createSprite`, `attachBehavior`, `removeClickable`,
  `clickedSprite`), so no wave came and no tower could be built, and eight of
  its images and sounds were never committed.

#### Fixed

- The admin's pinned stack is current: fastapi 0.109 (January 2024) -> 0.141,
  with starlette 1.x, pydantic 2.13, pydantic-settings 2.15, uvicorn 0.53,
  httpx 0.28 and websockets 16 (uvicorn's `standard` extra needs >= 13). CI
  had been testing a different admin than the one developers run. Starlette
  1.x's TestClient uses `httpx2` (pinned alongside; the admin itself still
  calls `httpx`), and the pytest filter for the old Starlette's anyio
  deprecation is gone: 0 warnings without it.
- `quantum console`: after a pause in a search-as-you-type field, the redrawn
  field got the focus with its text selected, so the next key replaced what
  had been typed ("b", pause, "a" searched "a"). It keeps the text, with the
  cursor at the end (UI-12). The console tests wait for the search of what
  was typed, not for a page load; the browser test waits for the URL of the
  whole text.
- The editor schemas offer the values the parser accepts: `q:param type`
  listed `datetime` for every param (only a `q:query`'s takes it) and lacked
  `time`, `q:invoke method` lacked `HEAD`/`OPTIONS`, and `validate` did not
  say a regular expression starting with `^` is accepted (it was an enum, so
  the language server flagged one). `test_editor_schemas.py` compares every
  closed list the parser checks with the schema.
- In HTML content, an expression that uses a scope variable inside something
  larger — `{session.visits + 1}`, `{session.n > 0}`, `{session.user.name}` —
  rendered empty although the variable existed (it was read as the session key
  "visits + 1"); `cookie.x` could not be read inside an expression at all. It
  is read as in `q:set`, everywhere (EXPR-11).
- `q:set type=` `int`, `long`, `numeric`, `float`, `double` and `text` — the
  names `q:param` accepts — convert like `integer`, `number`, `decimal` and
  `string`; they were accepted and converted nothing (`type="int"` stored the
  text "7") (ERR-1).
- The test suite no longer writes into the repository. It left
  `test_data/quantum_test.db`, `quantum_jobs.db`, `logs/`, `.quantum/knowledge`
  and page bundles in `static/` in the checkout; each writer now uses a
  temporary folder, and the root `conftest.py` fails the run, naming the files,
  when a test writes into the repository (`git status`, ignored files included,
  before and after).
- The job threads of `q:job`, `q:schedule` and `q:thread` are the process's and
  stop when asked. The server builds a service container per request, and
  each built its own job executor: every request to a page with `q:job`
  started one more queue worker, and every request with `q:schedule` one more
  scheduler running the same schedule again, none of them ever stopped. The
  executor is now shared per job database; its workers wait on a stop signal
  instead of sleeping, `stop_workers()`/`shutdown()` join them (a job in
  progress finishes first), and they are shut down when the process exits.
- `components/bank_transfer_demo.q` never ran (it queried a `default`
  datasource with tables nobody created, and read `flash` before it existed)
  and moved money wrongly: an overdraft or a transfer to an account that does
  not exist debited one side and credited nobody. It is now
  `projects/bank-transfer`, the proof app for `q:transaction` (DB-4): a SQLite
  config, a migration with three accounts and a `CHECK (balance >= 0)`, both
  accounts checked before the transaction, and a `quantum test` suite in CI.
- `tests/apps/test_ui_parity_script.py` failed now and then under `-n auto`: a
  pilot's pause could return while a button's Pressed message was still
  bubbling to the app, so the test read the page before the click's page load
  had started (measured: 1 click in 40). `quantum console` counts finished page
  loads (`pages_loaded`), and the console tests wait for the load their own
  action caused (`tests/console_pilot.py`) — no sleeps, no retries.
- The editor tooling describes the language the parser accepts: quantum-lsp's
  Core and AI tags have exactly the attributes the parser reads and does not
  refuse (vscode-quantum's q:llm had no `knowledge`/`top`/`minRelevance`; the
  agent, tool and data sub-tags were missing), and both tools stop offering
  `q:persist`, `q:route`, `q:component basePath`/`health`/`metrics`/`trace` and
  the other removed attributes. vscode-quantum's Core/AI schema and grammar are
  generated from quantum-lsp (`scripts/generate-editor-schemas.py`), its
  snippets all parse, and `tests/conformance/test_editor_schemas.py` fails when
  either drifts from the parser.
- `model=` on `q:llm`, `q:agent` and `q:team` agents takes expressions, like
  `endpoint=` and `apiKey=`; `model="{m}"` was sent to the server literally
  (IA-1).
- `range=` on a `q:action` param is checked, as on a `q:function` param
  (ACT-2, FN-1).
- `encoding=` on `q:data` reads the file (or response) in that encoding; every
  file was read as UTF-8 (DATA-1).
- A tool argument the model leaves out takes its `q:param`'s `default` (IA-4).
- The PARSE-3 test checks that a field is read by the code that runs its node,
  not only that its name appears somewhere in the runtime.
- A date in the session came back shifted by the server's UTC offset (Flask
  read a date without a timezone as UTC): it comes back the same date, and
  `sessionExpiry` may be a date or ISO text (SET-5).
- The redis message broker (`MESSAGE_BROKER_TYPE=redis`, `quantum mq`) could
  not load: its module imported `message_broker` by a bare name, so asking
  for it said "requires 'redis' package" even with redis installed.
- A `q:action` read and wrote an empty application scope of its own:
  `application.x` set in an action was lost and could not be read there;
  actions share the server's application scope, as pages do (EXEC-3).
- `projects/quantum-chat` works again (every post was a 500): its forms are
  `q:action`s, its dead runtime patches and a committed session key are gone,
  and a `quantum test` suite runs in CI.
- `projects/quantum-terminal`'s download links answered 404 under
  `quantum start`.
- The error for `<q:application type="testing">` and `qtest:` tags names
  `quantum test` as available; it said "coming in a later release" (APP-2).
- `quantum start` with hot reload: stopping the reload server no longer
  leaves its event loop and sockets behind ("RuntimeError: Event loop is
  closed" printed later); it uses the current websockets API.
- Reconfiguring logging closes the previous log files instead of leaking
  them; the websocket transport closes its event loop on shutdown.
- Admin: no deprecation warnings (datetime.utcnow, Pydantic class Config,
  FastAPI on_event); an unreachable duplicate GET /datasources/{id}/logs route
  was removed; the deploy health check and the project server start/stop no
  longer leak a connection or a child process.
- `services:` modules are no longer re-executed when the registry is
  reloaded; their classes stay the same objects.
- Dates bound to SQLite use explicit adapters (the same ISO text), instead of
  the default ones Python 3.12 deprecated.
- The test suite runs with no warnings and no flaky failures (17 runs in a
  row, shuffled): a test left pytest's own PID where `quantum stop` would kill
  it.
- A persisted `q:knowledge` base is stored in the working directory it is
  indexed from (IA-2). The default `./.quantum/knowledge` was handed to
  ChromaDB as a relative path, which it keys one store per process by, so a
  process that indexed bases from two directories wrote both to the first
  (and failed with "Failed to get segments" once it was gone — a flaky CI
  test). In one component, a `persist="false"` base no longer made the bases
  after it in-memory too.
- `quantum stop` no longer kills a process it did not start (RUN-3): a stale
  `.quantum.pid` whose PID the system had given to another program made it
  kill that program. The file records each process's start time, and a PID
  whose process started at another time is left alone (the stale file is
  removed, exit 1). A `.quantum.pid` written by 0.22 or earlier has no start
  time: stop refuses it once, and the server is stopped by hand.

#### Documented

- The docs build fails on a link to a page that does not exist
  (`ignoreDeadLinks: false`), and CI builds the docs on every push and pull
  request, not only when publishing them.
- The Hot Reload page described `quantum dev`, configuration keys,
  environment variables and partial updates that never existed; it now
  describes `quantum start --hot-reload` as it works.
- SPEC gains LOOP-5 (loop types), SET-3 (q:set operation and scope) and SET-4
  (q:set validation), and extends DB-1, ACT-3 (q:flash), DATA-1, INV-1,
  FILE-1, MAIL-1 and IA-1/2/4 — behaviour that already existed; every rule is
  exercised by a test that cites it.
- Every Core and AI tag has a checked example in the guide; the guide explains
  using one component inside another (q:import, props, q:slot).

## 0.22.0

### Added

- **`quantum test`** runs an app's `*.test.q` suites: `q:test` with
  `test:given`, `test:as`, `test:visit`, `test:submit` and `test:expect`
  (status, redirect, flash, text, error, var, queries, table, history), each
  test against a fresh SQLite database built from the migrations, in-process
  through the real server; the report points at the test line and the page
  line; exit code 1 on failure (TEST-1…TEST-4). Guide page "Testing an App".
- `*.test.q` files next to the pages are never served, and `quantum check`
  validates them (ROUTE-4).
- `projects/tarefas` and `projects/blog` have `quantum test` suites (29
  tests), run in CI.
- `q:llm knowledge=` takes `minRelevance` (0–1): chunks less relevant than it
  are not retrieved, and when none remains `found` is false and the model is
  not called. The result has `grounded`, true when the answer cites a source
  (IA-9). The docs assistant uses it: it says "The guide says nothing about
  that" instead of answering from unrelated chunks.

### Breaking

- `q:query mode="rag"` is a parse error that points to `q:llm knowledge=`,
  which cites its sources and reports `found`. `q:query` on
  `knowledge:<name>` still searches the chunks (IA-3).
- A `q:llm`, `q:agent` or `q:team` without `model=` uses
  `QUANTUM_LLM_DEFAULT_MODEL`, else `llm.model` in quantum.config.yaml; with
  neither it fails with an error that says what to configure. It used to fall
  back to `phi3`, which also shadowed the configured model. `llm.default_model`
  is still read (IA-1).
- A slice with a step (`{xs[::-1]}`, `{xs[0:10:2]}`) is an error (EXPR-13).
  The step was silently ignored: `[1, 2, 3][::-1]` returned `[1, 2, 3]`.

### Removed

- **Breaking:** the `qtest:` testing engine and `<q:application
  type="testing">` (decision D-T1). It compiled to a pytest + Playwright file,
  addressed CSS selectors instead of actions and queries, and never ran end to
  end. Removed with it: `quantum/core/features/testing_engine/`,
  `quantum/runtime/testing_code_generator.py`, `testing_builder.py` and
  `testing_templates.py`, the three `examples/*-tests.q`, and the
  grammar/schema entries in quantum-lsp and vscode-quantum. `type="testing"`
  and any `qtest:` tag are now a parse error that names the replacement,
  `quantum test` (APP-2).

### Fixed

- A `q:loop query="…"` over a query with no rows was a 500 ("Query not
  found") when the loop was a statement of the page; it runs zero times
  (LOOP-4).
- `install.py --check` probed write access with a file of a fixed name, so two
  checks at once removed each other's probe and failed; the suite hit it now
  and then under pytest-xdist.

### Documented

- A `type="query"` knowledge source is shared by every user of the app; there
  is no per-user filter yet (IA-8).

## 0.21.0

### Added

- **projects/helpdesk**: tickets with an attachment and e-mail to the support
  team and the requester — in the browser and in the console.
- `q:file action="send"` (FILE-2): a page answers with an uploaded file as a
  download, and decides who may have it. Uploads are never static files.
- `<ui:input rows="6">`, a multi-line field (UI-14). A form whose action takes
  a file posts multipart and draws a file input with the param's `accept`.
- `mail:` in quantum.config.yaml (MAIL-1); `host: log` writes messages to the
  log in development. `q:mail name=` and `onerror="continue"` (MAIL-2).
- `quantum check` also checks the SQL in `q:agent` tools.
- "Why Quantum" page (A6), with its example tested; the docs home no longer
  promises mobile apps or "40+ components".

### Breaking

- `q:mail` sends through `mail:` in the config, and is an error without it. It
  read `SMTP_*` variables and, unless `EMAIL_MOCK=false` was set, printed
  "[MOCK] Email sent" and reported success — no application ever sent mail by
  default. Use `${SMTP_HOST}` etc. in the config (CFG-1).
- A message the server refuses stops the page or action (MAIL-2); it used to
  be an unhandled error too, but some recipients refused was reported as sent.
- The result of `q:mail` is `<name>_result` (`mail_result` by default), not
  `_mail_result`.
- `q:param maxSize=` is a parse error (the attribute is `maxsize`), and so is
  a `maxsize` that is not a size. `q:file action=` other than upload, delete or
  send is a parse error.
- The upload result no longer has `url`: it pointed to `/uploads/...`, which
  was never served.

### Changed

- **The repository is in English** (EN): `SPEC.md` (rule IDs unchanged), the
  tests, the framework code, its messages and comments. Log and error texts
  that were Portuguese now read in English.
- **Support tiers** (`SUPPORT_TIERS.md`, rewritten for 1.0): the tiers are
  Core, AI, Experimental and Laboratory. `q:file`, `q:mail` and
  `q:transaction` move to Core (SPEC rules, tests and an app in CI);
  `q:team` moves to Experimental (no rule, no proving app) and now warns once
  when used. The pytest markers are `laboratory` and `isolated` (were
  `laboratorio` and `isolado`).
- The console's screen widget is `#page` (was `#tela`).
- The wheel no longer ships the old FastAPI admin (`quantum_admin/backend`,
  ~2.6 MB with its 600 KB `main.py`). The library the `.q` admin uses moved to
  `quantum_admin.core`; `quantum admin` is unchanged. The backend stays in the
  repository (A4.2).
- `quantum/runtime/web_server.py` (2150 lines) is split by concern:
  `web_config` (reading the config), `web_html` (asset extraction, htmx, hot
  reload), `web_errors` (welcome and error pages), `web_lifecycle` (start,
  banner, PID, signals). `QuantumWebServer`, `create_app`, `start_server`,
  `ConfigError` and `_validate_config` are imported from where they were.

### Removed

- `quantum/cli/commands` (`new`, `dev`, `build`, `serve`, `test`, `lint`,
  `docs`): a click CLI that the `quantum` command never wired, listed in the
  CLI docs as "future commands". The migration runner it held is now
  `quantum.cli.migrations` (`quantum migrate` is unchanged).

### Fixed

- `q:transaction` failed validation on every run (`quantum run`: "Invalid
  isolation level: "): the parser passed the datasource where the node expected
  the isolation level, and kept the level where nothing read it. An explicit
  `datasource=` never reached the executor. An unknown `isolationLevel` is now
  a parse error (DB-4).
- `quantum run` refused `<ui:alert variant="{...}">` (and a bound `variant` or
  `position` on `ui:toast`/`ui:skeleton`) as an invalid literal; the page
  resolves it when it renders (UI-1).
- `q:param maxsize` was parsed and never checked: any size was accepted.
- `q:file action="upload"` without `destination` failed with "empty file path";
  it saves under `paths.uploads`.
- `<ui:form submit="...">` with fields of its own drew no button.
- `<ui:table source="{rows}">` without `ui:column` drew every row empty; it
  shows one column per field (UI-5).
- Sending mail looked up the machine's full name on every message
  (`socket.getfqdn`): 12 s for the first message on a Windows machine.
- The test suite's admin database was shared by every pytest-xdist worker,
  which failed now and then with "table ... already exists".

## 0.20.0

### Added

- **A failure contract for AI** (IA-5). `onerror="continue"` on `q:llm`,
  `q:knowledge` and `q:query` (any datasource) lets a page handle a failure:
  `<name>_result.success` is false and `error.message` says why — an
  assistant page can say "unavailable" instead of answering 500.
- **Answers that cite their sources** (M5, IA-6). `q:llm knowledge="docs"`
  retrieves the top chunks of a knowledge base, asks the model to answer only
  from them citing `[n]`, and exposes `sources` and `cited` in
  `<name>_result`. With nothing retrieved the model is not called
  (`found: false`) — no uncited answer from memory.
- **Answers that arrive as they are written** (M5, IA-7). `q:llm
  stream="true"` renders the page at once; `<ui:stream for="answer">` shows
  the answer as the model writes it, in the browser (the framework's script,
  no JavaScript to write) and in the console. One-time tokens bound to the
  session; a failure halfway is shown as an error.
- **`urlencode(v)`** in expressions (EXPR-12), for values put in a URL.
- **projects/shop-agent**: a `q:agent` answering questions about a shop's
  SQLite database through read-only query tools; the page lists every call.
- `onerror="continue"` on `q:agent` (IA-5), and `call` in each of
  `<name>_result.actions`: the call written out, `low_stock(below=5)`.
- **projects/docs-assistant**: ask the Quantum guide; the answer is grounded in
  `docs/guide`, cites its pages and streams. It says so when the model server
  or the index is unavailable.

### Breaking

- A `q:knowledge` source that cannot be read (missing file or folder, no file
  matching the pattern, a failing query) is an error; it used to be a log
  warning and the base was built from fewer documents (IA-8).
- `q:source type="url"` (it read nothing) and unknown source types are parse
  errors (IA-8).
- A `q:agent` that does not finish stops the page, like `q:llm` (IA-5); it
  used to leave `success: false` and an empty answer on a page that went on.
  `onerror="continue"` keeps the old behaviour.
- A `q:agent`'s `timeout` (milliseconds, 60000 by default) is now the whole
  run's budget: each model call gets what is left. Before, every call waited
  60 s whatever `timeout` said. An agent on a slow local model may need a
  larger `timeout`.
- `q:agent max_iterations=` is a parse error: the attribute is `maxIterations`.
  The guide and the README wrote `max_iterations`, which was never read.
- Inside a `q:if`, a `q:else`/`q:elseif` right after an inner `</q:if>` is a
  parse error (IF-4): it belonged to the outer `q:if`, not the one it follows.
  `examples/message-queue-example.q` had exactly this bug.

### Fixed

- `q:llm timeout=` was read and never used: every request waited 60 seconds
  (and `stream="true"` too). It is honoured now, and a `q:agent`'s `timeout`
  reaches its model calls.
- A RAG query on a knowledge base that failed to build answered "Knowledge
  base is still loading. Please refresh the page." with `success: true`; it is
  an error with the real reason now.

### Changed

- `q:llm`'s `<name>_result.error` is `{message: ...}`, as `q:invoke`'s.

## 0.19.0

### Added

- **Declarative schema** (M6, DB-10). Keep a `schema.sql` with the tables as
  they should be; `quantum migrate plan` shows what changes against the
  migrations (new tables and columns, rebuilds that keep the rows, indexes),
  marks what loses data, and `--write NAME` saves the migration and its
  rollback after asking. Plans that lose data need `--allow-data-loss`.
  SQLite for now.
- **Change history** (M22, DB-11). `history: true` on a datasource records every
  write an action makes — who, when, which action, the row before and after —
  in the same transaction; `<ui:history table key datasource>` lists a row's
  history in the browser and the console. `projects/tarefas` shows it on the
  edit page.

## 0.18.0

### Added

- **Forms that know the action's rules** (M1, UI-9). A `<ui:form on-submit>`
  takes each field's `required`, `minlength`, `maxlength`, `min`, `max`, type
  and anchored `pattern` from the action's `q:param`s, and a select's options
  from its `enum`; the browser checks them before posting. When the server's
  validation fails, the form comes back with the values sent (never a
  password) and each error next to its field, in the browser and the console.
  An attribute on the field wins; `rules="off"` turns it off.
  `examples/form-rules.q`.

- **Forms from a table** (M17, UI-10). `<q:action table="posts"
  datasource="db">` takes its params from the table's schema: NOT NULL →
  required, `CHECK … IN` → enum, `VARCHAR(n)` → maxlength, the column type,
  nullable columns as `None`, and foreign keys that must name an existing row.
  A `<ui:form>` with no fields of its own draws one per column (select for an
  enum or a foreign key, checkbox for a boolean) and `values="{row}"` opens it
  as an edit form. `projects/tarefas` gained an edit page built this way.
  `quantum check` verifies the action's table and columns.
- **Pagination in a tag** (M14, UI-11). `<ui:pager for="query">` draws
  previous, the page numbers (with gaps) and next over a paginated query,
  keeping the other URL parameters, in the browser and the console.
  `projects/blog` dropped its hand-made pagination (a count query, LIMIT /
  OFFSET, URL building) for it.
- **Search as you type** (M15, UI-12). `<ui:input bind="q" search="results">`
  refreshes the element `#results` after each pause in typing, through htmx
  and the page's own queries, with the search in the URL; a plain GET form
  underneath, so Enter works without JavaScript; the same in the console.
  `projects/blog`'s search page uses it.
- **A table that sorts and edits itself** (M16, UI-13). `<ui:table
  sort="true">` turns headers into links that order the query in SQL
  (`q:query sortable="true"`, before pagination); `<ui:table edit="table"
  datasource="db">` makes each shown column an in-cell form posting to a
  generated action that edits only what the page declares, runs the page's
  guards, validates with the column's schema rules and updates one row by its
  key — shown in `/_dev`. In the console too. `projects/tarefas` has
  `/planilha`.

### Changed

- A failed action validation checks **every** field, not only the first; the
  flash is still the first error.

### Fixed

- `projects/blog`: `/search` with no `?q=` answered 500 (`{trim(query.q)}`
  fails when the URL has no parameters).
- `page=` on a paginated `q:query` was read as a number when the file was
  parsed, so `page="{query.page}"` was always page 1: a page could not move
  through pages at all. It is an expression now, and defaults to the URL's
  `?page=`; an invalid value is page 1 (DB-9).
- A page that failed while rendering answered 500 **without logging
  anything** in production; the error is now in the server log.

## 0.17.0

### Added

- **The `/_dev` panel** (M12, DEV-1). With `server.debug: true`, `/_dev` shows
  the last requests: the component, the action, every query with parameters,
  rows and time (or the database's error), the variables of the action or page
  and of `session` / `application`, the redirect and the flash. Off with
  `debug: false`, and only for requests from the machine itself. `quantum
  start` prints its address.
- **Errors point to the line** (M2, DEV-2). Parse errors say `at line N` —
  everywhere, not only on the page. In debug mode the error page shows the
  `.q` lines around the failing one, marked: the innermost statement or
  element that failed, in the called component's own file when the error is
  inside one; it links the SPEC rules the message cites. Key messages now cite
  their rule (`PARSE-1`, `PARSE-2`, `AUTH-6`, `ACT-9`, `UI-1`, `UI-5`).
- **`quantum check`** (M8, DEV-3): every page parses, every `q:query` compiles
  against the database (EXPLAIN, read-only, nothing runs), and every
  `{query.field}` a page reads — directly, through a loop, a `ui:table` /
  `ui:list` or a `<ui:column key>` — is a column the query returns. Reports
  `file:line: message`; exits 1 on a problem. SQLite for now. The schema
  reader behind it (tables, NOT NULL, defaults, CHECK … IN, foreign keys) is
  the one the declarative schema (M6) and forms from a table (M17) will use.
- **Reloading keeps the session** (DEV-2): in debug mode, without a configured
  `secret_key`, the session key lives in `.quantum/dev-secret-key`; every save
  used to log everyone out.

### Fixed

- **Error pages did not escape** their title, message and details: an error
  message carrying a request value (a query parameter) was written into the
  page as HTML.
- The debug error page showed generic XML hints ("Check your XML syntax") for
  errors that had nothing to do with XML syntax.

## 0.16.0

### Added

- **`quantum desktop`** (UI-4): the application in a desktop window. It
  starts the application's server on a free local port and opens a native
  window (pywebview) on it — the same pages, actions and session as the web,
  with no logic translated. `quantum desktop /some/page --width 800` opens a
  given page and size. Needs the new extra:
  `pip install "quantum-framework[desktop]"`; without it the command says so.
- **Tables and lists from data** (UI-5): `<ui:table source="{rows}">` draws one
  row per record — `<ui:column key="name">` shows a field, a column with
  content draws it per row (`<ui:button on-click="delete" with="id={row.id}">`)
  — and `<ui:list source="{items}" as="item">` repeats its content. Until now
  a table's body was empty and **the whole data source was written into the
  page as an HTML comment**; a list showed `{item.x}` raw. A source that is not
  a list, or a column key the row lacks, is an error.
- **Form fields open with a value** (UI-6): `value=` on `ui:input`,
  `ui:select`, `ui:radio`; `checked=` on `ui:checkbox`, `ui:switch`. Edit
  forms were not possible.
- **The core set of `ui:*`** (UI-7): 37 elements drawn with the same meaning in
  the browser, the console and the desktop, checked by one script run in a
  real browser and in the console (`tests/apps/test_ui_paridade.py`). The
  console now draws grids, tabs, cards, tables, lists, checkboxes, switches,
  radios, progress bars and images; for a tag outside the set it says it
  cannot draw it, instead of drawing something else.

- Guide: **One App, Many Screens** (`docs/guide/ui.md`), every screen in it
  served by a test and checked in the browser's text and the console's.
- Guide: **How a Page Runs** (`docs/guide/how-a-page-runs.md`) and SPEC
  section `EXEC-`: the order of a GET and of a POST, and how long a page
  variable, `flash`, `session.x` and `application.x` live (`application.x` is
  per server process: gone on restart, not shared between gunicorn workers).
  The errors for a statement inside markup (PARSE-2), a page variable read in
  an action (ACT-9) and a guard that reads the page (AUTH-6) link to it.
- CI: the Laboratório tests (games, Godot, React Native) run in a job of their
  own, still required.

### Breaking

- **`quantum run --target desktop` was removed** (UI-8). It generated a
  pywebview app with a JavaScript bridge that translated `q:set` and
  `q:function` on its own — a second implementation of the language. Use
  `quantum desktop`, which opens the same pages in a window.
- **Standalone UI builds are layout only** (UI-8): a `q:set`, `q:function` or
  any command inside `<q:application type="ui">` built with `--target html` or
  `--target textual` is an error. It used to be dropped without a word
  (`{count}` came out raw; buttons called functions that did not exist).
  Write screens as pages.
- **Browser state persistence was removed** (SET-2): `persist`, `persistKey`,
  `persistTtl`, `persistEncrypt` on `q:set`, and the `q:persist` tag. They only
  did anything in the standalone HTML build, and nothing in a page; they are
  now errors that say to use `session.x` or the database.
- `--target mobile` (React Native) is **Laboratório**: it warns once.

### Changed

- A page's title is the same in the browser, the console and the desktop
  window: the first `ui:window`'s `title`, else the component's name (UI-4).
  Pages served in HTML used to be titled `<path> - Quantum`.
- In a page, `ui:section` is a titled group, always open (it was a collapsed
  `<details>`: its content was hidden in the browser); a `ui:card`'s `title`
  shows next to a `ui:card-header` too.

### Fixed

- `examples/python-data-processing.q` used `<ui:code>`, which never existed,
  and `examples/state_persistence_demo.q` used `<ui:form-item>`; neither page
  opened. The first is fixed; the second is removed with the feature it showed.
  `examples/dashboard-ui.q` is now a page; `examples/task-manager-desktop.q`
  (the desktop bridge's demo) is removed.
- `docs/tools/cli.md` told to run `python src/cli/runner.py`, a path that no
  longer exists.

- Text directly inside a `ui:*` container vanished:
  `<ui:card-header>Summary</ui:card-header>` came out empty (UI-1).

## 0.15.0

### Added

- **`ui:*` inside pages** (UI-1). The UI Engine's elements — `ui:window`,
  `ui:vbox`, `ui:panel`, `ui:button`, `ui:form`… — can be used in any page
  served by `quantum start`, next to plain HTML, `q:loop`, `q:if` and the
  page's queries. The page's runtime does the logic; `{expressions}` are
  resolved by it and escaped. Events are the page's actions:
  `<ui:button on-click="save" with="id={row.id}">` posts to
  `<q:action name="save">` with the field `id`, and
  `<ui:form on-submit="create">` posts its fields. An event that names no
  action, or a `ui:` tag that does not exist, is an error with a suggestion.
  Until now `ui:*` only compiled from `<q:application type="ui">`, and inside
  a page it came out as `<window>`/`<vbox>` tags.
- A statement inside `ui:*` markup is a parse error, as inside HTML (PARSE-2).
- **Responsive layout, declared** (UI-2): `stack-below="md"` on `ui:hbox`,
  `hide-below` / `hide-above`, `grow="true"`, and
  `<ui:grid columns="1 sm:2 lg:3">`, with breakpoints `sm` (640 px), `md`
  (768 px) and `lg` (1024 px). The UI Engine's HTML had no media query at all:
  a 280 px sidebar made the page overflow on a phone.
- **`quantum console`** (UI-3): the application's pages in the terminal. It
  starts the application's server and draws each page with Textual from its
  view tree (`Accept: application/vnd.quantum.view+json`); buttons and forms
  send the page's actions, so login, validation and flash are the web's.
  `stack-below` counts terminal columns. The same `.q` is a web page and a
  console app, with no logic translated.
- `projects/tarefas`: a task app written in `ui:*` over SQLite, tested end to
  end in CI — the UI Engine's proof app — including in a real browser at
  1280 and 390 px (Playwright + Chromium, installed in CI) — and in the
  console, with the same script.

### Fixed

- `quantum migrate` reads migration files as UTF-8 on every system (DB-8). On
  Windows it used the system code page, and "página" was stored as
  "pÃ¡gina". The same for the other files the CLI reads.

## 0.14.0

### Fixed

- A `q:function` of the page can be called inside a `q:action` (ACT-10). It
  was a 500 every time: actions ran in one runtime shared by every request
  and thread, which never registered the page's functions. Each request now
  gets its own runtime, so simultaneous requests cannot see each other's
  state either.
- `ui:*` elements inside a served page are an error that says they are not
  supported there yet (UI-0); they came out as `<window>`/`<vbox>` tags no
  browser lays out. Building a UI from a file that is not
  `<q:application type="ui">` says how to fix it instead of raising
  `AttributeError`. The console and desktop targets write different files
  (`<id>_console.py`, `<id>_desktop.py`); they both wrote `<id>.py`, so one
  erased the other.

- `accept` on a `q:param type="file"` restricts the upload (ACT-11): it was
  accepted and never checked, so any file passed. The file name has to match
  as well as the type the browser declares — an `.exe` sent as `image/png` is
  refused.
- `returnType` on `q:function` is checked on every return (FN-4); it was
  accepted and never read.

- `logging.format` sets the format of log lines, and `paths.migrations` the
  folder `quantum migrate` reads (CFG-3); both were documented and ignored.
  Unknown keys under `server`, `paths` and `logging` are named in a warning,
  as they already were under `security` and `performance`.

### Breaking

- Attributes that were accepted and never did anything are parse errors
  (PARSE-3): `mask` on `q:set`, `transform` on `q:invoke`, `validation` on
  `q:param`, `basePath`, `health`, `metrics` and `trace` on `q:component`. A
  test now scans the Core's AST nodes and fails when a field set from the XML
  is not read by anything that executes.
- A `q:function` whose value does not match its `returnType` is an error;
  an unknown `returnType` is a parse error (FN-4).

### Changed

- The test suite runs in parallel in CI (`pytest -n auto`); `pytest-xdist` is in
  the `[dev]` extra. Tests that cannot share the machine are marked `isolado`.

## 0.13.0

### Security

- **A guard written by hand protected nothing.** `<q:if condition="not
  session.authenticated"><q:redirect url="/login"/></q:if>` at the top of a
  page did not redirect (the GET served the page) and did not stop the page's
  `q:action` (the POST ran it without a session). Three causes, all fixed:
  `q:redirect` outside an action was skipped silently (ACT-7); an action never
  ran the page's statements, so no check at the top could stop it — guards
  now run before each action (AUTH-6); and `not session.authenticated` was
  *false* for a visitor with no session, because a missing key made the whole
  condition false (EXPR-8).
- `<q:action require_auth="true">` was parsed and never checked: the action
  ran for anyone. It is now a parse error, with `csrf=` and `rate_limit=`,
  which were not enforced either (AUTH-7).
- `security.max_content_length` never reached Flask, so request bodies —
  uploads — had no size limit. Over the limit (16 MB by default) the answer is
  `413` (CFG-2).

### Fixed

- A `q:if` inside a `q:loop` inside a `q:action` did not see the loop
  variable, and a loop's `from`/`to`/`items` were read from the wrong context
  (ACT-8).
- Keys in `security:` or `performance:` that nothing implements
  (`csrf_protection`, `rate_limiting`, `cors_*`…) are named in a warning when
  the config loads (CFG-2).

- `round()` rounds halves away from zero — `round(2.5)` is 3 and
  `round(0.125, 2)` is 0.13; it was Python's banker's rounding over binary
  floats (2 and 0.12). `ceil()` and `floor()` are new (EXPR-9).
- A JavaScript habit in an expression (`Math.ceil`, `Date.now()`,
  `text.split(' ')`, `parseInt`) names the function to use instead
  (EXPR-10).
- A SQLite `database` that does not exist is an error that points to
  `quantum migrate up`; it used to be created empty, so the page failed later
  with "no such table" (DB-7). A datasource key nothing reads (`sqlite_path`,
  `pool_size`) is named in a warning.
- An error inside a `q:action` about a missing variable says why: an action
  does not run the page's statements (ACT-9).
- Error pages no longer suggest `quantum inspect`, which does not exist.

- Text written directly in a `q:if` / `q:else` branch is rendered (IF-3):
  `<h2><q:if condition="tag">Posts tagged {tag}</q:if><q:else>All</q:else></h2>`
  rendered an empty heading.
- `quantum migrate` runs migration files with more than one statement, and
  applies each file in one transaction: SQLite accepted one statement per
  file ("You can only execute one statement at a time"), so a table and its
  index could not be in the same migration (DB-8).
- `slugify(text)` makes a URL segment from a title (EXPR-9).
- `projects/blog` works end to end and is tested in CI (`tests/apps`): home
  with tag filter and pages, posts with comments, search, and an admin to
  create, edit, publish and delete posts. It had failed on every page. Its
  SQL was PostgreSQL-only while its database was SQLite, it seeded an admin
  whose password nobody knew, and it protected the admin with a hand-written
  guard that did not protect it. The first visit to `/login` now creates the
  admin account; there is no default password.
- `projects/quantum-dashboard` works end to end and is tested in CI: create
  (validated), finish, reopen and delete tasks with `q:action`, filter by
  status. It handled POSTs with a `q:if` at the top of the page, so there was
  no validation and reloading repeated the operation; its database lived in
  `/app/data`; and it started through a `startup.py` that patched the
  framework at run time with imports from the old `src/` layout. Those
  deployment files are gone.
### Breaking

- In a `condition`, a key a scope does not have (`session.x`, `query.x`…) is
  `None` (EXPR-8): `not session.x` is now true when `x` is missing.
- A guard that reads a variable the page sets, on a page with actions, is a
  parse error; a guard condition that cannot be evaluated is an error instead
  of false (AUTH-6).
- `q:redirect` outside an action now redirects.
- `q:action` refuses `require_auth`, `csrf` and `rate_limit` (AUTH-7).
- A datasource that is not in `quantum.config.yaml` is an error. The engine
  used to ask the old admin API on `localhost:8000` for it (DB-7).
- Session, application and request values are read only with their prefix —
  `session.role`, `request.path`. They were also copied in as bare names, so
  `{role}` or `{path}` silently read them (EXPR-11).
- `<q:html>`, `<q:div>` and other HTML element names with the `q:` prefix are a
  parse error (PARSE-1); they were read as the HTML element.

## 0.12.0

### Added

- **`quantum admin`**, with the new `[admin]` extra
  (`pip install "quantum-framework[admin]"`): starts the Quantum Admin — its
  `.q` screens and services now ship in the wheel. Data goes to
  `./.quantum-admin` (`--data`), application paths are relative to the current
  folder (`--root`), it listens on 127.0.0.1:8090. Session keys are kept in the
  data folder, so a restart does not sign everyone out. See *Quantum Admin* in
  the guide.
- **Declared services** (SVC-1..3): a Python function registered with
  `@service("name")`, in a module listed under `services:` in
  `quantum.config.yaml`, is called from a page with
  `<q:invoke name="x" service="name">`. `q:invoke service=` had been parsed
  since the first version and failed with "Unsupported invocation type".
  See the new guide page *Declared Services*.
- `login_url` (AUTH-4): where `require_auth` sends a visitor without a
  session — `security.login_url` in `quantum.config.yaml`, or `login_url=` on
  the component. It was always `/login`. Only local paths are accepted.
- Route segments inside `q:action` (ROUTE-2): a POST to
  `components/app/[name].q` has `name` in the action, as the page render
  does; a form field with the same name does not replace it. `[...path]`
  catch-all segments are now documented (ROUTE-1).
- Private components (ROUTE-3): a file or folder under `components/` whose name
  starts with `_` is not served; it exists to be imported, like a layout.

### Security

- **A layout's slot content leaked between requests.** Filling a `q:slot`
  mutated the component held in the resolver cache, so after the first request
  every later page rendered with that component showed the first page's slot
  content. Composition no longer mutates cached components (COMP-3).
- The session cookie is sent with `SameSite=Lax` and `HttpOnly` (AUTH-5), so a
  form on another site cannot post to a `q:action` with the visitor's session.

### Fixed

- Component composition (COMP-1..4): components are found under
  `paths.components` and the `from=` of `q:import` (they were searched in
  `./components` of the process's working directory); slot content is
  rendered in the page's scope, so loops and conditions over the page's data
  work inside a layout; child components run with the page's configuration
  (datasources, services); props are expressions; a missing or failing
  component is an error instead of an HTML comment on a 200 page. A child
  component sees the page's `session`, `application` and `request` scopes.
- `flash` and the `url` of `q:redirect` evaluate expressions (ACT-3):
  `flash="{result.error}"` ended the action with a 500. `flash` and
  `flashType` always exist on a rendered page (`''` without a message).
- `condition="1"`, `condition="2"` and `condition="{1}"` are true (IF-2).
  They were read as regex quantifiers and were always false in a `q:if`
  outside the markup; the same condition inside the markup was true.
- `and` / `or` short-circuit (EXPR-6): `user and user.name` failed when
  `user` did not exist, because both sides were evaluated first.

### Breaking

- `q:invoke endpoint=` is refused by the parser; it never did anything.
- The admin's screens moved from `components/admin` to
  `quantum_admin/components/admin` (and their CSS/JS from `static/` to
  `quantum_admin/assets`); `quantum start` at the repository root no longer
  serves `/admin`. Use `quantum admin --data quantum_admin` to open the
  repository's existing admin data.
- `components/_anything.q` and everything under a `_folder/` answer 404
  (ROUTE-3). Rename a page that starts with `_`.
- A component call that cannot be resolved or fails now makes the page fail.
- Inside a layout, slot content no longer sees the layout's own variables — it
  renders with the page's.
- A statement (`q:set`, `q:query`, `q:invoke`, `q:action`…) inside an HTML
  element or inside the content of a component call is a parse error
  (PARSE-2). It never ran: statements run before the page is rendered, so
  `<ul><q:set name="y" .../><li>{y}</li></ul>` printed a literal `{y}`, and a
  `q:action` inside a `<section>` was never found. Move it above the markup.
  So is a `q:set` in a `q:loop` that renders rows, when those rows read the
  value it sets: every row showed the last iteration's value. A total
  accumulated in the loop and read after it still works. The comment form of
  `projects/blog` was affected and never worked.

## 0.11.0

The release that writes the language down: `SPEC.md` states what a program
means, rule by rule, and every rule is pinned by a test that cites it.

### Breaking

- **`q:application type="html"`, `type="api"` and `type="microservices"` were
  removed** (APP-1). They never ran their routes. `q:application` without a
  `type` meant `html` and is refused too; the parse error explains how to move
  to pages in `components/` served by `quantum start`.
- **An expression that fails in a `q:` attribute is an error** that names it,
  with a suggestion when a similar name exists (EXPR-1, EXPR-2). It used to be
  left as literal text — `value="x{nada}y"` produced `"x{nada}y"`, and
  `{10 / zero}` produced its own braces. HTML content is still forgiving: an
  unresolved expression there is rendered as written and logged once (EXPR-4).
- **Arithmetic on a session/application value that is not set is an error**
  (EXPR-3). `{session.visitas + 1}` used to become `''` and fail later with
  "could not convert string to float". Reading the value alone still gives
  `''`; for counters use `operation="increment"`.
- **Only a missing name makes a `condition` false** (EXPR-5). A syntax error or
  an unknown function in a condition is now an error instead of a silent false.
- **The first top-level `q:return` ends the component** (RET-1), and a `value`
  that mixes text and expressions is always text: `"007"` stays `"007"` (RET-2).
- **A POST whose `action` field is missing or names no action is refused with
  400** on pages with more than one `q:action` (ACT-5). It used to run the first
  action.
- **`q:set` types are checked** (ERR-1). `type="number"` keeps fractions —
  `{5 / 2}` used to store `2`; `type="integer"` refuses `3.5` instead of
  truncating it; `type="boolean"` refuses anything but true/false/1/0/yes/no.
- **An unknown `q:` tag is a parse error**, with a suggestion (PARSE-1).
  `<q:sett>`, `<q:retrun>` or a tag the docs promised but never existed
  (`q:try`, `q:storedproc`, `q:fetch`, `q:include`, `q:throw`) used to be
  dropped silently, and the program ran without it.
- **`q:query` refuses `cache`, `ttl`, `reactive`, `interval`, `timeout`,
  `maxrows` and `batch`** (DB-5): they never did anything.
- **`quantum migrate` applies migrations to the datasource in
  `quantum.config.yaml`** (DB-6) — the one the pages use — chosen with
  `--datasource` when there are several. It used to read a separate `database:`
  section and, without one, try a local PostgreSQL named `quantum` before
  falling back to `./data/quantum.db`: the migrations landed in a different
  database than the app queried.
- **The `q:fetch` data-fetching feature was removed.** Its parser was never
  registered, so `q:fetch` never ran in a `.q` file; its guide page, example
  and module are gone.
- **`q:function` parameters are always converted and checked** against their
  `q:param` rules, like actions (FN-1). `validate="true"` was needed before, and
  even then `type="email"` and `min`/`max` were not checked.
- **`q:function` refuses attributes that never did anything** (FN-2): `cache`,
  `memoize`, `pure`, `async`, `retry`, `timeout`, `access`, `scope`,
  `validate`, `endpoint` and the REST attributes.
- **Arithmetic operators other than `+` need numbers** (EXPR-7): `'-' * 40`
  and `'%s' % x` are errors instead of Python's repetition and formatting. An
  attribute that is only `{3}` is the number 3, no longer the text `{3}`.
- **`default` on `q:set` applies when `value` resolves to nothing** (SET-1):
  `value="{session.clicks}" default="0"` stores `0` on the first visit instead
  of `''`.
- **`q:param type="number"` keeps whole numbers whole**: `"30"` is `30`, not
  `30.0` (`decimal` is still a float).
- **A failed `q:data` or `q:invoke` stops the component** with an error naming
  the source and the reason, like `q:query` already did (DATA-4, INV-2). They
  used to leave the variable empty and carry on. Add `onerror="continue"` to
  handle the failure through `<name>_result`, whose `error` is now always
  `{message}`.

### Fixed

- `&&` and `||` did not parse, so any condition using them was false for every
  input — including the examples in the conditionals guide (EXPR-6).
- A `q:else`/`q:elseif` written after `</q:if>` was dropped inside `q:loop`,
  `q:function`, HTML elements and most other bodies; it only worked at the top of
  a component (IF-1).
- `q:invoke url=` never worked without an explicit `timeout`, and its
  `q:param`s were sent empty (INV-1).
- `form.<field>` was empty inside `q:action` (ACT-6).
- Conversion errors in `q:set` say what to write: `value="{a} + {b}"` points to
  `{a + b}`, and JSON with single quotes asks for double quotes, instead of
  Python's "could not convert string to float" (ERR-1).
- `quantum run` printed a Python traceback for a failed `q:invoke`, and created
  `./logs/` and `./quantum_jobs.db` in the current directory for any program
  (RUN-1, RUN-2).
- `q:job` and `q:schedule` ran on two different job executors; every service now
  has one instance per runtime.
- A component's `q:function` could not be called from its HTML: `<p>{f(2)}</p>`
  rendered the literal text (FN-3).
- A `q:query` inside `q:transaction datasource="…"` had to repeat the
  datasource or the file did not parse (DB-4).
- `${NAME:default}` (with `:` only) is accepted in `quantum.config.yaml` as well
  as `${NAME:-default}`.

### Added

- `${VAR}` and `${VAR:-default}` in `quantum.config.yaml` read environment
  variables; a missing one stops startup naming the variable (CFG-1).
- `SPEC.md`, with conformance tests in `tests/conformance/`, and known gaps kept
  as strict expected failures until decided.
- The guide examples that show an **Output** are executed by the test suite;
  the expressions and conditionals pages were rewritten from what runs.

## 0.10.0

The release that narrows what Quantum promises to the core language plus AI,
and makes the documentation match what runs.

### Breaking

- **`q:application type="html"` and `type="api"` are now EXPERIMENTAL** and warn
  when run. Neither worked as documented: `type="html"` failed on start, and the
  `type="api"` server returned the literal text of the first `q:return` without
  running the route. Build web apps as pages in `components/` served by
  `quantum start`.
- **`QUANTUM_LLM_BASE_URL` now takes precedence over `llm.base_url`** in
  `quantum.config.yaml`, for every AI tag. Before, `q:llm` used the config and
  `q:agent`/`q:team` used the environment, so one program could talk to two
  model servers.
- **A failed RAG answer raises an error.** It used to be returned as the answer
  text ("Error generating answer: …").
- **Knowledge bases are stored under a new collection name** (`quantum-<name>`)
  and carry a fingerprint of their sources. Existing persisted bases are
  reindexed once, and from now on whenever their sources change.
- **The admin requires a login for every page and data route**, not just `/api`.
  Its session cookie is accepted for reads only.

### Fixed

- `q:query` inside `q:action` could not reach datasources declared in
  `quantum.config.yaml` — no form could write to a database.
- `q:compute` never added its field; `q:field` in XML imports ignored `xpath`
  and `type`; XML imports reported failure, so no transform ran on them.
- The admin served 18 data routes and 3 pages without a login, and its test
  suite wrote into the admin's real database.

### Added

- `hashPassword()` and `verifyPassword()` in expressions, for a real login
  written in `.q` ([Authentication](https://danielgregorio.github.io/quantum/guide/authentication)).
- Guide pages for Actions & Forms, Sessions & Scopes, Data Import,
  Authentication and AI, each written by running its examples.
- `tests/live_ai`: the AI tags tested against a real model server.
- `tests/conformance/test_known_gaps.py`: known gaps in the language, as tests
  that fail until each is decided.
- Laboratório tier: the game engine and the AS4 compiler stay in the repository
  with no stability promise, and warn when run.

## 0.9.1

- Package page on PyPI shows the current README and links.
- `get_memory_usage` no longer crashes on Windows without `psutil`; the admin
  no longer scans 10,000 ports one by one without it.

## 0.9.0

First public release.

- `q:return` inside `q:loop` returns the list instead of being discarded.
- `quantum stop` stops the reloader's child process too, and reports failure
  when a process survives.
