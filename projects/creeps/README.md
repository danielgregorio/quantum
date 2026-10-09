# Creeps — Godot's "Dodge the Creeps", transcribed

`creeps.q` is the "Dodge the Creeps" demo of
[godotengine/godot-demo-projects](https://github.com/godotengine/godot-demo-projects)
(`2d/dodge_the_creeps`, MIT), the game of Godot's "Your first 2D game"
tutorial, written in the game language. Same screen, player, creeps, timing
and screens; the art, music and font are the demo's (`assets/LICENSE.md`).

Run it: `quantum run projects/creeps/creeps.q`, then open `projects/creeps/godot`
in Godot. Arrows or WASD (or a joypad) to move; click Start, or press Space or Enter.

## The original, piece by piece

| In the demo | Lines | In `creeps.q` |
|---|---|---|
| `main.tscn`: a `Node` with a `ColorRect` (`#385f61`), 480x720 | 8 | `<qg:scene width="480" height="720" background="#385f61">`, three of them: `title`, `play`, `over` |
| `player.tscn` + `player.gd`: `Area2D`, `AnimatedSprite2D` (walk, up), capsule 27/68, 400 px/s, clamped to the screen, `hide()` until `start()` | 50 + 40 | `<qg:character controller="topdown" speed="400" bounds="scene" hitbox="54x68">` with `walk` and `walk-up` animations; hidden-until-start is the `title` scene |
| `player.gd`: `flip_h` by x, `rotation = PI` going down | 4 | the topdown controller: `walk-up` upside down for down |
| `player.gd`: `_on_body_entered` → hide, `hit` → `game_over()` | 12 | `<qg:on-collision with="creep">` → `qg:stop`, `qg:play`, `qg:goto-scene name="over"` |
| `mob.tscn` + `mob.gd`: `RigidBody2D`, three animations picked at random, `VisibleOnScreenNotifier2D` → `queue_free` | 60 + 8 | three `<qg:prefab ai="fly" rotate="true">`, each with its animation; a flyer is gone off-screen by itself |
| `main.gd`: `MobTimer` 0.5 s → a mob at a random point of a `Path2D` round the screen, heading perpendicular ± 45°, speed 150–250 | 20 | `<qg:spawner prefab="Flyer, Swimmer, Walker" along="edges" heading="inward" spread="45" every="30" count="0" />` and `speed="150..250"` |
| `main.gd`: `StartTimer` 2 s, then `ScoreTimer` 1 s → `score += 1` | 8 | `<qg:timer every="60" from="120">` with `q:set score` |
| `hud.tscn` + `hud.gd`: `ScoreLabel` (top, 60 px Xolonium), `MessageLabel` (centre), `StartButton`, `MessageTimer` | 60 + 30 | `<qg:hud position="top-center" font=… size="60">` and `<qg:hud position="center">` with `qg:text`s; messages are state the timers set |
| `hud.gd`: "Get Ready" for a `MessageTimer`, "Game Over", then the title after 1 s, then the button | 15 | `qg:timer after=` setting `message` and `can_start`; a `qg:menu` with a Start `qg:button` shown `if="{can_start}"`; `qg:on-input action="jump"` is the button's shortcut |
| `Music`, `DeathSound` | 4 | `<qg:sound loop="true">` played as `play` is entered, stopped on the hit |
| `project.godot`: four `move_*` actions on WASD/arrows | 40 | the defaults; `jump` on Space/Enter/JoyA/JoyStart |
| `Trail` particles behind the player | 20 | nothing (cosmetic) |

Deliberate differences: the player's trail is not drawn; a creep's capsule is a rectangle.

## What the language had to grow

1. **Edges and headings on `qg:spawner`**: `along="edges"`, `heading="inward"`,
   `spread=`, several prefabs drawn at random, `count="0"` for no end.
2. **A speed range**: `speed="150..250"` on a prefab, drawn from the seed as
   each instance is placed; `rotate="true"` turns a flyer's sprite to its heading.
3. **The top-down controller**: `bounds="scene"`, `walk-up`/`walk-down`
   animations (`walk-up` upside down stands in for down), analog strength.
4. **The HUD**: `position="center"`, `font=` (a .ttf), `size=`.
5. **Music**: `loop=` on `qg:sound`, `qg:stop`, and `qg:play`/`qg:stop`
   directly in a scene (as it is entered).
6. **Timers**: `from=` on `qg:timer every=`.
7. **The game's state in a scene**: a `q:set` of a game-wide name directly in
   a scene sets it as the scene is entered (`score` back to 0).
8. **Joypads** (asked by Pong, done here): `Joy*` names in `qg:input keys=`,
   player n on joypad n-1, analog strength on the ship and top-down controllers.
9. **Reserved names from Godot's reference**: `ready` as a state name was a
   GDScript error at run time; every member of `Node2D` is now refused at
   compile time, from the same generated table `gd:` uses.

Still missing after Creeps: particles beyond `qg:burst`. (The clickable Start
button came later, with `qg:menu`.)

## The test

`tests/godot/test_godot_creeps.py` replays it: the title waits, "Get Ready"
then creeps from the border and a point a second (the same creeps for the
same seed), the player's speed and the screen's edge, and a creep ending the
run with the score kept.
