extends RefCounted
# qg:connect: the game's door into a world, `quantum gameserver run`'s (PLAN_GAME_SERVER.md). It speaks the
# server's protocol (quantum/runtime/gameserver/server.py) on a WebSocket, polled once a tick by Q: what the player
# sees of each view (views[name][id], the entity's fields as the server sent them: the public ones, and the
# player's own entity's private ones), the player's own entity (you), and the events and refusals of the ticks the
# scene has not heard yet (its qg:on-event and qg:on-refused take them).
#
# Nothing of the world's is decided here: a qg:send asks, the server answers with the tick. The game draws what it
# is told (mirror.gd) and says what it was refused. One thing it guesses (Phase 3): a step of a command with
# predict="true" is shown at once, if the tile is not one of the world's walls, and taken back when the world
# refuses it (the hero walks back: no jump). --q-latency=MS holds every message half that long each way, counted in
# the game's ticks, so a stepped test of it is exact.

const DIRS := {"north": Vector2i(0, -1), "south": Vector2i(0, 1), "east": Vector2i(1, 0), "west": Vector2i(-1, 0),
	"northeast": Vector2i(1, -1), "northwest": Vector2i(-1, -1), "southeast": Vector2i(1, 1),
	"southwest": Vector2i(-1, 1)}

const MAX_HEARD := 256      # events or refusals kept for a scene that does not hear them (a title, an overlay)

var url := ""
var player := ""            # the name it said hello with
var peer: WebSocketPeer = null
var status := "offline"     # offline, connecting, in (the world let it in), closed
var reason := ""            # why it closed: the server's words, or the network's
var you := ""               # the id of the player's entity ("hero:ana")
var tick := 0               # the world's tick, as its last frame said
var rate := 10              # the world's ticks a second
var world_name := ""
var views: Dictionary = {}  # a view's name -> {id: the entity}
var events: Array = []      # [{name, value, at?, of?}], not yet heard
var refused: Array = []     # [{seq, name, reason}], not yet heard
var _pending: Array = []    # what was sent before the connection opened
var _hello := false
var _seq := 0
var sent := 0               # messages written to the world
var latency := 0            # ticks each message is held, each way (--q-latency=MS)
var _out: Array = []        # [tick, message] held
var _in: Array = []         # [tick, message] held
var _frame := 0
var predict: Dictionary = {}    # a command -> the param that says its step's way
var walls: Dictionary = {}      # Vector2i -> true: the world's walls, as the server keeps them
var map_size := Vector2i.ZERO
var step_ticks := 6             # the hero's step, in the game's ticks
var _guess: Array = []          # [seq, tile]: the steps shown before the world said yes
var _guessed_at := -1000


func setup(spec: Dictionary, latency_ms: int) -> void:
	predict = spec.get("predict", {})
	var w: Dictionary = spec.get("walls", {})
	map_size = Vector2i(int(w.get("width", 0)), int(w.get("height", 0)))
	var rows: Array = w.get("rows", [])
	for y in rows.size():
		var row: String = rows[y]
		for x in row.length():
			if row[x] == "1":
				walls[Vector2i(x, y)] = true
	var hero := str(spec.get("hero", ""))
	step_ticks = maxi(1, roundi(float(spec.get("kinds", {}).get(hero, 0.25)) * Engine.physics_ticks_per_second))
	latency = roundi(latency_ms / 2000.0 * Engine.physics_ticks_per_second)


func open(url_: String, name_: String) -> void:
	url = url_
	player = name_
	peer = WebSocketPeer.new()
	peer.inbound_buffer_size = 1 << 23
	peer.outbound_buffer_size = 1 << 20
	var err := peer.connect_to_url(url)
	if err != OK:
		status = "closed"
		reason = "cannot reach %s" % url
		return
	status = "connecting"
	Q.event("world", {"status": status, "url": url, "name": player})


func poll() -> void:
	if peer == null or status == "closed":
		return
	_frame += 1
	peer.poll()
	var state := peer.get_ready_state()
	if state == WebSocketPeer.STATE_OPEN:
		if not _hello:
			_hello = true
			_write({"type": "hello", "name": player})
			for m in _pending:
				_send(m)
			_pending.clear()
		while peer.get_available_packet_count() > 0:
			var data = JSON.parse_string(peer.get_packet().get_string_from_utf8())
			if data is Dictionary:
				if latency > 0:
					_in.append([_frame + latency, data])
				else:
					_apply(data)
		while not _in.is_empty() and int(_in[0][0]) <= _frame:
			_apply(_in.pop_front()[1])
		while not _out.is_empty() and int(_out[0][0]) <= _frame:
			_write(_out.pop_front()[1])
	elif state == WebSocketPeer.STATE_CLOSED:
		status = "closed"
		if reason == "":
			reason = peer.get_close_reason() if peer.get_close_reason() != "" else "the world closed the connection"
		Q.event("world", {"status": status, "reason": reason})


func _apply(m: Dictionary) -> void:
	match str(m.get("type", "")):
		"greeting":
			world_name = str(m.get("world", ""))
			rate = int(m.get("rate", 10))
		"welcome":
			you = str(m.get("you", ""))
			tick = int(m.get("tick", 0))
			status = "in"
			views = {}
			for v in m.get("views", []):
				views[str(v)] = {}
			Q.event("world", {"status": status, "you": you, "tick": tick})
		"tick":
			tick = int(m.get("tick", tick))
			for a in m.get("ack", []):
				_settle(int(a), false)
			for r in m.get("refused", []):
				_keep(refused, r)
				_settle(int(r.get("seq", -1)), true)
			var changed: Dictionary = m.get("views", {})
			for vname in changed:
				var seen: Dictionary = views.get(vname, {})
				var change: Dictionary = changed[vname]
				for e in change.get("enter", []):
					seen[str(e["id"])] = e
				for u in change.get("update", []):
					var id := str(u["id"])
					if seen.has(id):
						var e: Dictionary = seen[id]
						for k in u:
							e[k] = u[k]
				for id in change.get("leave", []):
					seen.erase(str(id))
				views[vname] = seen
			for e in m.get("events", []):
				_keep(events, e)
		"error":
			reason = str(m.get("reason", "the world refused"))
			status = "closed"
			peer.close()
			Q.event("world", {"status": status, "reason": reason})


func _keep(into: Array, item) -> void:
	into.append(item)
	if into.size() > MAX_HEARD:
		into.pop_front()


func _send(m: Dictionary) -> void:
	if latency > 0:
		_out.append([_frame + latency, m])
	else:
		_write(m)


func _write(m: Dictionary) -> void:
	peer.send_text(JSON.stringify(m))
	if str(m.get("type", "")) == "cmd":
		sent = int(m.get("seq", sent))


# a step guessed: shown at once, if the world will likely say yes (no wall, the last step over)
func _predict(seq: int, way) -> void:
	var step = DIRS.get(str(way))
	var from = _guess.back()[1] if not _guess.is_empty() else shown(you)
	if step == null or from == null or _frame - _guessed_at < step_ticks:
		return
	var to: Vector2i = from + step
	if walls.has(to) or to.x < 0 or to.y < 0 or (map_size.x > 0 and (to.x >= map_size.x or to.y >= map_size.y)):
		return
	_guess.append([seq, to])
	_guessed_at = _frame


# the world answered a command: a guess it took is the world's now; one it refused goes, and those after it
func _settle(seq: int, refused_: bool) -> void:
	for i in _guess.size():
		if int(_guess[i][0]) == seq:
			if refused_:
				_guess.resize(i)
			else:
				_guess.remove_at(i)
			return


# where an entity is drawn: the player's own at its last guessed step, the others where the world says
func shown(id) -> Variant:
	if str(id) == you and not _guess.is_empty():
		return _guess.back()[1]
	var e = entity(id)
	if e is Dictionary and e.get("at") is Dictionary:
		return Vector2i(int(e["at"].get("x", 0)), int(e["at"].get("y", 0)))
	return null


# qg:send: a command, with its arguments; its answer comes with a tick (refused, or what it changed)
func send(command: String, args: Dictionary) -> int:
	_seq += 1
	var m := {"type": "cmd", "seq": _seq, "name": command, "args": args}
	Q.event("send", {"command": command, "args": args, "seq": _seq})
	if status == "closed" or peer == null:
		_keep(refused, {"seq": _seq, "name": command, "reason": "Not connected to the world."})
		return _seq
	if predict.has(command) and status == "in":
		_predict(_seq, args.get(predict[command]))
	if _hello:
		_send(m)
	else:
		_pending.append(m)
	return _seq


func entity(id) -> Variant:
	for v in views.values():
		if v.has(id):
			return v[id]
	return null


func me() -> Dictionary:
	var e = entity(you)
	return e if e is Dictionary else {}


func close() -> void:
	if peer != null and status != "closed":
		peer.close()
	status = "closed"


# what the play protocol observes: the world as this player knows it
func observation() -> Dictionary:
	var seen := {}
	for v in views.values():
		for id in v:
			seen[id] = v[id]
	return {"status": status, "reason": reason, "world": world_name, "tick": tick, "you": you, "sent": sent,
		"guessed": _guess.size(),
		"me": me(), "views": views.duplicate(true), "entities": seen.duplicate(true)}
