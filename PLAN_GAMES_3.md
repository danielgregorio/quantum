# Games 3 — what the game language takes from Godot and Unity next

> Status: approved 2026-10-21, whole, the ten "later" items included (each
> comes in with the game that asks for it: Phase 6). Phase 1 in progress.
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
| Aiming and sorting maths | `sin()`, `cos()`, `atan2()`, `sorted()` | aiming with the mouse, a high-score table, turn order | S |

- [ ] `qg:after` and `ticks()`
- [ ] `qg:when`
- [ ] fields checked at compile time
- [ ] `q:function` in `q:application`
- [ ] `pressing()`, `pressed_for()`, `strength()`
- [ ] `sin()`, `cos()`, `atan2()`, `sorted()`

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

- [ ] Siege, written first: what the compiler refuses is the list
- [ ] `heading=` on `qg:spawn`
- [ ] `qg:steer`
- [ ] `qg:label`, `text=` on `qg:emit`
- [ ] `particles=` on things
- [ ] `qg:beam`, `trail=`
- [ ] `scale-x`/`scale-y`, `visible=`, `flip-v=`, `layer=`, `y-sort=`
- [ ] `walls="bounce"`
- [ ] `side="left"` / `side="right"`
- [ ] `buffer-frames=`
- [ ] `spacing=`

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

- [ ] Crates, written first
- [ ] `pushable="true"`
- [ ] animated tiles
- [ ] `qg:choice`, `portrait=`, `speed=`
- [ ] `qg:camera-to`
- [ ] `controller="pointer"`
- [ ] `qg:attach`, `qg:detach`, `extends=`
- [ ] more of Tiled

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

- [ ] options screen: `bus=`, `qg:volume`, `qg:slider`, `qg:fullscreen`
- [ ] `qg:rebind`
- [ ] save slots
- [ ] touch controls, Android and iOS presets
- [ ] HUD layout, `qg:icon`
- [ ] menu grids and scrolling
- [ ] macOS preset
- [ ] the twelve games with an options screen

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

- [ ] seat selection
- [ ] shared fields
- [ ] split screen
- [ ] input sequences, `qg:rumble`

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

Out by design (also in the map): rigid-body physics, which breaks the
lockstep's determinism; shaders and post-processing, which are code; a
scene editor, which is Godot's and Tiled's; and RPCs and node sync, which the
lockstep makes unneeded.

## Record

Each phase gets what was built and learned here as it is done, as in
[PLAN_GAMES_2.md](PLAN_GAMES_2.md).
