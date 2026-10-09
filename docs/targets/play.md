---
title: Play the games
outline: [2, 3]
---

# Play the games

Eight games written in the game language, each a single `.q` file in
[`projects/`](https://github.com/danielgregorio/quantum/tree/main/projects), built by
`quantum run`, replayed in CI from input tapes, and exported here by Godot
4.4.1 for the browser, Linux and Windows. The browser builds run as
they are; the desktop builds are a zip with one executable inside (on Linux,
`chmod +x` it first). The site rebuilds them from `main` with
`scripts/export-games.py`.

Pong, Arena, Chess and Towers are played by two, on one keyboard or over the
network: on the title, one machine chooses **Host a game**, the other types
the host's address and chooses **Join**, and both run the same game in
lockstep (`PLAN_MULTIPLAYER.md` in the repository says how). Over the network
it takes the desktop builds: a browser cannot host, and joining from a page
served over HTTPS needs a secure WebSocket the games do not offer yet. The
command line skips the title:

```
./pong.x86_64 -- --q-host=7777            # player 1 hosts on port 7777
./pong.x86_64 -- --q-join=HOST:7777       # player 2 joins
```

| Game | What it is | Play | Download | Source |
|---|---|---|---|---|
| **Hopper** | A platformer: a world map, three levels (one drawn in Tiled), a block with a power-up, walkers to stomp, a pit, a checkpoint, spikes, a flag | [browser](https://quantumframework.net/games/hopper/) | [Linux](https://quantumframework.net/games/hopper/hopper-linux.zip) · [Windows](https://quantumframework.net/games/hopper/hopper-windows.zip) | [hopper.q](https://github.com/danielgregorio/quantum/blob/main/projects/hopper/hopper.q) |
| **Keep** | A top-down adventure: six rooms, slimes and bats, a sword, a key and a locked door, a switch that opens a gate elsewhere, a chest | [browser](https://quantumframework.net/games/keep/) | [Linux](https://quantumframework.net/games/keep/keep-linux.zip) · [Windows](https://quantumframework.net/games/keep/keep-windows.zip) | [keep.q](https://github.com/danielgregorio/quantum/blob/main/projects/keep/keep.q) |
| **Drift** | A vertical shooter: three waves from the scene's seed, drones and tanks that shoot, a boss with two phases, a high score kept between runs | [browser](https://quantumframework.net/games/drift/) | [Linux](https://quantumframework.net/games/drift/drift-linux.zip) · [Windows](https://quantumframework.net/games/drift/drift-windows.zip) | [drift.q](https://github.com/danielgregorio/quantum/blob/main/projects/drift/drift.q) |
| **Pong** | Godot's own Pong demo transcribed: two paddles, a ball that bounces; two players on one keyboard or over the network | [browser](https://quantumframework.net/games/pong/) | [Linux](https://quantumframework.net/games/pong/pong-linux.zip) · [Windows](https://quantumframework.net/games/pong/pong-windows.zip) | [pong.q](https://github.com/danielgregorio/quantum/blob/main/projects/pong/pong.q) |
| **Creeps** | Godot's "Dodge the Creeps" tutorial game transcribed: creeps from the border at random speeds, a point a second | [browser](https://quantumframework.net/games/creeps/) | [Linux](https://quantumframework.net/games/creeps/creeps-linux.zip) · [Windows](https://quantumframework.net/games/creeps/creeps-windows.zip) | [creeps.q](https://github.com/danielgregorio/quantum/blob/main/projects/creeps/creeps.q) |
| **Towers** | A tower defense: turrets that shoot the nearest dino, dinos down a road in waves, gold and a base; two builders over the network | [browser](https://quantumframework.net/games/towers/) | [Linux](https://quantumframework.net/games/towers/towers-linux.zip) · [Windows](https://quantumframework.net/games/towers/towers-windows.zip) | [towers.q](https://github.com/danielgregorio/quantum/blob/main/projects/towers/towers.q) |
| **Arena** | A one-on-one fighting game: moves with frame data, blocking, hit stun, rounds on a clock; two players on one keyboard or over the network | [browser](https://quantumframework.net/games/arena/) | [Linux](https://quantumframework.net/games/arena/arena-linux.zip) · [Windows](https://quantumframework.net/games/arena/arena-windows.zip) | [arena.q](https://github.com/danielgregorio/quantum/blob/main/projects/arena/arena.q) |
| **Chess** | Chess, its rules written in the language: castling, en passant, promotion, check, mate, stalemate; white and black on one board or over the network | [browser](https://quantumframework.net/games/chess/) | [Linux](https://quantumframework.net/games/chess/chess-linux.zip) · [Windows](https://quantumframework.net/games/chess/chess-windows.zip) | [chess.q](https://github.com/danielgregorio/quantum/blob/main/projects/chess/chess.q) |

## Controls

- **Hopper**: arrows or WASD, Space/Z/X to jump; on the map, jump enters a level.
- **Keep**: arrows or WASD; Space swings the sword.
- **Drift**: arrows or WASD; Space fires.
- **Pong**: W/S for the left paddle, the arrows for the right one.
- **Creeps**: arrows or WASD; Space or Enter starts.
- **Towers**: the mouse (or the arrows) points, click or Enter builds; `1` and `2` choose the turret; a click on a turret upgrades it.
- **Arena**: player 1 A/D, W jump, S crouch, J punch, K kick; player 2 the arrows, `.` punch, `/` kick. Hold away from the opponent to block.
- **Chess**: click a piece, then a square (white first).

A joypad works everywhere: the pad or the left stick moves, A jumps or
selects, B cancels. Player 2 reads the second joypad.

## The language they are written in

The tags, with every attribute, and each game whole: [Games (Laboratory)](/targets/games).
Each project's `README.md` says what it is, and, for the transcribed ones,
maps the original piece by piece and lists what the language had to grow
to say it.
