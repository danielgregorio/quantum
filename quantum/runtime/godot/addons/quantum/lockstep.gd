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
# One peer hosts (qg:host in a scene, or --q-host=PORT: it is player 1),
# the others join (qg:join, or --q-join=HOST:PORT) and are players 2.. in
# the order they connect. The networked game starts, in qg:multiplayer's
# start= scene, when all `players` are there; `status` says where things
# are for net_status(). The transport is ENet, or WebSocket (the one a
# browser build can join with). This node samples the local
# keys (player 1's actions, whatever player this peer is), schedules them
# `delay` ticks ahead for its own player, and gives Q the input of every
# player for the tick (Q.set_input) — the game reads nothing else.
# Every `check_every` ticks the peers compare a hash of the whole state: a
# difference is a desync, reported and fatal, never silent.
#
# A player who leaves can come back. The host (or the relay) keeps every
# input of the game; when a player leaves, the others wait at the first tick
# without their input ("waiting"), and the next to join takes the free seat:
# the host sends them the inputs so far, and their game runs from the start
# with them, `CATCH_UP_SPEED` times faster than it is played ("catching up"),
# checking the state everyone agreed on, until it is where the others wait.
# Running faster keeps every tick the same: the engine runs more ticks a
# second and slows its clock as much (time_scale), so each tick still steps
# 1/60 of a second. The rollback (rollback.gd) cannot rejoin: a game of it
# ends when a player leaves.
#
# Someone may watch (qg:watch, --q-watch=HOST:PORT): a peer with no seat and
# no input, which runs the game from the inputs the players send everyone.
# One who comes before the game starts starts with it; one who comes later
# gets the inputs so far and catches up, as a rejoining player does. A
# joiner says which it is as it connects (_hello), and only then is given a
# seat, or none. Not under the rollback.

var ACTIONS: Array = ["left", "right", "up", "down", "jump"]   # the game's, from game.json

var players: int = 2
var min_players: int = 0       # qg:multiplayer min-players=: the host may start with this many (0: all of them)
var delay: int = 3
var check_every: int = 60
var port: int = 7777
var host: String = ""          # "" when hosting
var transport: String = "enet"
var from_command_line: bool = false   # started by --q-host/--q-join: a failure ends the process
var status: String = "offline"        # offline, hosting, joining, connected, playing, waiting, catching up, failed, ended
var connected_players: int = 0

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
var relay: bool = false          # --q-relay=PORT: host with no seat, passing the players' inputs on (quantum relay)
var latency_ms: int = 0          # --q-latency=MS: this peer's frames leave that much later (tests)
var _outbox: Array = []          # [due msec, player, tick, mask, cx, cy]
var _log: Dictionary = {}        # tick -> {player: entry}: every input of the game, for a player who rejoins
var _agreed: Dictionary = {}     # tick -> the hash of the state every player reported
var catch_up_to: int = -1        # a rejoining player runs fast up to this tick, the game it missed
var watching: bool = false       # this peer only watches: no seat, no input (qg:watch, --q-watch)
var _watchers: Dictionary = {}   # peer id -> true: the host's (or the relay's) list of those who watch
var _late: Dictionary = {}       # peer id -> true: those who came after the start, or watch (frames handed on)

const CATCH_UP_SPEED := 16       # a power of two: 1/(60*16)*16 is exactly 1/60
const LOG_PART := 200            # ticks of inputs a message carries to a rejoining player
const WS_BUFFER := 1 << 24       # bytes a WebSocket peer holds in each direction
const MAX_WATCHERS := 8          # those who may watch a game besides its players


func setup(spec: Dictionary, game_: Node, host_: String, port_: int) -> void:
	game = game_
	ACTIONS = game_.spec.get("actions", ACTIONS)
	players = int(spec.get("players", 2))
	min_players = int(spec.get("min_players", 0)) if spec.get("min_players") != null else 0
	delay = int(spec.get("delay", 3))
	check_every = int(spec.get("check_every", 60))
	transport = str(spec.get("transport", "enet"))
	if OS.has_feature("web"):
		transport = "websocket"   # a browser has no ENet: the web build joins a WebSocket host
	host = host_
	port = port_
	if host.contains("://"):
		transport = "websocket"   # a relay's URL
	name = "Lockstep"
	process_physics_priority = -100   # before every node of the scene
	if host == "":
		var peer: MultiplayerPeer
		var err: int
		if transport == "enet":
			var enet := ENetMultiplayerPeer.new()
			err = enet.create_server(port, players - 1 + MAX_WATCHERS)
			peer = enet
		else:
			var ws := _websocket()
			err = ws.create_server(port)
			peer = ws
		if err != OK:
			push_error("quantum: cannot host on port %d (%d)" % [port, err])
			status = "failed"
			if from_command_line:
				get_tree().quit(2)
			return
		status = "hosting"
		multiplayer.peer_connected.connect(_on_peer_connected)
		multiplayer.peer_disconnected.connect(_on_peer_gone)
		multiplayer.multiplayer_peer = peer
		if relay:
			# no seat: every player joins, and the peer passes their frames on (server relay)
			print("quantum: relaying on port %d, waiting for %d player(s)" % [port, players])
			return
		player = 1
		_peers[1] = 1
		connected_players = 1
		print("quantum: hosting on port %d, waiting for %d more player(s)" % [port, players - 1])
	else:
		status = "joining"
		multiplayer.connected_to_server.connect(_on_connected)
		multiplayer.connection_failed.connect(_on_connection_failed)
		multiplayer.server_disconnected.connect(_on_peer_gone.bind(1))
		_connect()


# A WebSocket peer with room for a rejoining player's inputs: the host sends
# them all at once, and the default buffers (64 KiB) would drop some.
func _websocket() -> WebSocketMultiplayerPeer:
	var ws := WebSocketMultiplayerPeer.new()
	ws.inbound_buffer_size = WS_BUFFER
	ws.outbound_buffer_size = WS_BUFFER
	ws.max_queued_packets = 65536
	return ws


func _connect() -> void:
	if transport == "enet":
		var enet := ENetMultiplayerPeer.new()
		enet.create_client(host, port)
		multiplayer.multiplayer_peer = enet
	else:
		var ws := _websocket()
		# an address may be a whole URL: wss://relay.example/pong/ROOM (quantum relay)
		ws.create_client(host if host.contains("://") else "ws://%s:%d" % [host, port])
		multiplayer.multiplayer_peer = ws


func _on_connected() -> void:
	status = "connected"
	print("quantum: connected to " + host)
	_hello.rpc_id(1, watching)   # a player, or one who watches: the seat waits for this


# The networked game is over for this peer: back to no network.
func leave() -> void:
	if multiplayer.multiplayer_peer != null:
		multiplayer.multiplayer_peer.close()
		multiplayer.multiplayer_peer = null
	status = "offline"
	Q.external_input = false


# --- joining ---

func _on_peer_connected(_id: int) -> void:
	pass   # its seat, or none, when it says which it is (_hello)


@rpc("any_peer", "call_remote", "reliable")
func _hello(watch: bool) -> void:
	var id := multiplayer.get_remote_sender_id()
	if watch:
		_take_watcher(id)
	else:
		_take_seat(id)


# One who watches: no seat; the inputs so far when the game is under way, which
# it catches up on. The players' frames reach it as they reach every peer.
func _take_watcher(id: int) -> void:
	if not can_rejoin() or _watchers.size() >= MAX_WATCHERS:
		multiplayer.multiplayer_peer.disconnect_peer(id)   # the rollback's ticks are never certain enough
		return
	_watchers[id] = true
	_late[id] = true
	_assign.rpc_id(id, 0)
	_count.rpc_id(id, connected_players)
	print("quantum: someone watches (%d)" % _watchers.size())
	if started:
		_send_log(id)   # else it starts with the players: _start_with goes to every peer


func _take_seat(id: int) -> void:
	var n := 1
	while n in _peers.values():   # the lowest free seat
		n += 1
	if n > players or (started and not can_rejoin()):
		multiplayer.multiplayer_peer.disconnect_peer(id)
		return
	_peers[id] = n
	connected_players = _peers.size()
	_assign.rpc_id(id, n)
	_count.rpc(connected_players)
	if started:
		_late[id] = true
		print("quantum: player %d rejoined at tick %d" % [n, tick])
		_send_log(id)
		status = "relaying" if relay else "playing"
		_seat_taken.rpc()
		return
	print("quantum: player %d joined" % n)
	if _peers.size() == players:
		if relay:
			started = true   # the players play; the relay only passes their frames on
			status = "relaying"
			_fill_pipeline()   # kept as the players have it, for one who rejoins
		else:
			_begin()
		_start_with.rpc(players)


func _on_connection_failed() -> void:
	_retries += 1
	if _retries > 20:
		push_error("quantum: cannot reach %s:%d" % [host, port])
		status = "failed"
		if from_command_line:
			get_tree().quit(2)
		return
	await get_tree().create_timer(0.5).timeout
	if status == "joining":
		_connect()


func _on_peer_gone(_id: int) -> void:
	_late.erase(_id)
	if _watchers.has(_id):
		_watchers.erase(_id)   # one who watched: nothing changes for the players
		return
	if relay:
		_peers.erase(_id)
		connected_players = _peers.size()
		if started and can_rejoin() and not _peers.is_empty():
			_seat_free.rpc()   # the others cannot hear a peer leave: the relay tells them
			status = "waiting"
		elif started:
			_gone.rpc()
			status = "ended"
		else:
			_count.rpc(connected_players)
		return
	if started and player == 1 and _id != 1 and can_rejoin():
		# the host keeps the game: the seat waits for the next to join
		push_warning("quantum: a player left at tick %d; waiting for someone to take the seat" % tick)
		_peers.erase(_id)
		connected_players = _peers.size()
		status = "waiting"
		_seat_free.rpc()
		return
	push_warning("quantum: a player left at tick %d" % tick)
	ended = true
	if started:
		status = "ended"
	elif player == 1:
		# before the game: a seat is free again
		for k in _peers.keys():
			if k == _id:
				_peers.erase(k)
		connected_players = _peers.size()
		ended = false
	else:
		status = "failed"


# A tick waits for the others' input: the scene stands still. Its collision
# objects stay in the physics while it does (they would leave it, the default
# for a disabled node, and coming back would report every overlap as new: a
# paddle would hit a ball it already hit, on one peer and not the other).
var _kept: Dictionary = {}   # collision object -> its own disable_mode


func _freeze(scene: Node, on: bool) -> void:
	if on:
		_kept.clear()
		for n in _collision_objects(scene):
			_kept[n] = n.disable_mode
			n.disable_mode = CollisionObject2D.DISABLE_MODE_KEEP_ACTIVE
		scene.process_mode = Node.PROCESS_MODE_DISABLED
	else:
		scene.process_mode = Node.PROCESS_MODE_INHERIT
		for n in _kept.keys():
			if is_instance_valid(n):
				n.disable_mode = _kept[n]
		_kept.clear()


static func _collision_objects(n: Node) -> Array:
	var out := []
	if n is CollisionObject2D:
		out.append(n)
	for c in n.get_children():
		out += _collision_objects(c)
	return out


func stalled() -> bool:
	return _stalled


@rpc("authority", "call_remote", "reliable")
func _assign(n: int) -> void:
	player = n


@rpc("authority", "call_remote", "reliable")
func _count(n: int) -> void:
	connected_players = n


# qg:start-now: the game starts with the players who are there, once min_players are. The
# host decides; under a relay, which has no seat, player 1 asks it. From then on the game is
# for that many: `players` is what every tick waits for and every hash is compared across.
func start_now() -> void:
	if started or min_players == 0:
		return
	if player == 1 and not relay and multiplayer.is_server():
		_start_with_those_here()
	elif player == 1:
		_ask_start.rpc_id(1)


@rpc("any_peer", "call_remote", "reliable")
func _ask_start() -> void:
	if relay and _peers.get(multiplayer.get_remote_sender_id(), 0) == 1:
		_start_with_those_here()


func _start_with_those_here() -> void:
	var here := _peers.size()   # the host is in it as player 1; a relay is not in it
	if started or here < min_players:
		return
	players = here
	print("quantum: starting with %d player(s)" % players)
	if relay:
		started = true
		status = "relaying"
		_fill_pipeline()
	else:
		_begin()
	_start_with.rpc(players)


@rpc("authority", "call_remote", "reliable")
func _start_with(n: int) -> void:
	players = n
	_begin()


@rpc("authority", "call_remote", "reliable")
func _gone() -> void:
	_on_peer_gone(0)


@rpc("authority", "call_remote", "reliable")
func _seat_free() -> void:
	status = "waiting"
	connected_players -= 1


@rpc("authority", "call_remote", "reliable")
func _seat_taken() -> void:
	if status == "waiting":
		status = "playing"
	connected_players = players


# Whether a player who leaves can come back (not under the rollback).
func can_rejoin() -> bool:
	return true


# --- rejoining ---

# The host to the player taking a free seat: the inputs so far, a part at a
# time (a WebSocket message has a size limit), then what everyone agreed on.
func _send_log(id: int) -> void:
	var ticks: Array = _log.keys()
	ticks.sort()
	var part := {}
	for t in ticks:
		part[t] = _log[t]
		if part.size() >= LOG_PART:
			_log_part.rpc_id(id, part)
			part = {}
	if not part.is_empty():
		_log_part.rpc_id(id, part)
	_log_done.rpc_id(id, _agreed, _log.size())


# Merged into what is here: a player's frame for one of these ticks may have come
# straight from them before the host's part did (both reach a newcomer), and a part
# that replaced it would leave that tick waiting for good.
@rpc("authority", "call_remote", "reliable")
func _log_part(part: Dictionary) -> void:
	for t in part:
		if not _log.has(int(t)):
			_log[int(t)] = {}
		for p in part[t]:
			_log[int(t)][int(p)] = part[t][p]


@rpc("authority", "call_remote", "reliable")
func _log_done(agreed: Dictionary, count: int) -> void:
	for t in range(count):   # the host's are every tick from the first: none may be missing
		if not _log.has(t):
			# a part was lost on the way: the game cannot be caught up, say so rather than wait
			push_error("quantum: rejoining got no inputs for tick %d of %d" % [t, count])
			status = "failed"
			return
	for t in agreed:
		_agreed[int(t)] = int(agreed[t])
	for t in _log:
		if not _frames.has(t):
			_frames[t] = {}
		for p in _log[t]:
			_frames[t][p] = _log[t][p]
	var last := count - 1
	catch_up_to = last
	started = true
	status = "catching up"
	connected_players = players
	Q.external_input = true
	_speed(CATCH_UP_SPEED)
	print("quantum: rejoining as player %d: catching up %d ticks" % [player, last + 1])
	game.call("_q_lockstep_ready")


# The engine runs k times as many ticks a second, each still 1/60 of a second.
func _speed(k: int) -> void:
	Q.catch_up = k
	Q.apply_clock()   # with the game's own speed (qg:time-scale), if it is in slow motion


func _begin() -> void:
	_fill_pipeline()
	started = true
	status = "watching" if watching else "playing"
	connected_players = players
	Q.external_input = true
	game.call("_q_lockstep_ready")


# The first `delay` ticks have no input from anyone: the pipeline fills.
func _fill_pipeline() -> void:
	for t in range(delay):
		_frames[t] = {}
		for p in range(1, players + 1):
			_frames[t][p] = [0, 0.0, 0.0]
		_log[t] = _frames[t].duplicate()


# --- every tick ---

func _physics_process(_delta: float) -> void:
	if not started or desynced or relay:
		return
	var scene: Node = game.current_scene
	if scene == null:
		return
	# 1. what this player presses now runs `delay` ticks from now, everywhere
	var mask := 0
	var local: Dictionary = Q.sample_local()   # held, and tapped since the last tick
	for i in ACTIONS.size():
		if local.has(ACTIONS[i]):
			mask |= 1 << i
	var ahead := tick + delay
	if not _frames.has(ahead):
		_frames[ahead] = {}
	if player > 0 and not _frames[ahead].has(player):
		var raw: Vector2 = Q.raw_cursor
		_frames[ahead][player] = [mask, raw.x, raw.y]
		_keep(player, ahead, _frames[ahead][player])
		if not ended:
			_send_frame(player, ahead, mask, raw.x, raw.y)
	# 2. this tick runs only when every player's input for it is here
	var frame: Dictionary = _frames.get(tick, {})
	if frame.size() < players:
		if not _stalled:
			_stalled = true
			_freeze(scene, true)
		return
	if _stalled:
		_stalled = false
		_freeze(scene, false)
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
		if tick <= catch_up_to or player == 0:
			# the game this player missed (or watches): it must be the one the others played
			if _agreed.has(tick) and _agreed[tick] != h:
				_desync(tick, "the game caught up differs from the one played (%d, not %d)" % [h, _agreed[tick]])
				return
		else:
			_report(tick, player, h)
			if not ended:
				_hash.rpc(player, tick, h)
	_frames.erase(tick - delay - 1)
	tick += 1
	if catch_up_to >= 0 and tick > catch_up_to:
		catch_up_to = -1
		_speed(1)
		status = "watching" if watching else "playing"
		print("quantum: caught up at tick %d" % tick)


func _send_frame(p: int, t: int, mask: int, cx: float, cy: float) -> void:
	if latency_ms <= 0:
		_frame.rpc(p, t, mask, cx, cy)
	else:
		_outbox.append([Time.get_ticks_msec() + latency_ms, p, t, mask, cx, cy])


var _reported: String = ""


func _process(_delta: float) -> void:
	# a web page says where its network is (window.quantumNet): "playing", "playing desync"...
	var said := status + (" desync" if desynced else "")
	if said != _reported:
		_reported = said
		Q.web_report("quantumNet", said)
		_show_notice()
	var now := Time.get_ticks_msec()
	while not _outbox.is_empty() and int(_outbox[0][0]) <= now and not ended:
		var f: Array = _outbox.pop_front()
		_frame.rpc(f[1], f[2], f[3], f[4], f[5])


# --- what the players are told while the game cannot go on as usual ---

const NOTICES := {
	"waiting": "Waiting for the other player to come back",
	"catching up": "Catching up",
	"ended": "The other player left",
}
var _notice: Label = null


# The notice for where the network is, over the scene, in the player's
# language ("" when the game goes on as usual). The relay shows nothing.
func notice() -> String:
	if relay or not started:
		return ""
	if desynced:
		return "The games differ: the match stopped"
	return NOTICES.get(status, "")


func _show_notice() -> void:
	var text := notice()
	Q.web_report("quantumNotice", Q.translate(text))
	if text == "":
		if _notice != null:
			_notice.get_parent().visible = false
		return
	if _notice == null:
		var layer := CanvasLayer.new()
		layer.layer = 100   # over the scene and its HUD
		layer.name = "Notice"
		var panel := PanelContainer.new()
		panel.set_anchors_preset(Control.PRESET_CENTER)
		var box := StyleBoxFlat.new()
		box.bg_color = Color(0, 0, 0, 0.75)
		box.set_content_margin_all(12)
		panel.add_theme_stylebox_override("panel", box)
		_notice = Label.new()
		_notice.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		panel.add_child(_notice)
		layer.add_child(panel)
		add_child(layer)
	_notice.text = text   # a Label shows its text translated (qg:language)
	var panel_node: Control = _notice.get_parent()
	panel_node.reset_size()
	panel_node.position = (get_viewport().get_visible_rect().size - panel_node.size) / 2.0
	_notice.get_parent().get_parent().visible = true


# What a player reads (the play protocol): the notice, while there is one.
func quantum_view() -> Dictionary:
	var text := notice()
	return {} if text == "" else {"kind": "notice", "text": Q.translate(text)}


@rpc("any_peer", "call_remote", "reliable")
func _frame(p: int, t: int, mask: int, cx: float, cy: float) -> void:
	_keep(p, t, [mask, cx, cy])
	# the host (or the relay) hands every player's frame to those who came late or watch: Godot's own
	# relay of a frame that reaches the host as one joins may miss them, and they would wait for good
	for w in _late:
		if w != multiplayer.get_remote_sender_id():
			_frame.rpc_id(w, p, t, mask, cx, cy)
	if relay:
		return   # passed on by the multiplayer API itself; kept only for a player who rejoins
	if not _frames.has(t):
		_frames[t] = {}
	_frames[t][p] = [mask, cx, cy]


# Every input, for a player who rejoins (only the host, or the relay, sends it).
func _keep(p: int, t: int, entry: Array) -> void:
	if not _log.has(t):
		_log[t] = {}
	_log[t][p] = entry


@rpc("any_peer", "call_remote", "reliable")
func _hash(p: int, t: int, h: int) -> void:
	if relay:
		if not _agreed.has(t):
			_agreed[t] = h   # the players compare among themselves; this is for one who rejoins
		return
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
			_desync(t, "the players' games differ (%s)" % str(_hashes[t]))
			return
	_agreed[t] = values[0]
	_hashes.erase(t)


func _desync(t: int, why: String) -> void:
	desynced = true
	push_error("quantum: desync at tick %d — %s" % [t, why])
	game.current_scene.process_mode = Node.PROCESS_MODE_DISABLED
