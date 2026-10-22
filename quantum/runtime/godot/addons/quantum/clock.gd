extends Node
# The scene's clock: one node per scene ("Clock", placed with it), stepped
# first in every physics tick, before the tweens and the things. It counts
# the ticks the scene has played (ticks()), runs what a qg:after put off
# when its count is done, and reads the scene's qg:when conditions. It stops
# while the scene is paused or the lockstep waits, and goes with the scene.
#
#   qg:after   a record: the ticks left, the method of the script that put
#              it off (the scene's, or the prefabs' P) and what its names
#              were then (me, other, a loop variable, a parameter); a thing
#              gone by then is passed as null. One with a name replaces one
#              of that name still waiting.
#   qg:when    a condition method of the scene and its handler: read at the
#              start of every tick, from the scene's first, after the delays
#              due then; the handler runs when it turns true (at the first
#              reading too, when true then), and again only after it has
#              been false.
#
# Being records and flags, they roll back (q_save / q_load).

var tick: int = 0
var delays: Array = []      # {left, caller, method, args, name}
var whens: Array = []       # [condition method, handler method], the scene's, in its order
var _was: Array = []        # each qg:when's last reading


func _ready() -> void:
	process_physics_priority = -60   # before the tweens (-50) and the things
	whens = get_parent().q_spec.get("when", [])
	_was.resize(whens.size())
	_was.fill(false)


func after(caller: Object, ticks: int, method: String, args: Array, name_: String = "") -> void:
	if name_ != "":
		for rec in delays.duplicate():
			if rec["name"] == name_:
				delays.erase(rec)
	delays.append({"left": maxi(1, ticks), "caller": caller, "method": method, "args": args, "name": name_})


func _physics_process(_delta: float) -> void:
	tick += 1
	# a copy: what a delay runs may put off more (it counts from the next tick)
	for rec in delays.duplicate():
		if not delays.has(rec):
			continue   # replaced by one a delay run before it this tick put off
		rec["left"] -= 1
		if rec["left"] > 0:
			continue
		delays.erase(rec)
		var caller = rec["caller"]
		if is_instance_valid(caller) and caller.has_method(rec["method"]):
			caller.callv(rec["method"], rec["args"].map(_live))
	var scene := get_parent()
	for i in whens.size():
		var now := bool(scene.call(whens[i][0]))
		var turned: bool = now and not _was[i]
		_was[i] = now
		if turned:
			scene.call(whens[i][1])


# For the rollback: the count, the delays as far as they have got (things by
# their path from the scene, the caller as "scene" or "P"), and the readings.
func q_save() -> Dictionary:
	var scene := get_parent()
	var recs := []
	for rec in delays:
		var r: Dictionary = rec.duplicate()
		r["caller"] = "P" if rec["caller"] == P else "scene"
		r["args"] = rec["args"].map(func(a): return _save_arg(scene, a))
		recs.append(r)
	return {"tick": tick, "delays": recs, "was": _was.duplicate()}


func q_load(d: Dictionary) -> void:
	var scene := get_parent()
	tick = d["tick"]
	delays.clear()
	for r in d["delays"]:
		var rec: Dictionary = r.duplicate()
		rec["caller"] = P if r["caller"] == "P" else scene
		rec["args"] = r["args"].map(func(a): return _load_arg(scene, a))
		delays.append(rec)
	_was = d["was"].duplicate()


# A thing that has gone (or is going) is null; `is` on a freed one is an error,
# so the type is asked first.
static func _live(a):
	if typeof(a) == TYPE_OBJECT:
		return a if Q.alive(a) else null
	return a


static func _save_arg(scene: Node, a):
	if typeof(a) == TYPE_OBJECT:
		return {"q_node": scene.get_path_to(a)} if Q.alive(a) and a is Node else null
	return a.duplicate(true) if (a is Array or a is Dictionary) else a


static func _load_arg(scene: Node, a):
	if a is Dictionary and a.has("q_node"):
		return scene.get_node_or_null(a["q_node"])
	return a.duplicate(true) if (a is Array or a is Dictionary) else a
