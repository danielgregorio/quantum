# RPG — Godot's "JRPG" demo, transcribed

`rpg.q` is the "JRPG" demo of
[godotengine/godot-demo-projects](https://github.com/godotengine/godot-demo-projects)
(`2d/role_playing_game`, MIT) written in the game language. It has the same
map, tile for tile, the same slimes, the same lines, and the same fight with
the same numbers. The art and the font are the demo's (`assets/LICENSE.md`),
packed by `scripts/art/rpg.py`.

To run it: `quantum run projects/rpg/rpg.q`, then open `projects/rpg/godot` in
Godot. Walk with the arrows or WASD (two at once walk diagonally). Walk into
the key or the other slime to hear what they say; Enter, Space or a click
shows the next line. In the fight, choose Attack, Defend or Flee.

## The original, piece by piece

| In the demo | Lines | In `rpg.q` |
|---|---|---|
| `exploration.tscn`: the `Ground`, `Pathways` and `Grid` TileMapLayers, 64 px tiles that are single images placed flipped or transposed | 1900 | three `qg:tilemap`s on one tileset, the last with `collision="true"`. `scripts/art/rpg.py` decodes the layers' `tile_map_data` and makes each image-and-transform used a tile of `assets/tiles.png`. |
| `grid.gd` + `pawn.gd` + `walker.gd` + `player.gd`: a pawn asks the grid for the next cell; an empty cell is walked to in 0.25 s, a pawn there opens its dialogue, anything else is a 0.25 s bump | 47 + 17 + 54 + 21 | `<qg:character controller="grid" diagonal="true" step-frames="15">`. Stepping into a thing runs the character's `qg:on-collision` with its tag; a wall is a bump. |
| the `Opponent` and the `Object` pawns, each with a `DialoguePlayer` | — | the `Opponent` and `Key` prefabs, placed with `qg:instance` |
| `dialogue_player.gd` + `interface.gd` + `dialogue_data/*.json`: the lines one at a time in a box, the player stopped until the last | 44 + 40 | `<qg:dialogue>` with its `qg:line`s, opened by `<qg:say>` |
| `game.gd`: the opponent's dialogue over, the fight; the fight over, back to the map and "you won" or "I won" | 57 | the dialogue's `<qg:on-end>` goes to the `combat` scene; the game state `outcome` says how it ended, and the map, entered again, puts the player back where it was (`me.col`, `me.row`) and says the line |
| `combat.gd` + `turn_queue.gd` + `combatant.gd` + `health.gd`: turns in order; a hit takes the damage less the armor; Defend adds the defense to the armor until the next turn | 52 + 52 + 40 + 31 | the scene's `life`, `armor`, `foe_life`, `foe_armor` and `turn`, and two `q:function`s |
| `player.tscn`, `opponent.tscn`: 10 and 7 life, 2 and 3 damage, 1 defense each, 1 and 0 armor | — | the same numbers in the `q:set`s |
| `opponent.gd`: on its turn, a 0.25 s `Timer`, then it attacks | 20 | a `qg:timer every="1"` counting down `wait` from 15 |
| `ui.gd`: Attack, Defend and Flee, only on the player's turn; Flee loses | 46 | `<qg:menu if="{turn == 'player'}">` with three `qg:button`s |

These differences are deliberate:

- The map is not moved 25 px down, as the demo's layers are.
- The grass, flower and pebble decorations are not placed.
- Damage shakes the scene. The demo squashes the slime that is hit.
- The fight's names and life bars are a HUD over the background, not the demo's panels, and the buttons are the language's menu. The blue and green pillars are not drawn.
- There is no fade to black between the map and the fight.

## Beyond the demo

The demo has a key that says "Just a key..." and nothing to carry. Here the
player takes what it walks into, in the game state, so the map remembers it
across fights:

- the key: `keys`, and its name in `taken`, so its `qg:instance if=` leaves it
  off the map from then on;
- two potions on the map, at (1, 1) and (14, 9): `potions`;
- a HUD with what it carries, and a Potion button in the fight, shown while
  it has one: 5 life back, up to 10 (the demo's `health.gd` has a `heal`
  nothing calls), and the opponent's turn.

The potion is drawn by `scripts/art/rpg.py` (CC0). All of it is the
language as it was: game state, `qg:instance if=`, `qg:destroy`, `qg:menu`
buttons with `if=`.

## What the language had to grow

1. **Grid walking**: `controller="grid"` steps from cell centre to cell
   centre of the scene's tilemap in `step-frames=` ticks. The tiles of a layer
   with collision, the edge of the map and the things in the scene close a
   cell. Stepping into a thing runs `qg:on-collision`; anything else closed is
   a bump. `diagonal=` lets two directions held at once step diagonally.
   `me.col` and `me.row` are the cell it stands in.
2. **Dialogue**: `<qg:dialogue name=>` holds `qg:line who= text=` (either may
   be an expression) and a `qg:on-end`. `<qg:say dialogue=>` opens it: the
   lines show one at a time in a box at the bottom of the screen, select shows
   the next, and the scene is paused until the last (`talking()` says so).
3. **Layers**: several `qg:tilemap`s in a scene are layers of one map on one
   tileset, drawn in order.

Every number above is checked in Godot by `tests/godot/test_godot_rpg.py`:

- a step of a quarter of a second, a step after the other while held, and diagonal steps;
- a wall that is a bump;
- the key's line, and select that closes it;
- the opponent's three lines, then the fight;
- an attack, and the answer a quarter of a second later;
- Defend's armor, for one hit;
- four attacks that win, and the line on the map from where the fight started;
- Flee, which loses;
- a potion picked up, and drunk in the fight.
