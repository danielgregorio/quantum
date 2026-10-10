# Pong — Godot's demo, transcribed

`pong.q` is the "Pong with GDScript" demo of
[godotengine/godot-demo-projects](https://github.com/godotengine/godot-demo-projects)
(`2d/pong`, MIT) written in the game language: the same court, paddles, ball
and rules, tag for node. The point of the exercise is not the game; it is
what a game that already exists makes the language say. The sprites are the
demo's (`assets/LICENSE.md`).

Run it: `quantum run projects/pong/pong.q`, then open `projects/pong/godot`
in Godot. Left paddle on W/S, right paddle on the arrows.

## The original, piece by piece

| In the demo | Lines | In `pong.q` |
|---|---|---|
| `pong.tscn`: a `Node2D` with a `ColorRect` background (`#24272a`) | 4 | `<qg:scene width="640" height="400" background="#24272a">` |
| `Left`, `Right`: `Area2D` + `Sprite2D` + 8x32 shape, `modulate` cyan / magenta, `paddle.gd` | 2 × 3 + 28 | `<qg:character controller="ship" axis="vertical" speed="100" hitbox="8x32" gd:modulate=…>` |
| `paddle.gd`: `_process` reads `<name>_move_up/down`, clamps `y` to `[16, height - 16]` | 5 | `player="1"` / `player="2"` and `bounds="scene"` (the ship's default) |
| `project.godot`: four input actions, keyboard and joypad | 40 | four `<qg:input player=… action=… keys=… />` (keyboard; joypad is a gap) |
| `paddle.gd`: `_on_area_entered`: ball direction = `(±1, randf() * 2 - 1).normalized()` | 3 | `<qg:on-collision with="ball"><qg:deflect target="other" dx="±1" dy="{random(-1, 1)}" /></qg:on-collision>` |
| `Ball`: `Area2D` + sprite + 8x8 shape, `ball.gd`: `position += speed * delta * direction`, `speed += 2 * delta` | 3 + 15 | `<qg:prefab ai="fly" heading="left" speed="100" accel="2" hitbox="8x8">` + `<qg:instance name="ball">` |
| `ball.gd`: `reset()` to the initial position, `LEFT`, default speed | 4 | `<qg:respawn target="me" />` |
| `Ceiling`, `Floor`: `Area2D` 640x20 at y=-10 / 410, `ceiling_floor.gd`: `direction = (direction + (0, ±1)).normalized()` | 2 × 2 + 5 | two `<qg:zone tag="edge">` and, on the ball, `<qg:on-collision with="edge"><qg:deflect axis="y" /></qg:on-collision>` |
| `LeftWall`, `RightWall`: `Area2D` 20x400 at x=-10 / 650, `wall.gd`: `area.reset()` | 2 × 2 + 4 | two `<qg:zone tag="wall">` and, on the ball, `<qg:on-collision with="wall"><qg:respawn /></qg:on-collision>` |
| `Separator`: a `Sprite2D` at (320, 200) | 2 | `<qg:sprite sheet="separator" x="320" y="200" />` |
| `Camera2D` with `offset = (320, 200)` | 2 | nothing: a scene is shown whole |
| six `[connection signal="area_entered" …]` lines | 6 | nothing: `qg:on-collision` is the connection |

The one deliberate difference: the demo's ceiling and floor *add* a
vertical push to the ball's direction and renormalize; here the ball's
vertical heading is *reflected* (`qg:deflect axis="y"`), which is what a
bounce means and what a second game would ask for. The demo's analog paddle
speed (`get_action_strength`) is digital here: the keys are pressed or not.

## What the language had to grow

Each of these was missing; each is a tag or an attribute, never a line of
script, and each is the shape a second game would reuse:

1. **A second player.** `player=` on `qg:input` and `qg:character`: player 2's
   keys are declared (`p2_up`, `p2_down` are what the replay tape presses).
2. **One axis.** `axis="vertical|horizontal"` on the ship controller.
3. **Zones.** `qg:zone name= tag= x= y= width= height=`: an invisible rectangle
   with a tag, touched like a prefab.
4. **A free heading, an acceleration, and a deflection.** `heading="x,y"` and
   `accel=` on a flying prefab; `qg:deflect axis=` (reflect) or `dx= dy=`
   (set), on `me` or `other`; `qg:respawn target="other"` for a thing.
5. **Frames that are not square.** `tile="8x32"` on `qg:spritesheet`.
6. **A picture.** `qg:sprite sheet= x= y=`, with no behaviour.

And one built-in: `random(a, b)` in expressions, from the scene's seeded
source, so a replay is the same every time.

Still missing after Pong, left for the next game: joypad bindings and analog
strength on `qg:input`; a score (the demo has none).

## Over the network

`pong.q` declares `<qg:multiplayer players="2" start="court" />` and its title
is a `<qg:lobby local="court" />`: two on one keyboard, or one player on each
machine — one chooses Host a game, the other types the host's address and
chooses Join, and the court starts on both. Both run the whole game in
lockstep (`PLAN_MULTIPLAYER.md`): the demo's random slant comes from the scene
seed, so both see the same ball. The command line still skips the title:

```
godot --path projects/pong/godot -- --q-host=7777          # player 1, the left paddle
godot --path projects/pong/godot -- --q-join=HOST:7777     # player 2, the right one
```

`tests/godot/test_godot_multiplayer.py` runs two headless Godots on
localhost, over ENet and over WebSocket: through the title's own Host and
Join buttons, and by the command line; the courts agree with each other,
and with one Godot replaying both tapes.

## The test

`tests/godot/test_godot_pong.py` replays the game in Godot: the ball's
first tick and its acceleration, the left paddle's return at a random slant
(the same with the same seed), the ceiling and the reset past a paddle, and
each paddle on its own player's keys, stopped at the court's edge.
