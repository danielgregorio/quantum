extends Node
# Declarative multiplayer (qg:multiplayer): deterministic lockstep.
#
# A Quantum game is a deterministic simulation: every rule runs in the
# physics tick, the only random source is the scene's seed, and the
# players reach it through input actions. So two copies of the game that
# see the same actions on the same ticks are the same game — the replay
# harness proves it in CI. Multiplayer is then only this: every peer runs
# the whole game; each tick, each peer sends what its player pressed, and
# a tick runs when every player's input for it is known. There is no
# server-side state, nothing to synchronise, no prediction; `delay` ticks
# of input latency hide the round trip.
#
# One peer hosts (--q-host=PORT: it is player 1), the others join
# (--q-join=HOST:PORT) and are players 2.. in the order they connect. The
# game starts when all `players` are there. This node samples the local
# keys (player 1's actions, whatever player this peer is), schedules them
# `delay` ticks ahead for its own player, and gives Q the input of every
# player for the tick (Q.set_input) — the game reads nothing else.
# Every `check_every` ticks the peers compare a hash of the whole state: a
# difference is a desync, reported and fatal, never silent.

var ACTIONS: Array = ["left", "right", "up", "down", "jump"]   # the game's, from game.json

var players: int = 2
var delay: int = 3
var check_every: int = 60
var port: int = 7777
var host: String = ""          # "" when hosting

var tick: int = 0              # the simulation tick about to run
var player: int = 0            # this peer's player number, 0 until assigned
var started: bool = false
var desynced: bool = false
var ended: bool = false        # a peer left: the game runs out its known ticks, then stalls for good
var game: Node = null

var _frames: Dictionary = {}   # tick -> {player: mask}
var _hashes: Dictionary = {}   # tick -> {player: hash}
var _peers: Dictionary = {}    # peer id -> player number (host only)
var _retries: int = 0
var _stalled: bool = false


func setup(spec: Dictionary, game_: Node, host_: String, port_: int) -> void:
	game = game_
	ACTIONS = game_.spec.get("actions", ACTIONS)
	players = int(spec.get("players", 2))
	delay = int(spec.get("delay", 3))
	check_every = int(spec.get("check_every", 60))
	host = host_
	port = port_
	name = "Lockstep"
	process_physics_priority = -100   # before every node of the scene
	var peer := ENetMultiplayerPeer.new()
	if host == "":
		var err := peer.create_server(port, players - 1)
		if err != OK:
			push_error("quantum: cannot host on port %d (%d)" % [port, err])
			return
		player = 1
		_peers[1] = 1
		multiplayer.peer_connected.connect(_on_peer_connected)
		multiplayer.peer_disconnected.connect(_on_peer_gone)
		print("quantum: hosting on port %d, waiting for %d more player(s)" % [port, players - 1])
		if players == 1:
			_begin()
	else:
		peer.create_client(host, port)
		multiplayer.connected_to_server.connect(func(): print("quantum: connected to " + host))
		multiplayer.connection_failed.connect(_on_connection_failed)
		multiplayer.server_disconnected.connect(_on_peer_gone.bind(1))
	multiplayer.multiplayer_peer = peer


# --- joining ---

func _on_peer_connected(id: int) -> void:
	var n := _peers.size() + 1
	if n > players:
		multiplayer.multiplayer_peer.disconnect_peer(id)
		return
	_peers[id] = n
	_assign.rpc_id(id, n)
	print("quantum: player %d joined" % n)
	if _peers.size() == players:
		_begin()
		_start.rpc()


func _on_connection_failed() -> void:
	_retries += 1
	if _retries > 20:
		push_error("quantum: cannot reach %s:%d" % [host, port])
		get_tree().quit(2)
		return
	await get_tree().create_timer(0.5).timeout
	var peer := ENetMultiplayerPeer.new()
	peer.create_client(host, port)
	multiplayer.multiplayer_peer = peer


func _on_peer_gone(_id: int) -> void:
	push_warning("quantum: a player left at tick %d" % tick)
	ended = true


func stalled() -> bool:
	return _stalled


@rpc("authority", "call_remote", "reliable")
func _assign(n: int) -> void:
	player = n


@rpc("authority", "call_remote", "reliable")
func _start() -> void:
	_begin()


func _begin() -> void:
	# the first `delay` ticks have no input from anyone: the pipeline fills
	for t in range(delay):
		_frames[t] = {}
		for p in range(1, players + 1):
			_frames[t][p] = [0, 0.0, 0.0]
	started = true
	Q.external_input = true
	game.call("_q_lockstep_ready")


# --- every tick ---

func _physics_process(_delta: float) -> void:
	if not started or desynced:
		return
	var scene: Node = game.current_scene
	if scene == null:
		return
	# 1. what this player presses now runs `delay` ticks from now, everywhere
	var mask := 0
	for i in ACTIONS.size():
		if Input.is_action_pressed(ACTIONS[i]):
			mask |= 1 << i
	var ahead := tick + delay
	if not _frames.has(ahead):
		_frames[ahead] = {}
	if not _frames[ahead].has(player):
		var raw: Vector2 = Q.raw_cursor
		_frames[ahead][player] = [mask, raw.x, raw.y]
		if not ended:
			_frame.rpc(player, ahead, mask, raw.x, raw.y)
	# 2. this tick runs only when every player's input for it is here
	var frame: Dictionary = _frames.get(tick, {})
	if frame.size() < players:
		if not _stalled:
			_stalled = true
			scene.process_mode = Node.PROCESS_MODE_DISABLED
		return
	if _stalled:
		_stalled = false
		scene.process_mode = Node.PROCESS_MODE_INHERIT
	var input := {}
	for p in range(1, players + 1):
		var entry: Array = frame[p]
		var m: int = int(entry[0])
		Q.cursors[p] = Vector2(float(entry[1]), float(entry[2]))
		for i in ACTIONS.size():
			if m & (1 << i):
				input[ACTIONS[i] if p == 1 else "p%d_%s" % [p, ACTIONS[i]]] = 1.0
	Q.set_input(input)
	# 3. the state everyone must agree on
	if check_every > 0 and tick > 0 and tick % check_every == 0 and scene.has_method("quantum_state"):
		var h := hash(JSON.stringify(scene.quantum_state(), "", true))
		_report(tick, player, h)
		if not ended:
			_hash.rpc(player, tick, h)
	_frames.erase(tick - delay - 1)
	tick += 1


@rpc("any_peer", "call_remote", "reliable")
func _frame(p: int, t: int, mask: int, cx: float, cy: float) -> void:
	if not _frames.has(t):
		_frames[t] = {}
	_frames[t][p] = [mask, cx, cy]


@rpc("any_peer", "call_remote", "reliable")
func _hash(p: int, t: int, h: int) -> void:
	_report(t, p, h)


func _report(t: int, p: int, h: int) -> void:
	if not _hashes.has(t):
		_hashes[t] = {}
	_hashes[t][p] = h
	if _hashes[t].size() < players:
		return
	var values: Array = _hashes[t].values()
	for v in values:
		if v != values[0]:
			desynced = true
			push_error("quantum: desync at tick %d — the players' games differ (%s)" % [t, str(_hashes[t])])
			game.current_scene.process_mode = Node.PROCESS_MODE_DISABLED
			return
	_hashes.erase(t)
