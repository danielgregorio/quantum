# Games 3 — what the game language takes from Godot and Unity next

> Status: approved 2026-10-21, whole, the ten "later" items included (each
> comes in with the game that asks for it: Phase 6). Phases 1 to 5 done
> (2026-10-21 and 22: Siege the game of the second, Crates of the third, the
> fourth in every game, Rally of the fifth); Phase 6 next, each item with
> the game that asks for it.
> Laboratory tier: no tag here carries a stability promise until it ships.
> The proposal it comes from is the Claude Docs page "Proposta: próximos
> recursos da linguagem de jogos"; the map it was chosen from is
> [GAMES_PARITY.md](GAMES_PARITY.md).

## The decision

Bring 34 features into the `qg:` language in five phases, each pulled by a
game, and ten more later, each with the game that needs it. The map against
Godot 4.4 and Unity 6 has 251 rows: 146 covered, 42 partial, 40 gaps and 23
left out by design. Of the gaps and the partial rows, a feature comes in when
it passes four tests:

1. **It serves more than one genre**, or every game that is going to ship.
2. **It has a declarative form**: a tag or an attribute, no script.
3. **It keeps determinism**: it runs in the fixed 60 Hz tick, so replays,
   tests and the lockstep stay true.
4. **A game asks for it**: each phase is pulled by a game written before its
   tags, as Bricks pulled the gaps of 2026-10-21. A tag no game uses does not
   come in.

Size: **S** fits an afternoon, **M** one or two days, **L** more, counting
the Godot test, the reference and the dataset.

Phase 1 comes first because the others use it: Siege aims with `atan2()` and
counts its waves with `qg:when`. Phases 2 to 5 may change order with what is
to ship first.

## Rules for every feature

The same as for the gaps of 2026-10-21:

- `quantum/runtime/godot/schema.py` is the one place a tag or an attribute is
  declared; the reference (`docs/targets/games.md`,
  `scripts/generate-games-reference.py`) and the editors' schemas
  (`scripts/generate-editor-schemas.py`) are regenerated from it.
- A tag the compiler does not know, or an attribute it does not use, is an
  error with the line; so is a field a thing does not have (Phase 1).
- Every tag has a line in the feature's intentions
  (`quantum/core/features/game_engine/intentions/primary.intent`) and a game
  in its positive dataset; a refusal the compiler gives goes in the negative
  one.
- Every feature has a test that runs in Godot (`tests/godot/`), and a
  networked one, if it touches what the lockstep or the rollback carries.
- The game that asks for a feature uses it, and its replay is a test.
- `CHANGELOG.md` (Unreleased) and the row in `GAMES_PARITY.md` move with it.

## Phase 1 — Game logic

No new game: these are pieces Bricks, Drift and Delve already ask for, and
the next phases use. One of them is the one hole in the language's promise
the map found: `hero.foo` compiles and only breaks in Godot.

| Feature | Proposed tag | Who uses it | Size |
|---|---|---|---|
| A delay a handler starts | `<qg:after ticks="600">…</qg:after>` and `ticks()` | a power-up that runs out, a bomb's fuse, a respawn after a pause | M |
| A handler when a condition turns true | `<qg:when condition="{count('enemy') == 0}">` | a wave won (Drift), a room solved (Keep), a level cleared (Bricks, today a function called from two places) | M |
| Fields checked at compile time | `hero.foo` is an error that lists the fields there are | every game | M |
| Functions for every scene | `q:function` straight in `q:application` | rules repeated across scenes (Delve's three crypts) | S |
| Held actions, and for how long | `pressing('run')`, `pressed_for('fire')`, `strength('right')` | a charged shot, a run button, analog speed | S |
| Aiming and sorting maths | `sin()`, `cos()`, `atan2()`, `sort()` | aiming with the mouse, a high-score table, turn order | S |

- [x] `qg:after` and `ticks()`
- [x] `qg:when`
- [x] fields checked at compile time
- [x] `q:function` in `q:application`
- [x] `pressing()`, `pressed_for()`, `strength()`
- [x] `sin()`, `cos()`, `atan2()`, `sort()` (the Core's name)

What was built (2026-10-21):

- `addons/quantum/clock.gd`: one `Clock` node a scene, stepped first in the
  tick (before the tweens and the things). It counts `ticks()`, holds the
  qg:afters as records (the ticks left, the method that runs, the values of
  the handler's names) and reads the qg:whens' conditions (methods of the
  scene); it saves and loads them for the rollback, things by their path.
- `qg:after` compiles its body to a method of the script (`_after_N`) whose
  parameters are the names of the handler's own scopes (`Scope.locals()`:
  `me`, `other`, a loop's thing, a parameter, a variable), passed as they
  are; a thing gone by then is passed as null. `qg:when` compiles to a
  condition method and a handler with no `me`.
- A game's `q:function` is compiled into every scene's script and into P,
  with a scope of the game's state and functions only, so it means the same
  everywhere; a scene's of the same name is an error. The Core parser leaves
  them to the game compiler.
- `pressing()`, `pressed_for()`, `strength()` read the input of the tick
  (`Q._now`, and the ticks each action has been held, kept with it and
  saved by the rollback); an action named by a literal is checked.
- Fields: a character's id is checked against its controller's fields, `me`
  and `other` of a handler and a qg:for-each's thing against every thing's;
  a q:set, a parameter or a variable is not checked (it may hold a
  dictionary).
- In the games: Delve's and Keep's `hurt` (three and five copies) are one
  function of the game; Bricks' last brick is a qg:when (it runs a tick
  after the brick goes, which nothing in its tests sees).

What was learned: the condition of a qg:when is best read in the clock's
step, after the delays due then, so a delay that destroys the last enemy
and the qg:when that sees it agree on the tick; a lambda capturing a loop's
thing would have kept it, but could not be saved by the rollback, so the
values travel as arguments; `is` on a freed object is an error in GDScript,
so what a delay passes on is asked its type first. `q:call args=` split on
every comma (a text with one became two arguments): fixed with the phase.

## Phase 2 — Action and aiming

Pulled by a new game, **Siege**: a top-down shooter in waves, aimed with the
mouse or the right stick, with a charged shot, damage numbers and a mode for
two. It is the genre that uses Phase 1 most, and most of the "feel" the
language lacks.

| Feature | Proposed tag | Who uses it | Size |
|---|---|---|---|
| Aiming | `heading="{dx},{dy}"` on `qg:spawn`, for an `ai="fly"` prefab | aimed shots (Siege), a bow aimed with the mouse | S |
| Turn and thrust | `<qg:steer turn= thrust= drag=>`, a part of `qg:behavior` | an Asteroids ship, a racer seen from above | M |
| Text and bars in the world | `<qg:label x= y= value=>` (following a prefab) and `text=` on `qg:emit` | damage numbers, signs, names over the players | M |
| Emitters on things | `particles=` on a prefab or a character, always on | an engine's flame, an enemy on fire, a carried torch | S |
| Lines, beams and trails | `<qg:beam from= to=>` and `trail=` on a prefab | a laser tower (Towers), a grappling hook, a ship's trail | M |
| Squash, stretch, hide, depth | `scale-x`/`scale-y` on the tween, `visible=`, `flip-v=`, `layer=`, `y-sort=` on the scene | every game's "juice"; depth in a top-down game | M |
| Shots that bounce off tiles | `walls="bounce"` on `ai="fly"` | a ricochet, a ball in a level of tiles | S |
| Left and right in a collision | `side="left"` and `side="right"` on `qg:on-collision` | a switch hit from the side, a shield, a bumper | S |
| A buffered jump | `buffer-frames=` on the platformer controller and on `qg:jump` | every platformer (Hopper, Robot) | S |
| Keeping apart | `spacing=` on a prefab | swarms, crowds of enemies that do not overlap | M |

- [x] Siege, written first: what the compiler refuses is the list
- [x] `heading=` on `qg:spawn`
- [x] `qg:steer`
- [x] `qg:label`, `text=` on `qg:emit`
- [x] `particles=` on things
- [x] `qg:beam`, `trail=`
- [x] `scale-x`/`scale-y`, `visible=`, `flip-v=`, `layer=`, `y-sort=`
- [x] `walls="bounce"`
- [x] `side="left"` / `side="right"`
- [x] `buffer-frames=`
- [x] `spacing=`

What was built (2026-10-21):

- Siege (`projects/siege/siege.q`, art by `scripts/art/siege.py`), written
  first. The compiler's refusals were the list, and three more the game
  needed: a cursor read by its id (`aim.x`), `qg:damage amount=` as an
  expression, and the things Siege ran into below.
- `addons/quantum/looks.gd`: one `Looks` node on a character or a thing (or
  at a place of a scene, for a scene's label) keeps up every tick what is
  only seen: its labels (methods of the scene's script, or P's, with `me`),
  `visible=`, an effect kept going on it (`particles=`) and its trail. The
  play protocol's screen reads the labels. `beam.gd`: a line between two
  things for so many ticks. `Q.emit_text`: a label that rises and fades.
- `thing.gd`: `walls="bounce"` reflects the heading off the tile's normal;
  `spacing=` adds a push of half the overlap a tick away from each thing of
  its tag (in the scene's order, the same on every peer); a touch's side is
  judged from where the two are (`Q.side_of`), for things and for the
  left and right of characters; a thing that walks into a solid prefab
  touches it (`_bumps`).
- `behavior_body.gd`: `qg:steer` (an angle, thrust along it, drag, a top
  speed; the picture turns); `buffer=` on `qg:jump`, `buffer-frames=` on the
  platformer.
- `tween.gd`: `scale-x`, `scale-y`, and every scale from the thing's own
  size; the state reports a `scale_y` that differs, and `hidden` things.

What was learned: a thing's hitbox is no larger than its body, so a thing
pushing on a solid never overlapped it and its `qg:on-collision` never ran
(characters have a sensor two pixels larger for this); the slide collisions
of its move are the touch. A prefab's handlers run in P, and several scene
actions took `self` for the scene: from P they did nothing (`qg:goto-scene`)
or stopped the game (`qg:spawn`); a game function called from a prefab
made it plain. A shot that meets the tiles (`walls=`) is a moving body: it
started inside the archer that shot it and stuck there. A prefab that does
not move never touches; its `qg:on-collision` is now refused. Spacing as a
soft push lost to the seek that draws a crowd together; half the overlap a
tick holds them apart.

## Phase 3 — Puzzle and adventure

Pulled by a new game, **Crates**: a box-pushing puzzle with rooms drawn in
Tiled. With it, Keep and Delve gain dialogue with choices and a camera
cutscene (the gate the lever opened).

| Feature | Proposed tag | Who uses it | Size |
|---|---|---|---|
| Pushable things | `pushable="true"` on a solid prefab | box puzzles, puzzle rooms in an adventure | M |
| Animated tiles | `frames=` and `fps=` on `qg:tile` | water, lava and torches in any tile game | S |
| Dialogue with choices, a portrait and typed text | `<qg:choice label=>` in `qg:line`, `portrait=`, `speed=` on `qg:dialogue` | RPGs, visual novels, Keep | M |
| The camera to a point | `<qg:camera-to target= x= y= zoom= seconds=>`, then back to `follow=` | cutscenes, a boss's entrance, showing what a lever opened (Delve) | M |
| Click to walk | `controller="pointer"`: walks to where the cursor chose, by the shortest path | point-and-click, tactics | M |
| Things made of things | `<qg:attach>` and `qg:detach`; `extends=` on `qg:prefab` | a carried item, a turret on a tank, enemy families that change a number | L |
| More of Tiled | zones, exits and paths as objects; custom properties; several tilesets; flipped tiles | big levels drawn whole in Tiled (Crates, Hopper) | L |

- [x] Crates, written first
- [x] `pushable="true"`
- [x] animated tiles
- [x] `qg:choice`, `portrait=`, `speed=`
- [x] `qg:camera-to`
- [x] `controller="pointer"`
- [x] `qg:attach`, `qg:detach`, `extends=`
- [x] more of Tiled

What was built (2026-10-22):

- Crates (`projects/crates/crates.q`, art by `scripts/art/crates.py`, rooms
  in `projects/crates/rooms/*.tmx`), written first: three rooms of crates and
  pads, a foreman, two kinds of gate, a key. Each room was checked solvable
  by a small solver before it was drawn, and its moves are the CI's tape.
- `grid_body.gd`: a step into a pushable thing with a free cell beyond moves
  both (a `push` event) and runs the walker's touch; arriving in a cell
  touches the zones there, a Tiled zone too. `pointer_body.gd`: the pointer
  controller, a grid walker whose `_wanted()` follows a route found breadth
  first (right, down, left, up on a tie) to the clicked cell; a click on a
  thing ends in stepping into it, a crate only from beside it.
- `carried.gd` and `Q.attach`/`Q.detach`/`Q.carrying`: a carrier's
  `Carried` node moves what it carries after everything has moved; a carried
  thing's areas and body are quiet (deferred), and it stands in no cell.
- `model.py`: `extends=` is resolved on the XML before the game is read, so
  everything downstream sees whole prefabs: the attributes and children of
  the prefab extended, a child of the same kind and name (an animation, a
  state, a handler of the same `with=` and `side=`, the one `qg:behavior`)
  replaced.
- `camera.gd`: a shot (there, hold, back), saved and loaded with the
  rollback; `Q.camera_to` pauses the scene unless asked not to, and the
  camera goes on while the scene is paused. `dialogue.gd`: typing by the
  game's ticks, a face from the dialogue's sheet, choices with a focus, and
  a choice that opens another dialogue hands over to it; the box grows
  upwards with its choices.
- `tiled.py`, `tilemap.gd`: several tilesets (each layer one, matched by its
  image's name to the game's `qg:tileset`), Tiled's flip bits as Godot's
  transform flags, objects of class `zone`, `exit` and `path`, an object's
  `state`, the map's properties (`tiled()` is a constant as it compiles);
  `qg:tile frames= fps=` as the atlas's own animation.
- `a.col`, `a.row` for any thing (`Q.cell_col`, `Q.cell_row`), and
  `tile_at(col, row, layer)`. Keep's end asks what now with `qg:choice`,
  Delve's lever sends the camera to the wall (`pause="false"`: the
  playtest's ticks stay the same), Siege's brute `extends` its raider.

What was learned: a `qg:state` with no `frame=` drew frame 0 (the schema's
default), which no game had shown because every state so far named one; a
shut gate drawn as a worker made it plain. A game function that holds
`qg:camera-to` is compiled into every scene, the title too, which has no
camera: the check belongs to the scene's own handlers. `count()` read by a
HUD as the scene was built ran outside the tree. Clicks on a far crate
pushed it whichever way the walk came from; ending beside it, and pushing
on the next click, says what will happen.

## Phase 4 — To ship a game

No new game: it goes into all twelve, which gain an options screen and run on
a phone. It is what separates an example from a game someone publishes.

| Feature | Proposed tag | Who uses it | Size |
|---|---|---|---|
| An options screen | `bus=` on `qg:sound`, `<qg:volume bus= value=>` (kept between runs), `<qg:slider>` in a menu, `<qg:fullscreen>` | every game shipped | M |
| Rebinding keys | `<qg:rebind action=>` in a menu: the next key becomes the action's | shipping on desktop, accessibility | M |
| Save slots | `slot=` on `qg:save`, `qg:continue` and `has_save()` | RPGs and long adventures | M |
| Touch and phones | `<qg:touch-button action= x= y=>` and a touch stick that press the game's actions; Android and iOS presets | a phone's browser, app stores | L |
| HUD layout and pictures | positions `bottom-left`/`bottom-right`, `color=`, `if=` on `qg:hud`, `<qg:icon sheet= frame=>` | every game's HUD; a title with a logo | S |
| Grid and scrolling menus | `columns=` on `qg:menu`, scrolling past the screen | level select, a shop, an inventory | M |
| A macOS build | a macOS preset in `scripts/export-games.py` | shipping on desktop | S |

- [x] options screen: `bus=`, `qg:volume`, `qg:slider`, `qg:fullscreen`
- [x] `qg:rebind`
- [x] save slots
- [x] touch controls, Android and iOS presets
- [x] HUD layout, `qg:icon`
- [x] menu grids and scrolling
- [x] macOS preset
- [x] the twelve games with an options screen (fourteen now)

What was built (2026-10-22):

- Keep first, as it should read: three games on its title (`qg:save slot=`,
  `has_save(n)`), an Options scene (a slider of its sounds' bus, the full
  screen, the sword's key), a heart and a key drawn in its HUD and the
  message along the bottom only while there is one, and a stick and a button
  for a phone. The other thirteen followed: Options on each title (a lobby's
  `options=`), or in the pause menu of Robot, Drift and the RPG; Arena's keys
  in a grid of two columns that scrolls; touch controls for each.
- `q.gd`: the settings (`quantum-settings.json`: volumes, full screen,
  keys), the buses made from the sounds' `bus=` under Master, the keys put
  back over the game's own as the inputs are made, the slots
  (`quantum-save-<n>.json`, and the slot in use).
- `menu.gd`: sliders and keys among the buttons, a grid, a scroll that
  follows the focus; a key waits for the next press in `_input`, locally, as
  a field's typing does. `hud.gd`: icons, colours, `if=`, the bottom corners.
  `touch.gd`: buttons and sticks that press the actions with
  `Input.action_press`, so the tick, the replay and the lockstep see actions
  as from keys.
- `scripts/export-games.py`: macOS (exported here: an unsigned universal
  .app), Android and iOS presets, with ETC2/ASTC imported for them.

What was learned: Godot makes mouse events from touches, which worked the
controls twice and compared a finger's number with "mouse"; the made events
carry the emulation device and are left out. A test touches the window, not
the scene: the stretch from 320x192 to the window is the root viewport's
final transform. A macOS build for Apple's chips needs ETC2/ASTC imported,
which the desktop builds do not. A slider's number may not be called
`speed`: the compiler keeps the names of the properties of Godot's nodes
from the game's state, so the test's is `pace`.

## Phase 5 — Multiplayer and the play protocol

The lockstep already covers two to four players, spectators and rollback.
What is missing is choosing who sits where, talking between players and
playing on one screen. The first row is the one discussed on 2026-10-21: it
takes the waits out of the test harness and lets an agent take seat 3 or 4.

| Feature | Proposed tag | Who uses it | Size |
|---|---|---|---|
| Choosing the seat | `--q-seat=N` on joining; `seat=` on `play_start` with `join=`; `player=N` on `play_act` | tests with three or more machines, agents in any seat of Bricks | S |
| Names and messages between players | `shared="true"` on a `qg:field`: the text travels with the inputs when sent | showing who is who, a short chat | M |
| Split screen | `player=` on `qg:camera`, one view per player | local racing and co-op that split up | L |
| Input sequences and rumble | `sequence="down, right, punch" within=` on `qg:on-input`; `<qg:rumble player= strength= seconds=>` | special moves in Arena, every game with a controller | M |

- [x] seat selection
- [x] shared fields
- [x] split screen
- [x] input sequences, `qg:rumble`

What was built (2026-10-22):

- Seats: `--q-seat=N` asks the host (or the relay) for a seat as the joiner
  says hello; taken, the joiner is turned away and the game goes on (a peer
  turned away was never seated, so its leaving changes nothing). The play
  protocol: `seat=` on `play_start` with `join=`, `quantum play --seat`;
  `player=N` on `play_act` and `play_until` names the actions as player 1's
  and presses player N's on one machine, and in a networked game says the
  session's own seat (another is refused). `replay_peers` gives each tape the
  seat of its place, so its joiners come all at once, the host first. A
  test runs four machines of Bricks, three of them agents asking for seats 3,
  4 and 2, a fifth turned away from 3.
- Shared fields: Enter puts the field's text in this machine's next frame of
  the lockstep (a fourth element, `{field key: text}`, logged for one who
  rejoins); on the tick of that frame every machine sets the bound state and
  runs what the field holds, with `sender` and `text`. The rollback never
  guesses a text (a guess repeats the keys only), so a late one rolls back
  to its tick. The menu goes on, on every machine, when its own seat's text
  comes back; only the machine whose seat it is takes the keyboard.
  `local="true"` on `qg:menu` is this machine's seat's menu, of shared fields
  only. While a field has the keyboard, the keys type and play nothing (the
  Enter that ends it does not choose again). Typing is now something a
  player does in the play protocol (`text=`) and in a tape (`["type", text]`),
  so tests and agents type. Bricks over the network starts with who is who.
- Split screen: `split.gd` puts each player's camera in a `SubViewport` that
  draws the scene's world, side by side for two and in quarters for three or
  four, under the scene's HUD; over the network each machine shows its own
  player's camera, and the others run unseen. The screen of
  `qg:on-screen-exit` is every view, each as large as it is shown, so it is
  the same on every machine of a game. Rally, written for it: two cars on a
  circuit drawn in Tiled, laps counted at the line after halfway round.
- Sequences: every press is kept with how many ticks ago it was, in the
  input's state (the rollback saves and replays it); a sequence holds on its
  last step's press and uses its presses up. `forward` and `back` are read
  from the facing of the player's character. `qg:rumble` drives
  `Input.start_joy_vibration` on that player's pad (on one machine the Nth;
  over the network this machine's own, only for its seat) and a phone's
  vibrator. A fighter takes `qg:damage` as a hit, blocked by holding away.
  Arena's blast: down, forward, punch, felt on the joypad of the one it hits.

What was learned: a tick counter in the input's state differs between two
machines from the start (each counted its own ticks while it waited for the
other), so the lockstep's hash differed at its first check: the presses keep
an age instead, and the networked game starts with none. Under the rollback
a flying prefab cannot be taken back (no `qg:spawn` in its scenes), so
Arena's special move hits at once and shows a beam, which the rollback does
not draw twice. A local menu's field has one key on every machine: the menu
must go on only when its own seat's text comes back, not another player's.
A field reopened put the caret at its start; it goes to the end.

## Phase 6 — Later, with the game that asks

Ten gaps of the map stay out of Phases 1 to 5: they are real, but each serves
one genre or a rare case. Approved with the rest; each comes in when the game
that needs it is written, under the same rules.

| Feature | Why it waits | The game that would ask |
|---|---|---|
| 2D lights and shadows | only visual; asked by a cave, horror or stealth game, none on the roadmap | a stealth or cave game |
| Isometric and hexagonal maps | strategy and tactics only; it touches neighbours and the whole pathfinding | a tactics game |
| Positional sound | almost no effect in games the size of a screen | a level wider than the screen with off-screen threats |
| Terrain costs in pathfinding | strategy maps only (mud, road) | a tactics or strategy game |
| Plurals, assets and fonts per language | only when a translated game has counts, voices or another alphabet | a translated RPG |
| Reloading without restarting (hot reload) | a tool, not language; the replay already goes back to the same tick | the editor's game preview |
| Characters that block each other | platform co-op and sports only | a co-op platformer or a sports game |
| Mouse right button, wheel, hover | point-and-click and strategy only (selling a tower in Towers) | Towers' sell, a point-and-click |
| Nine-slice images | today's menus have no frames that stretch | a game with framed dialogue boxes |
| Music and sounds within a scene | boss music and footsteps only; `qg:music` per scene covers the rest | a boss fight in Hopper or Delve |

- [x] characters that block each other: already so, found by testing it (below)
- [x] mouse right button, wheel, hover (Towers' sell)
- [x] music and sounds within a scene (Delve's warden)
- [ ] positional sound
- [ ] nine-slice; plurals, assets and fonts per language (the RPG)
- [ ] 2D lights and shadows (Delve)
- [ ] isometric and hexagonal maps, terrain costs (a tactics game)
- [ ] hot reload

What was found (2026-10-22): characters already block each other. A
character is a `CharacterBody2D` on the physics layer the tiles and solids
are on, masking it, so two stop at each other and a platformer stands on its
partner's head; the map said they passed through. A test says it now
(`tests/godot/test_godot_bodies.py`), and Rally's cars bump. Fighters keep
their own rule (they do not cross on the ground), and ships pass through.

What was built (2026-10-22), for Towers: the right button, the wheel and
hover. `action=` on `qg:on-select` makes another of the player's actions
choose with the cursor (a `qg:input` of `MouseRight` is a right click), and
the keys `WheelUp` and `WheelDown` press an action as the wheel turns; both
are actions, so the replay and the lockstep carry them as they carry keys.
`hovered()` (or `hovered(2)`) is the thing under a player's cursor: the
cursor's point travels with the input, so it is the same on every machine.
Towers sells a tower with a right click (or X: 25 gold, 50 upgraded),
changes the tower to build with the wheel (or Tab), and says in its HUD what
the tower under the mouse sells for.

What was built (2026-10-22), for Delve: music and sounds within a scene.
`qg:music` in a handler changes the music there and then, crossfading; the
skeleton archer of the vault is its warden, and its fight has a theme of its
own (`warden.ogg`) from when it first sees a delver (a `qg:when`) until it
falls. `sounds="bones1, bones2, bones3"` on `qg:play` plays one of them each
time, so no two skeletons fall alike; the state records the list as
written, so the draw (from the voices' generator, heard only) changes
nothing a replay compares. The new music and the bones are synthesized by
`scripts/art/delve_music.py`, which writes the old two again byte for byte.
Layers of music that come in on the beat stay in the map.

Out by design (also in the map): rigid-body physics, which breaks the
lockstep's determinism; shaders and post-processing, which are code; a
scene editor, which is Godot's and Tiled's; and RPCs and node sync, which the
lockstep makes unneeded.

## Record

Each phase gets what was built and learned here as it is done, as in
[PLAN_GAMES_2.md](PLAN_GAMES_2.md).
