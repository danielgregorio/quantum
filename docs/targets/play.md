---
title: Play the games
outline: [2, 3]
---

# Play the games

**[All the games on one page →](https://quantumframework.net/games/)**

Twelve games written in the game language, each a single `.q` file in
[`projects/`](https://github.com/danielgregorio/quantum/tree/main/projects), built by
`quantum run`, replayed in CI from input tapes, and exported here by Godot
4.4.1 for the browser, Linux and Windows. The browser builds run as
they are; the desktop builds are a zip with one executable inside (on Linux,
`chmod +x` it first). The site rebuilds them from `main` with
`scripts/export-games.py`. Each game's source has a page of its own (the
Source column below, or **View the source** on the games page): every line
highlighted and numbered, each tag a link to its entry in
[the reference](/targets/games), and what a tag or an attribute does shown
when it is pointed at.

Pong, Arena, Chess and Towers are played by two, on one keyboard or over the
network: on the title, one machine chooses **Host a game**, the other types
the host's address and chooses **Join**, and both run the same game in
lockstep (`PLAN_MULTIPLAYER.md` in the repository says how). Bricks is played
by two to four, each on their own machine: it starts as the fourth joins, or
when the host chooses **Start now** with two or three. The command line skips
the title:

```
./pong.x86_64 -- --q-host=7777            # player 1 hosts on port 7777
./pong.x86_64 -- --q-join=HOST:7777       # player 2 joins
```

### Two browsers, through a relay

A web page cannot host, so two people in their browsers meet at a relay:
`quantum relay`, a small server that opens a room for each name it is
asked for. Each room runs the game itself in a headless Godot that takes
no seat and passes each player's inputs on to the other. A page served
over HTTPS, like this site, may only open a secure WebSocket, so the
relay needs a domain and a certificate:

```
pip install "quantum[websocket]"
quantum relay --port 443 --cert fullchain.pem --key privkey.pem
```

Then both players open the same link, with any room name they agree on,
and choose **Join** on the title (the address field already holds the room):

```
https://quantumframework.net/games/pong/?join=wss://relay.example.com/pong/friday-night
```

The first to join is player 1. The relay never sees the game, only the
inputs. Every second the lockstep compares the two games and reports any
difference. A player who leaves (a closed tab, a lost connection) can come
back: the other waits, and whoever opens the same link and joins takes the
seat, catching up the game so far in a few seconds. When the last player
leaves, the room closes. Without a
certificate, `quantum relay --port 8765` serves `ws://`, which is enough
on a local network with a page served over plain HTTP. A desktop build
joins the same rooms: `--q-join=wss://relay.example.com/pong/friday-night`.

### Running the relay

`deploy/relay/Dockerfile` is the relay as a container. It holds Godot and
the networked games, compiled when the image is built, and listens on
plain `ws://` on port 8080. The host in front of it gives it HTTPS. A
request without a WebSocket upgrade (`GET /health`) answers what the relay
holds, as JSON, for the host's health checks.

On [Fly.io](https://fly.io), from the repository's root
(`deploy/relay/fly.toml` says the same):

```
fly launch --no-deploy --copy-config --config deploy/relay/fly.toml --name my-quantum-relay
fly deploy --config deploy/relay/fly.toml --dockerfile deploy/relay/Dockerfile
fly scale count 1 --config deploy/relay/fly.toml
```

The players then join `wss://my-quantum-relay.fly.dev/pong/ROOM`. Keep one
machine: a room lives on the machine its first player reached. Any host
that runs a container and terminates TLS works the same way (Render,
Railway, a server behind Caddy or nginx).

To give the games page a **Play online** button on each networked game,
set the repository variable `QUANTUM_RELAY_URL` to the relay's address
(`wss://my-quantum-relay.fly.dev`). The site's next build adds the button.
It makes a room of its own and a link to send to a friend.

| Game | What it is | Play | Download | Source |
|---|---|---|---|---|
| **Hopper** | A platformer: a world map, four levels (one drawn in Tiled), a block with a power-up, walkers to stomp, a pit, a checkpoint, spikes, a flag; the fourth with water to swim, snow that slides, a ladder and a hopping enemy | [browser](https://quantumframework.net/games/hopper/) | [Linux](https://quantumframework.net/games/hopper/hopper-linux.zip) · [Windows](https://quantumframework.net/games/hopper/hopper-windows.zip) | [hopper.q](https://quantumframework.net/games/hopper/source/) |
| **Keep** | A top-down adventure: six rooms, slimes and bats, a sword, a key and a locked door, a switch that opens a gate elsewhere, a chest | [browser](https://quantumframework.net/games/keep/) | [Linux](https://quantumframework.net/games/keep/keep-linux.zip) · [Windows](https://quantumframework.net/games/keep/keep-windows.zip) | [keep.q](https://quantumframework.net/games/keep/source/) |
| **Delve** | A dungeon crawl: a wall a lever opens and the skeletons that come through it, crushers, a skeleton archer, a vault two levers keep shut; alone, or two delvers over the network | [browser](https://quantumframework.net/games/delve/) | [Linux](https://quantumframework.net/games/delve/delve-linux.zip) · [Windows](https://quantumframework.net/games/delve/delve-windows.zip) | [delve.q](https://quantumframework.net/games/delve/source/) |
| **Drift** | A vertical shooter: three waves from the scene's seed, drones and tanks that shoot, a boss with two phases, a high score kept between runs | [browser](https://quantumframework.net/games/drift/) | [Linux](https://quantumframework.net/games/drift/drift-linux.zip) · [Windows](https://quantumframework.net/games/drift/drift-windows.zip) | [drift.q](https://quantumframework.net/games/drift/source/) |
| **Pong** | Godot's own Pong demo transcribed: two paddles, a ball that bounces; two players on one keyboard or over the network | [browser](https://quantumframework.net/games/pong/) | [Linux](https://quantumframework.net/games/pong/pong-linux.zip) · [Windows](https://quantumframework.net/games/pong/pong-windows.zip) | [pong.q](https://quantumframework.net/games/pong/source/) |
| **Bricks** | A brick breaker: three levels, steel bricks, bombs that break their neighbours, the last brick in slow motion; alone, or two to four paddles over the network | [browser](https://quantumframework.net/games/bricks/) | [Linux](https://quantumframework.net/games/bricks/bricks-linux.zip) · [Windows](https://quantumframework.net/games/bricks/bricks-windows.zip) | [bricks.q](https://quantumframework.net/games/bricks/source/) |
| **Creeps** | Godot's "Dodge the Creeps" tutorial game transcribed: creeps from the border at random speeds, a point a second | [browser](https://quantumframework.net/games/creeps/) | [Linux](https://quantumframework.net/games/creeps/creeps-linux.zip) · [Windows](https://quantumframework.net/games/creeps/creeps-windows.zip) | [creeps.q](https://quantumframework.net/games/creeps/source/) |
| **Towers** | A tower defense: turrets that shoot the nearest dino, dinos down a road in waves, gold and a base; two builders over the network | [browser](https://quantumframework.net/games/towers/) | [Linux](https://quantumframework.net/games/towers/towers-linux.zip) · [Windows](https://quantumframework.net/games/towers/towers-windows.zip) | [towers.q](https://quantumframework.net/games/towers/source/) |
| **Arena** | A one-on-one fighting game: moves with frame data, blocking, hit stun, rounds on a clock; two players on one keyboard or over the network | [browser](https://quantumframework.net/games/arena/) | [Linux](https://quantumframework.net/games/arena/arena-linux.zip) · [Windows](https://quantumframework.net/games/arena/arena-windows.zip) | [arena.q](https://quantumframework.net/games/arena/source/) |
| **Chess** | Chess, its rules written in the language: castling, en passant, promotion, check, mate, stalemate; white and black on one board or over the network | [browser](https://quantumframework.net/games/chess/) | [Linux](https://quantumframework.net/games/chess/chess-linux.zip) · [Windows](https://quantumframework.net/games/chess/chess-windows.zip) | [chess.q](https://quantumframework.net/games/chess/source/) |
| **Robot** | Godot's "Platformer 2D" demo transcribed: slopes and ledges, a robot that runs, jumps twice and shoots, crawling enemies, coins, lifts, a pause menu | [browser](https://quantumframework.net/games/robot/) | [Linux](https://quantumframework.net/games/robot/robot-linux.zip) · [Windows](https://quantumframework.net/games/robot/robot-windows.zip) | [robot.q](https://quantumframework.net/games/robot/source/) |
| **RPG** | Godot's "JRPG" demo transcribed: a slime walks a grassy map cell by cell, talks, and fights another slime turn by turn | [browser](https://quantumframework.net/games/rpg/) | [Linux](https://quantumframework.net/games/rpg/rpg-linux.zip) · [Windows](https://quantumframework.net/games/rpg/rpg-windows.zip) | [rpg.q](https://quantumframework.net/games/rpg/source/) |

## Controls

- **Hopper**: arrows or WASD, Space/Z/X to jump; on the map, jump enters a level. On a ladder, up and down climb; in water, each jump is a stroke.
- **Keep**: arrows or WASD; Space swings the sword.
- **Delve**: arrows or WASD; Space swings the sword; walk into a lever to pull it. Escape leaves the lobby.
- **Drift**: arrows or WASD; Space fires.
- **Pong**: W/S for the left paddle, the arrows for the right one.
- **Creeps**: arrows or WASD; Space or Enter starts.
- **Towers**: the mouse (or the arrows) points, click or Enter builds; `1` and `2` choose the turret; a click on a turret upgrades it.
- **Arena**: player 1 A/D, W jump, S crouch, J punch, K kick; player 2 the arrows, `.` punch, `/` kick. Hold away from the opponent to block.
- **Chess**: click a piece, then a square (white first).
- **Robot**: arrows or A/D; Up, W or the joypad's A jumps (again in the air); Space, Z or Ctrl shoots; Escape pauses.
- **RPG**: arrows or WASD walk (two at once, diagonally); walk into someone to talk; Enter, Space or a click shows the next line; in the fight, Attack, Defend, Potion or Flee.

A joypad works everywhere: the pad or the left stick moves, A jumps or
selects, B cancels. Player 2 reads the second joypad.

## The language they are written in

The tags, with every attribute, and each game whole: [Games (Laboratory)](/targets/games).
Each project's `README.md` says what it is, and, for the transcribed ones,
maps the original piece by piece and lists what the language had to grow
to say it.
