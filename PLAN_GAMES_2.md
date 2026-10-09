# Games 2 — plan for a complete declarative game engine

> Status: proposal (2026-10-09). Laboratory tier. This is the design the
> roadmap lists as "Games 2: games as a deterministic declarative simulation".
> Nothing here carries a stability promise until it ships.

## The decision

**Keep Godot 4 as the only runtime. Keep the `qg:` language. Rebuild the
middle — the code generators — from scratch. Retire the PixiJS backend.**

Why not rebuild everything: the language layer (`qg:` parser, 1.7k lines of
AST nodes, 84 parser tests) is in good shape and already knows the vocabulary
a platformer needs (`qg:prefab type="enemy" defeated-by="stomp"`,
`qg:enemy` with seven AI kinds, question blocks, checkpoints, a world map,
state that persists between scenes). Throwing that away buys nothing.

Why not keep the generators: they are the part that leaked.

| Problem today | Where |
|---|---|
| Two backends (PixiJS 4.4k lines, Godot 6.1k lines) that drifted: every tag had to be implemented twice, and in practice was implemented in one. **Done first (2026-10-09): the PixiJS backend is deleted; Godot is the only backend.** | `quantum/runtime/game_builder.py` |
| `q:function` bodies are copied through as raw JavaScript / GDScript, line by line. `q:if` and `q:loop` inside a function are silently dropped on Godot. This is the escape hatch every game in `projects/` falls into: the platformer has ~130 lines of JS in 15 functions | `game_engine_2d/src/parser.py:163`, `godot_code_generator.py:4548` |
| Unknown collision actions become a comment and the game builds anyway — against the "nothing without effect" rule | `godot_code_generator.py:4585` |
| Genre rules (stomp, squish, emerge, question block) are hard-coded as special cases in the generator instead of composed from primitives. A third genre means a third pile of special cases | `godot_code_generator.py` (`_write_*_script`, 3k lines) |
| No game uses the Godot backend. Nothing in CI runs Godot, so 259 tests assert generated text, not behaviour | `tests/test_godot_codegen.py` |

Why Godot and not a browser engine or our own: a real engine with an editor,
headless mode for CI (`godot --headless`), exports to web, desktop and mobile
from one project, and GDScript is a small, regular target to generate. The web
still works — Godot's HTML5 export runs in the browser — so retiring PixiJS
loses no platform, only a second implementation. The repository already made
this argument once, about the React Native target: a backend that
"translates on its own" is the opposite of one runtime.

## The architecture: thin compiler, fat runtime

Today the compiler writes a bespoke 4k-line GDScript project per game. Instead:

```
game.q ──parse──> Game AST ──compile──> project/
                                         ├── addons/quantum/      fixed GDScript runtime (versioned, identical in every game)
                                         ├── game.json            the declarative part: scenes, prefabs, tilemaps, HUD, inputs
                                         ├── scripts/*.gd         only the imperative part: q:function bodies, compiled
                                         └── project.godot, export_presets.cfg, assets/
```

1. **`addons/quantum/` — the runtime.** Hand-written GDScript, checked into
   this repository, tested on its own with GUT or Godot's test runner. It
   interprets `game.json`: builds the scene tree, wires collisions, runs the
   kinematic controllers, HUD, timers, spawners, state machines, scene
   transitions, persistence. Genre behaviour lives here as **composable
   components** (`Stompable`, `Collectible`, `Breakable`, `Patrol`, `Chase`,
   `Projectile`, `Spawner`…), not as generator special cases. The compiler
   never emits these; it names them.
2. **`game.json` — the data.** Everything declarative in the `.q` file becomes
   data. Most of a game is this file.
3. **`scripts/*.gd` — compiled logic.** `q:function`, `q:if`, `q:loop`,
   `q:set` and Quantum expressions (`{score + 100}`) compile to GDScript
   through one expression compiler, with the same semantics the Core runtime
   gives them (`quantum/core/expressions.py` is the reference). **Raw text
   inside a `q:function` is a compile error.** When a game needs something the
   language cannot say, the language grows a tag or a built-in; the game does
   not grow a script.

Deterministic by construction (the roadmap's "Games 2" promise): all game
logic runs in `_physics_process` at a fixed 60 Hz; no logic in `_process`;
one seeded RNG per scene (`<qg:scene seed="…">`); own kinematic movement
(CharacterBody2D + tile collision), no rigid-body simulation. Then **replay is
a test**: record inputs per tick, run the game headless for N ticks, assert
state. That is how the games get tested in CI without a screen.

## The language surface at the end

Existing tags stay (with their attributes), plus what the three games force.
Target shape, to be refined by writing the games first:

```xml
<q:application id="…" type="game" engine="godot">       <!-- engine="2d" means godot; pixi is gone -->

  <qg:prefab name="Walker" type="enemy" health="2" defeated-by="stomp" ai="patrol" speed="40" />
  <qg:prefab name="Shroom" type="item" effect="grow" auto-move="true" />
  <qg:prefab name="QBlock" type="block" content="Shroom" hit-from="below" becomes="empty" />

  <qg:character id="player" controller="platformer" hitbox="16x16"
                run-speed="90" jump-height="64" variable-jump="true" coyote-frames="6">
    <qg:state-machine initial="small">
      <qg:state name="small" hitbox="16x16" />
      <qg:state name="big"   hitbox="16x32" />
    </qg:state-machine>
    <qg:on-collision with="enemy" side="top">   <!-- side is new: top/bottom/left/right/any -->
      <qg:destroy target="other" /> <qg:bounce force="200" /> <qg:play sound="stomp" />
      <q:set name="score" value="{score + 100}" />
    </qg:on-collision>
    <qg:on-collision with="enemy" side="any">
      <qg:transition to="small" else="die" /> <qg:invulnerable frames="120" />
    </qg:on-collision>
  </qg:character>

  <qg:scene name="level-1" seed="7" tileset="assets/kenney/tilemap_packed.png" tile="16">
    <qg:tilemap src="levels/1.tmx">                 <!-- Tiled; object layers spawn prefabs -->
      <qg:spawn-layer name="enemies" />
      <qg:spawn-layer name="items" />
    </qg:tilemap>
    <qg:camera follow="player" bounds="tilemap" />
    <qg:hud position="top-left"><qg:counter bind="score" digits="6" /></qg:hud>
    <qg:timer every="30s" action="spawn" prefab="Walker" at="offscreen-right" />
  </qg:scene>
</q:application>
```

Action tags (`qg:destroy`, `qg:bounce`, `qg:play`, `qg:spawn`, `qg:transition`,
`qg:emit`, `qg:goto-scene`, `qg:shake`, `qg:tween`) replace the
`action="destroy-other;emit:x"` strings. Anything else is `q:set`/`q:if`/
`q:loop` on game state with Quantum expressions, as in the rest of the language.

## The three games

Chosen so the engine is not a one-genre engine. Each one is a Laboratory
project under `projects/`, art from Kenney (CC0), neutral names (no
third-party characters, titles or level layouts — see CHANGELOG, the earlier
clean-up for the same reason).

| Game | Genre | What it forces out of the engine |
|---|---|---|
| **Hopper** (platformer, 3 levels + world map) | side-scroller | kinematic controller, tilemaps from Tiled, side-aware collisions, enemies with AI, power-ups and character states, breakable/question blocks, checkpoints, world map, state persisting across scenes, game over screen |
| **Keep** (top-down adventure, ~6 rooms) | top-down | 8-direction movement, room-to-room transitions with the camera snapping, triggers and switches, keys/doors (inventory as state), hearts, melee hitbox, simple enemies, dialogue boxes in the HUD |
| **Drift** (vertical shooter, 3 waves + boss) | arcade | projectiles and pools, spawners on timers and waves, particles, boss state machine with phases, screen shake, lives/continues, high score persisted to disk |

Snake and Tic-tac-toe (today Pixi + JS) are migrated at milestone 1 as the
smoke test of the new backend; they are not counted among the three.

## Phases

Estimates assume one person full-time; each phase ends green in CI.

### Phase 0 — Ground (3–4 days)

- Pin a Godot 4 version. `scripts/godot.py`: download the headless binary into
  a cache; CI job `laboratory` installs it. `quantum run game.q --engine godot
  --check` imports the project headless and fails on any script error. This
  alone turns the 259 text-assertion tests into real ones.
- `tests/godot/`: a harness that runs a project headless for N ticks with a
  scripted input tape and dumps state as JSON. Used by every game test after.

### Phase 1 — Runtime addon and new compiler, feature-parity with Snake (2 weeks)

- `addons/quantum/`: scene builder from `game.json`, input map, sprites,
  animations, timers, event bus, HUD counters, scene manager, persistence.
- New `quantum/runtime/godot/` package replacing `godot_code_generator.py`
  and `godot_templates.py`: AST → `game.json` + compiled scripts.
- Expression and statement compiler: Quantum expressions → GDScript, `q:set`,
  `q:if`, `q:loop`, `q:function` with parameters and return. Raw text in a
  function is a compile error with the line. Unknown tag or attribute is a
  compile error. Conformance tests: the same expression evaluated by the Core
  evaluator and by Godot gives the same value (table of ~200 cases).
- Migrate Snake and Tic-tac-toe (today their `q:function` bodies are still
  the JavaScript of the old backend, copied into GDScript as they are);
  their replays pass in CI.
- Milestone: `projects/quantum-snake/snake.q` has zero lines of script.

### Phase 2 — Platformer kit and Hopper (3 weeks)

- Kinematic `platformer` controller with the existing retro constants
  (variable jump, coyote frames, rising/falling gravity, terminal velocity).
  Tune against a replay suite, not by eye: "from standing, a 12-frame hold
  reaches 64 px" is a test.
- Tilemap from Tiled `.tmx` (tiles, collision layer, object layers → prefabs).
- Side-aware collisions, `qg:character` states that change hitbox, items,
  blocks, checkpoints, enemy AI (`patrol`, `chase`, `hop`, `charge`,
  `emerge`, `fly-patrol`), stomp with squish, world map, game over.
- Hopper: 3 levels, world map, 3 enemy kinds, 2 power-ups.
- Milestone: Hopper playable end to end from a web export; every tag it
  needed exists; `kenney-platformer` is deleted (Hopper replaces it).

### Phase 3 — Top-down kit and Keep (2 weeks)

- `topdown` controller, 8-direction animation sets, room transitions
  (`qg:door to="room-3" at="east"`), camera snap/scroll modes, triggers
  (`qg:trigger area`), switches, keys as inventory state, melee hitbox as a
  timed child collider, `qg:dialogue` in the HUD with paging.
- Keep: 6 rooms, 2 enemy kinds, 1 locked door, 1 switch puzzle, an ending.

### Phase 4 — Arcade kit and Drift (2 weeks)

- Projectiles with pooling, `qg:spawner` with waves, particles, boss as a
  prefab with a `qg:state-machine` driving phases, screen shake, continues,
  high score persisted (`qg:persistent`).
- Drift: 3 waves, 1 boss with 2 phases, high-score table.

### Phase 5 — Document and ship (1 week)

- (The PixiJS backend was removed before phase 0, with its tests, the
  committed HTML builds and the web pages that framed them. `engine="2d"`
  keeps working and means Godot.)
- `docs/targets/games.md`: the tag reference, generated from the AST nodes the
  way `FEATURE_STATUS.md` is generated, so it cannot rot. Three "build this
  game" tutorials, one per genre, each one tested in CI like the cookbook.
- Web exports of the three games on the site (`docs/public/games/`), built in
  CI.
- CHANGELOG, roadmap row "Games 2" → done, SUPPORT_TIERS updated.

**Total: about 11 weeks.** Phases 3 and 4 can overlap if there are two people;
0–2 are sequential.

## Rules for the whole effort

1. **Write the game before the feature.** Each phase starts by writing the
   game's `.q` as it should read; every tag the compiler rejects is the to-do
   list. Not the other way round.
2. **No escape hatch.** No raw GDScript in `.q`, no `qg:script`, no
   `lang="gdscript"`. If a game truly cannot be expressed, that is a language
   finding; record it in the plan and add the smallest general tag.
3. **Every tag has a replay test.** A tag with no game using it and no test
   is deleted at the end of the phase.
4. **Generated output is never edited** (SUPPORT_TIERS already says so). The
   `projects/*/godot/` directories are build output, in `.gitignore`.
5. **Compile errors, not comments.** Unknown tag, attribute, action or
   prefab name fails the build with file and line.
6. **Determinism is tested.** Same tape, same final state hash, in CI, on
   Linux. (Cross-platform determinism is not promised; we use only integer
   tile math and Godot's fixed physics tick.)

## Risks

| Risk | Mitigation |
|---|---|
| Godot binary in CI (~100 MB download, Godot version drift) | pinned version, cached; one place (`scripts/godot.py`) knows the version |
| GDScript expression semantics ≠ Python-like Quantum semantics (integer division, truthiness, string ops) | the conformance table in Phase 1; the compiler emits helper calls (`Q.div`, `Q.truthy`) where they differ |
| The kinematic controller "feels wrong" and tuning drags on | replay tests pin the numbers first; feel is tuned within the tested envelope |
| Three games is a lot of content | levels are data (Tiled); the plan sizes them small (3 levels, 6 rooms, 3 waves) |
| Playground cannot run games (Pyodide has no Godot) | out of scope; the site embeds the web exports instead |

## Open questions for the author

- Name of the file format: is `game.json` fine, or a Godot `.tres` resource so
  the editor shows it natively? (`.json` is easier to test from Python.)
- Should the three games live in `projects/` (today's convention) or in a
  new `games/`?
- Keep `qg:` as the prefix, or move to `game:`? (Cosmetic; decide before the
  docs are generated.)
