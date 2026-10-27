extends RefCounted
# qg:connect: the game's door into a world, `quantum gameserver run`'s (PLAN_GAME_SERVER.md). It speaks the
# server's protocol (quantum/runtime/gameserver/server.py) on a WebSocket, polled once a tick by Q: what the player
# sees of each view (views[name][id], the entity's fields as the server sent them: the public ones, and the
# player's own entity's private ones), the player's own entity (you), and the events and refusals of the ticks the
# scene has not heard yet (its qg:on-event and qg:on-refused take them).
#
# Nothing of the world's is decided here: a qg:send asks, the server answers with the tick. The game draws what it
# is told (mirror.gd) and says what it was refused.

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
	peer.poll()
	var state := peer.get_ready_state()
	if state == WebSocketPeer.STATE_OPEN:
		if not _hello:
			_hello = true
			_send({"type": "hello", "name": player})
			for m in _pending:
				_send(m)
			_pending.clear()
		while peer.get_available_packet_count() > 0:
			var data = JSON.parse_string(peer.get_packet().get_string_from_utf8())
			if data is Dictionary:
				_apply(data)
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
			for r in m.get("refused", []):
				_keep(refused, r)
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
	peer.send_text(JSON.stringify(m))


# qg:send: a command, with its arguments; its answer comes with a tick (refused, or what it changed)
func send(command: String, args: Dictionary) -> int:
	_seq += 1
	var m := {"type": "cmd", "seq": _seq, "name": command, "args": args}
	Q.event("send", {"command": command, "args": args, "seq": _seq})
	if status == "closed" or peer == null:
		_keep(refused, {"seq": _seq, "name": command, "reason": "Not connected to the world."})
	elif _hello:
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
	return {"status": status, "reason": reason, "world": world_name, "tick": tick, "you": you, "sent": _seq,
		"me": me(), "views": views.duplicate(true), "entities": seen.duplicate(true)}
