# Robot — Godot's "Platformer 2D", transcribed

`robot.q` is the "Platformer 2D" demo of
[godotengine/godot-demo-projects](https://github.com/godotengine/godot-demo-projects)
(`2d/platformer`, MIT) written in the game language. It has the same level,
tile for tile, the same robot with the same numbers, and the same enemies,
coins, lifts and pause menu. The art and sounds are the demo's
(`assets/LICENSE.md`).

To run it: `quantum run projects/robot/robot.q`, then open `projects/robot/godot`
in Godot. Use the arrows or A/D to run, and Up, W or the joypad's A to jump; you
can jump again in the air. Space, Z or Ctrl shoots. Escape pauses the game.

## The original, piece by piece

| In the demo | Lines | In `robot.q` |
|---|---|---|
| `project.godot`: 800x480, gravity 2100, 120 physics ticks | — | `<qg:scene width="800" height="480">`; `gravity="2100"` on the robot and the enemies. The language ticks at 60 Hz, and every number is per second, so the motion is the same. |
| `tileset.tres`: 20 atlas sources of 64 px tiles, each with a collision polygon and flipped alternatives | 689 | `<qg:tileset tile="64">` with a `qg:tile` for each tile that is not a full square. Several grassy tops start 10 px down. Two thin ledges are 36 and 33 px thick. The slope is one-way. Flipped alternatives are negative numbers in the tilemap. |
| `level.tscn`: the `TileMapLayer`, 341 cells from (-12, -11) to (22, 12) | 70 | the CSV rows of `<qg:tilemap collision="true">`. They were decoded from the scene's `tile_map_data`, and every position is moved by (768, 704). |
| `player.tscn`: scale 0.8, 42.5x54.5 box, 8x8 frames of 64 px; `idle`, `run`, `jumping`, `falling` | 269 | `<qg:character controller="platformer" scale="0.8" hitbox="34x44">` with `idle`, `walk`, `jump` and `fall` animations. The hitbox is the scaled box. |
| `player.gd`: walk 300 px/s, `move_toward` at 1800 px/s², jump -725, terminal velocity 700 | 30 | `run-speed="300" accel="1800" jump-speed="725" max-fall="700"` |
| `player.gd`: a second jump in the air multiplies `velocity.x` by 2.5; releasing jump while rising multiplies `velocity.y` by 0.6 | 15 | `air-jumps="1" air-jump-boost="2.5" jump-cut="0.6"`; `coyote-frames="0"`, because the demo only jumps from the floor |
| `gun.gd` + `bullet.tscn`: `shoot` spawns a `RigidBody2D` at 850 px/s the way the sprite faces, with a 0.3 s cooldown and a 1 s life | 25 + 14 | `fire-action="shoot" fire-prefab="Bullet" fire-every="18"`; `Bullet` is `ai="fly" speed="850" lifetime="60" walls="stop"` |
| `bullet.gd`: `_on_body_entered` → `Enemy.destroy()` | 6 | the bullet's `<qg:on-collision with="enemy">`: `qg:burst`, `qg:play sound="explode"`, `qg:destroy` both |
| `enemy.gd`: 22 px/s, gravity, turns at walls and where its floor rays find nothing | 58 | `<qg:prefab ai="patrol" speed="22" turns-at="edge" gravity="2100">`, with the 16-frame walk at 16 fps |
| `coin.tscn` + `coin.gd`: an `Area2D` spinning 0,1,2,3,2,1; picked on touch | 187 + 11 | `<qg:prefab name="Coin" scale="0.65">` with a `walk` animation, and the robot's `<qg:on-collision with="coin">` |
| `coins_counter.gd`: the count, top-left | 16 | `<qg:hud><qg:counter bind="coins">` |
| `platform.tscn`: an `AnimatableBody2D`, a one-way 192x27 box 7.5 px above its middle; two `AnimationPlayer`s move them, one 210 px up and back in 4 s, the other 295 px in 8 s | 174 + 30 | `ai="shuttle" one-way="true" shape="-96,-21; 96,-21; 96,6; -96,6"` with `dy="-210" period="240"` and `dy="-295" period="480"` |
| `PlatformStatic`: a `StaticBody2D` rotated 0.356 rad, a six-point polygon, two sprites | 20 | the `Ledge` prefab: its `shape=` is the demo's polygon, the instance has `gd:rotation`, and the second picture is a `qg:sprite` |
| `parallax_background.tscn`: a sky, clouds and two rows of distant platforms, at a tenth of 0.2, 0.1, 0.2 and 0.4 of the camera across, fixed up and down | 150 | two `<qg:parallax>`: `sky` (the sky and the clouds) at `scroll="0.02"`, `hills` at `scroll="0.04"` |
| the player's `Camera`: limits -715, -250, 1425, 690; offset 50 px down | 8 | `<qg:camera bounds="none" gd:limit_left="53" ... gd:offset="0,39">` (the demo's limits moved like the map) |
| `game.gd` + `pause_menu.gd`: `toggle_pause` pauses the tree and opens a menu with Resume | 25 + 78 | `<qg:on-input action="pause">` with `qg:pause`/`qg:resume`, and a `<qg:menu if="{paused()}">` with Resume and Restart |
| `project.godot`: `jump` on Up/W/JoyA, `shoot` on Space/Z/Ctrl/JoyX, `toggle_pause` on Escape/Start | 60 | three `qg:input`s |

These differences are deliberate:

- The bullet flies straight. In the demo it is a rigid body with a tenth of the gravity that bounces off the floor.
- An enemy dies with a burst at once. The demo plays a fall-and-fade animation first.
- The robot passes through enemies, while in the demo it bumps them. It is invincible in both.
- The decorations (grass, flowers, trees, vines, bushes) are not placed.
- The music, splitscreen and the fullscreen key are not transcribed. The music has no license of its own in the demo (`assets/LICENSE.md`).
- The parallax sky is two pictures instead of six layers: `scripts/art/robot_sky.py` draws the sky and its clouds into one, and the two rows of distant platforms into another, as the screen first shows them.

The demo's map has two lips. One is the 10 px step at the foot of the slope, the other the 7 px edge at its top. A rectangle cannot walk over either of them, so the robot jumps them in this level as it would in the demo.

## What the language had to grow

1. **Tiles with shapes**: `qg:tile frame= shape= one-way=` inside a
   `qg:tileset` gives a tile its own polygon, from the tile's top-left corner,
   or `shape="none"` for no collision at all. A negative number in a tilemap is
   the tile flipped left to right, and Godot flips its shape with it.
2. **The platformer controller**: `accel=` (run speed eased in and out),
   `jump-speed=` (the take-off speed instead of a height), `air-jumps=` with
   `air-jump-boost=`, `jump-cut=` (the demo's release rule instead of the
   extra gravity), and a `fall` animation.
3. **Shooting from a platformer**: `fire-action=` and `fire-prefab=` on
   `controller="platformer"`. The shot starts in front of the character,
   heading the way it faces, and `fire-every=` is the cooldown between
   presses. `fire-action` names any action now, `shoot` included.
4. **Solid shapes**: `shape=` on a solid prefab is a polygon from its centre,
   concave or not, so a lift's box can sit off-centre and a platform can be
   tilted (`gd:rotation` on the instance).
5. **Shots that walls stop**: `walls="stop"` on an `ai="fly"` prefab. A level
   larger than the screen keeps its shots alive across the whole tilemap, not
   only on screen.
6. **Pictures at their size**: `scale=` on a prefab or a character scales the
   picture only. A prefab that is not `ai=` (a coin) plays its `walk`
   animation.
7. **Pause**: `qg:pause` and `qg:resume` stop and restart everything that
   plays in the scene (characters, things, timers, spawners). Menus, the HUD,
   the cursors and `qg:on-input` keep going. `paused()` says which, and
   `qg:menu if=` shows a menu only while its condition holds.
8. **A parallax backdrop**: `qg:parallax` places a picture on the screen,
   behind the level, repeating across. `scroll=` is how fast it moves with
   the camera: 0 stays still, 1 moves with the level.

Every number above is checked in Godot by `tests/godot/test_godot_robot.py`:

- the robot stands on the lowered grass;
- its speed after 10 ticks of acceleration, and the coins it picks up;
- a jump held against a jump released early;
- one more jump in the air, and no third;
- the shooting cooldown, and a bullet that a wall stops;
- an enemy shot;
- the slope;
- the lift that carries it;
- the pause that freezes the world on its tick until the menu resumes it.
