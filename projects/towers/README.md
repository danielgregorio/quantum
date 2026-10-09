# Towers — a tower defense, transcribed

`towers.q` is the [Godot 4 Tower Defense Template](https://github.com/ape1121/Godot-4-Tower-Defense-Template)
(MIT) written in the game language: its grass map, its four dinos, two of
its four turrets, its waves, gold and base. Two players can build on the
same map over the network. The assets are the template's (`assets/LICENSE.md`).

Run it: `quantum run projects/towers/towers.q`, then open `projects/towers/godot`
in Godot. Point with the mouse (or the arrows), click (or Enter) to build the
chosen turret on a free cell, click a turret to upgrade it; `1` and `2`
choose the turret. Over the network:

```
godot --path projects/towers/godot -- --q-host=7777          # player 1
godot --path projects/towers/godot -- --q-join=HOST:7777     # player 2
```

## The original, piece by piece

| In the template | Lines | In `towers.q` |
|---|---|---|
| `Data.gd`: turrets, enemies and maps as dictionaries of stats | 183 | the `qg:prefab`s' attributes and `qg:state`s |
| `turret_base.gd`: `DetectionArea` enter/exit, `try_get_closest_target`, `look_at`, `AttackCooldown` | 122 | `ai="turret" targets="dino" range= fire-every= rotate="true"`: the nearest target in range, every so many ticks |
| `projectileTurret.gd` + `bulletBase.gd`: a bullet headed at the target, damage on `area_entered`, pierce | 18 + 31 | `fire-prefab="Bullet"` headed at the target; the Bullet's `qg:on-collision with="dino"` does `qg:damage` and `qg:destroy` |
| `melee_turret.gd`: damage every enemy in `DetectionArea` | 11 | `attack="area" damage="5"` |
| `turret_details.gd`: upgrade (stats × or +), sell | 62 | a click on a turret: `qg:become target="other" state="level2"` (fire-every halved); no sell yet |
| `turret_drag_texture.gd`: drag a turret from the HUD, red over obstacles, drop to build | 65 | `qg:cursor grid="48"` + `qg:on-select`: `thing_at('road', cursor.x, cursor.y)` and `other` say whether the cell is free; `qg:spawn at="cursor"` |
| `map1.tscn`: `Path2D` curve, `CollisionPolygon2D` obstacles | 30 | `qg:path points=` (the curve's points, straight between them) and `qg:zone tag="road"` rectangles |
| `enemy_mover.gd`: `PathFollow2D` at `0.0005 × speed` a frame, damage flash, `finished_path` → base damage | 62 | `ai="path" speed="100"` per unit (the curve is 3,337 px); `qg:on-collision with="base"` at the road's end |
| `EnemySpawner.gd`: waves, `wave_spawn_count × difficulty`, kinds unlocked by difficulty, next wave when all are dead | 73 | two `qg:timer`s: one sends a dino every 12 ticks while `to_spawn > 0`, one starts the next wave when `count('dino') == 0` |
| `baseMap.gd`: `gold`, `baseHP`, game over | 33 | game state, and a `qg:timer every="1"` that goes to `lost` at 0 |
| `hud.gd`: HP, gold, wave, enemies, "next wave in" | 42 | `qg:hud` counters bound to the state |
| `Globals.gd` signals, main menu, map select, map 2, the ray turret | ~200 | not transcribed |

The template's dino speeds (1, 2, 5, 10) are its `progress_ratio` units; here
they are 100 px/s each, the same along this road. Waves here are
`5 + 3 × wave` dinos with a new kind every two waves, instead of the
template's `10 × 1.5^wave` (which puts 30 dinos on the road at wave 1).

## What the language had to grow

1. **Named actions and the mouse**: `qg:input action="buy-gatling" keys="1"`
   and `qg:on-input action="buy-gatling"`; `MouseLeft`/`MouseRight` as keys;
   `select` and `cancel` as default actions.
2. **A cursor as input**: `qg:cursor player= grid= step= sheet=` is the
   mouse, or the player's directions; `qg:on-select` runs with `cursor`
   (x, y, col, row, player) and `other`, the thing under it. Under
   `qg:multiplayer` the cursor travels in the input frame with the keys,
   so a click is the same click on every peer.
3. **The world in expressions**: `count(tag)` and `thing_at(tag, x, y)`,
   the first of the queries the gap analysis called the number-one gap.
4. **A route**: `qg:path points=` and `ai="path"`; `qg:spawn at="path" path=`.
5. **A turret**: `ai="turret" targets= range= attack= damage=`, a prefab's
   `fire-prefab` headed at the target; `qg:state` overriding `fire-prefab`
   and `range`; `qg:become target="other"`.

Still missing after Towers: selling (a `cancel` click on a turret needs
`qg:on-select action="cancel"`), the template's main menu and map select
(`qg:menu`), the ray turret (a beam: a `qg:line` thing), a second map.

## The test

`tests/godot/test_godot_towers.py` replays it: a click builds on a free
cell and not on the road or without the gold, a click upgrades, waves come
down the road and the gatling earns gold (the same every time), the base
falls with no towers, and two peers build the same defence in lockstep.
