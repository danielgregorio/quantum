# Arena — a fighting game, and the fighting games' own netcode

`arena.q` is a one-on-one fighting game in the shape of the arcade classics:
two fighters on a stage, walk, jump, crouch, block by holding away, a punch
and a kick with frame data, hit stun and push back, health bars, a 99-second
clock, best of three rounds. It was not transcribed from a repository: no
complete open-source Godot fighter with a usable licence turned up (the
candidates are in the project's log), so it was written to see what a
fighting game asks of the language. The sprites are placeholders drawn for
the repository (`assets/LICENSE.md`); a CC0 sheet such as "Godinez Fighter"
replaces them frame for frame.

Run it: `quantum run projects/arena/arena.q`, then open `projects/arena/godot`
in Godot. Player 1: A/D, W jump, S crouch, J punch, K kick. Player 2 on the
same keyboard: the arrows, `.` punch, `/` kick. Over the network, the title's
Host and Join, with **rollback** (`<qg:multiplayer rollback="8" delay="2" />`):
each machine plays on at once, guessing the other's input, and runs the last
ticks again when a guess was wrong — the fighting games' own netcode
(`PLAN_MULTIPLAYER.md`). From the command line:

```
godot --path projects/arena/godot -- --q-host=7777          # player 1
godot --path projects/arena/godot -- --q-join=HOST:7777     # player 2
```

## What a fighter is, in tags

```xml
<qg:character id="p1" controller="fighter" player="1" sheet="red" x="200" y="252" hitbox="40x90"
              speed="140" jump-height="100" health="100" facing="right">
  <qg:animation name="idle" frames="0" />      <!-- walk, jump, crouch, block, hit, ko -->
  <qg:move name="punch" action="punch" frames="6, 7, 8" fps="15" active="1"
           reach="36x20" at="40,-10" damage="8" stun="14" push="40" />
  <qg:on-ko> ... </qg:on-ko>
</qg:character>
```

- **`controller="fighter"`**: faces the other fighter of the scene, walks,
  jumps (`jump`), crouches (`down`), blocks when holding away from the
  opponent while the opponent attacks, stands on the y it was placed at.
- **`qg:move`**: an attack on an action, as an animation with one active
  frame. In that frame a box of `reach` centred `at` (forward, down) is
  tested once against the opponent's body: a hit takes `damage`, stuns
  `stun` ticks, pushes `push` pixels; a block takes no damage and half the
  rest. Frame data is the language's own: no script.
- **`qg:on-ko`**: runs once at 0 health with `me` the loser and `other` the
  winner; the scene keeps the rounds.
- **`qg:bar bind="p1.health"`** in the HUD; `p1.health` in expressions and
  `qg:respawn target="p1"` in the scene's own logic — a character's id is a
  name in its scene.

## What the language had to grow

1. `controller="fighter"` with `health=`, `facing=`, `qg:move` and `qg:on-ko`.
2. `qg:bar` in the HUD, bound to a q:set or to a fighter's health.
3. A character's id as a name in the scene's expressions and as the target
   of its actions (`qg:respawn target="p2"` from a `q:function`).

Still missing: special moves from input sequences (a quarter circle), air
attacks and throws, a character select screen.

## The test

`tests/godot/test_godot_arena.py` replays it: a punch and a kick land for
their damage and push, a block takes none, kicks to a KO give the round and
the second round starts with both at their marks, two peers fight the same
fight, and — with 30 to 120 ms of latency injected — two rollback peers end
where one replay of both tapes ends, through two rounds and the result.
