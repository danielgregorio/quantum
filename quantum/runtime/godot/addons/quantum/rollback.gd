extends "res://addons/quantum/lockstep.gd"
# Rollback (qg:multiplayer rollback=N): the lockstep without the wait.
#
# The lockstep runs a tick only when every player's input for it is here.
# The rollback runs it at once, with the inputs it has and a guess for the
# others (each player keeps pressing what they last pressed), and keeps a
# snapshot of the state before every tick. When an input arrives for a tick
# already run and it is not what was guessed, the state goes back to that
# tick's snapshot and the ticks since are run again, inside one frame, with
# what is now known. Every peer ends at the same state as the lockstep would;
# it only never stops to wait (unless it is more than `window` ticks ahead
# of what is certain). The input delay (`delay`) still applies to the local
# player and may be small: one or two ticks.
#
# What it takes from the scene: every node that runs in the tick saves and
# loads its state (q_save / q_load), and nothing in it goes through Godot's
# physics, which cannot be run again inside a frame — the compiler allows
# rollback only for scenes made of such nodes (a fighter, timers, menus, the
# HUD, pictures). A scene change waits until the tick that asked for it is
# certain, then happens on every peer at that tick.

var window: int = 8
var confirmed: int = -1          # every tick up to this one has every player's real input
var rollbacks: int = 0           # how many times the state went back (a report, for tests)
var stop_at: int = -1            # the replay harness: advance no further than this tick
var _used: Dictionary = {}       # tick -> {player: entry} the inputs a tick was run with
var _snapshots: Dictionary = {}  # tick -> the state before that tick
var _rollback_from: int = -1
var _pending = null              # [tick, scene]: a qg:goto-scene waiting to be certain
var _sim_tick: int = 0
var _scene: Node = null
var _steppers: Array = []        # the scene's nodes that run in a tick, in Godot's order
var _savers: Array = []          # the scene's nodes with a state to save, in tree order


func setup(spec: Dictionary, game_: Node, host_: String, port_: int) -> void:
	window = int(spec.get("rollback", 8))
	super.setup(spec, game_, host_, port_)


func request_scene(name_: String) -> void:
	if _pending == null:
		_pending = [_sim_tick, name_]


func net_report() -> Dictionary:
	return {"rollbacks": rollbacks, "confirmed": confirmed, "tick": tick}


@rpc("any_peer", "call_remote", "reliable")
func _frame(p: int, t: int, mask: int, cx: float, cy: float) -> void:
	if not _frames.has(t):
		_frames[t] = {}
	var entry := [mask, cx, cy]
	_frames[t][p] = entry
	# a tick already run with a guess for this player that was wrong: back to it
	if t < tick and _used.has(t) and _used[t].get(p) != entry:
		if _rollback_from < 0 or t < _rollback_from:
			_rollback_from = t


func _physics_process(_delta: float) -> void:
	if not started or desynced:
		return
	var scene: Node = game.current_scene
	if scene == null:
		return
	if scene != _scene:
		_index(scene)
	# 1. this player's input, `delay` ticks ahead, to everyone
	var mask := 0
	var local: Dictionary = Q.sample_local()   # held, and tapped since the last tick
	for i in ACTIONS.size():
		if local.has(ACTIONS[i]):
			mask |= 1 << i
	var ahead := tick + delay
	if not _frames.has(ahead):
		_frames[ahead] = {}
	if not _frames[ahead].has(player):
		var raw: Vector2 = Q.raw_cursor
		_frames[ahead][player] = [mask, raw.x, raw.y]
		if not ended:
			_send_frame(player, ahead, mask, raw.x, raw.y)
	# 2. a guess was wrong: back to that tick, and run the ticks since again
	if _rollback_from >= 0 and _rollback_from < tick and _snapshots.has(_rollback_from):
		_resimulate(_rollback_from)
	_rollback_from = -1
	# 3. what is now certain
	while _known(confirmed + 1):
		confirmed += 1
		if check_every > 0 and confirmed > 0 and confirmed % check_every == 0 and _snapshots.has(confirmed + 1):
			var h := hash(var_to_str(_snapshots[confirmed + 1]))
			_report(confirmed, player, h)
			if not ended:
				_hash.rpc(player, confirmed, h)
	# 4. a scene change, once the tick that asked for it is certain
	if _pending != null:
		if int(_pending[0]) <= confirmed:
			var to: String = _pending[1]
			_pending = null
			_snapshots.clear()
			_used.clear()
			game.go_to_scene(to)
			_stall(true)
			return
		_stall(true)
		return
	# 5. not too far ahead of what is certain (nor past where a replay stops)
	if tick - confirmed > window or (stop_at >= 0 and tick >= stop_at):
		_stall(true)
		return
	# 6. this tick: Godot runs the scene's nodes after this one, with this input
	_snapshots[tick] = _save()
	_apply_input(tick)
	_sim_tick = tick
	_stall(false)
	tick += 1
	_prune()


func _stall(on: bool) -> void:
	if on == _stalled:
		return
	_stalled = on
	var scene: Node = game.current_scene
	if scene != null:
		scene.process_mode = Node.PROCESS_MODE_DISABLED if on else Node.PROCESS_MODE_INHERIT


func stalled() -> bool:
	return _stalled


func _known(t: int) -> bool:
	if not _frames.has(t):
		return false
	return _frames[t].size() >= players


# The input of a tick: what is known, and for the others what they pressed last.
func _apply_input(t: int) -> void:
	var input := {}
	var used := {}
	for p in range(1, players + 1):
		var entry = _frames.get(t, {}).get(p)
		if entry == null:
			entry = _guess(p, t)
		used[p] = entry
		Q.cursors[p] = Vector2(float(entry[1]), float(entry[2]))
		var m: int = int(entry[0])
		for i in ACTIONS.size():
			if m & (1 << i):
				input[ACTIONS[i] if p == 1 else "p%d_%s" % [p, ACTIONS[i]]] = 1.0
	_used[t] = used
	Q.set_input(input)


func _guess(p: int, t: int) -> Array:
	var k := t - 1
	while k >= 0 and k >= t - window - delay - 4:
		if _frames.has(k) and _frames[k].has(p):
			return _frames[k][p]
		k -= 1
	return [0, 0.0, 0.0]


func _resimulate(from: int) -> void:
	rollbacks += 1
	Q.resimulating = true
	_load(_snapshots[from])
	var dt := 1.0 / Engine.physics_ticks_per_second
	var until := tick
	for k in range(from, until):
		_sim_tick = k
		_apply_input(k)
		for n in _steppers:
			if is_instance_valid(n):
				n._physics_process(dt)
		_snapshots[k + 1] = _save()
		if _pending != null:
			# the scene changes after this tick now: the ticks after it never were
			tick = k + 1
			break
	for k in _snapshots.keys():
		if k > tick:
			_snapshots.erase(k)
	Q.resimulating = false


func _save() -> Dictionary:
	var nodes := []
	for n in _savers:
		nodes.append(n.q_save())
	return {"nodes": nodes, "G": G.quantum_state().duplicate(true), "q": Q.input_state(),
		"s": Q.sounds_played.size(), "c": Q.cursors.duplicate(), "pending": _pending}


func _load(d: Dictionary) -> void:
	for i in _savers.size():
		_savers[i].q_load(d["nodes"][i])
	for k in d["G"].keys():
		var v = d["G"][k]
		G.set(k, v.duplicate(true) if (v is Array or v is Dictionary) else v)
	Q.restore_input(d["q"])
	Q.sounds_played.resize(int(d["s"]))
	Q.cursors = d["c"].duplicate()
	_pending = d["pending"]


func _index(scene: Node) -> void:
	_scene = scene
	_steppers = []
	_savers = []
	var all := []
	_walk(scene, all)
	for n in all:
		if n.has_method("q_save"):
			_savers.append(n)
		if n.get_script() != null and n.has_method("_physics_process"):
			_steppers.append(n)
	# Godot's order: by process_physics_priority, then the tree's (a stable sort)
	var keyed := []
	for i in _steppers.size():
		keyed.append([_steppers[i].process_physics_priority, i, _steppers[i]])
	keyed.sort_custom(func(a, b): return a[0] < b[0] or (a[0] == b[0] and a[1] < b[1]))
	_steppers = keyed.map(func(e): return e[2])


func _walk(n: Node, out: Array) -> void:
	out.append(n)
	for c in n.get_children():
		_walk(c, out)


func _prune() -> void:
	var keep := mini(confirmed, tick - window - 2)
	for k in _snapshots.keys():
		if k < keep:
			_snapshots.erase(k)
	for k in _used.keys():
		if k < keep:
			_used.erase(k)
	for k in _frames.keys():
		if k < keep - window - delay - 4:
			_frames.erase(k)
