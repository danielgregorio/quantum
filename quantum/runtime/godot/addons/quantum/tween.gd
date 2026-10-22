extends Node
# qg:tween: one property of a thing goes from what it is to a value, eased,
# over so many ticks. The scene's tweens are kept here, one node per scene
# ("Tweens", placed with it), as records it steps in the physics tick (the
# same on every peer, in every replay), before the things' own tick, so a
# thing sees where its tween put it. They stop while the scene is paused or
# the lockstep waits; a tween goes when its thing goes, and a new tween of
# the same property of the same thing replaces it.
#
#   x, y        the thing's position (it moves in the game: collisions see it)
#   rotation    its picture's turn, in degrees
#   scale       its picture's size (1: its own, as its scale= makes it)
#   scale-x     across only, and scale-y up and down only: a squash, a stretch
#   alpha       how opaque it is (0 to 1)
#   tint        the colour its picture is multiplied by (white: as drawn)
#
# When one is done (the last of its repeats), its qg:on-end runs: a handler
# of the script that started it (the scene's, or the prefabs' P), with `me`
# the thing it moved. A tween started there plays next: a sequence.
#
# Being records, they roll back (q_save / q_load): the rollback goes back to
# a tick with the tweens that were playing then, as far as they had got, and
# the looks (scale, rotation, alpha, tint) of what they had touched.

var tweens: Array = []   # {target, property, from, to, ticks, t, trans, ease, repeat, yoyo, caller, on_end}
# qg:travel: a thing goes cell by cell along a way found as it starts, a
# cell every `step` ticks, and its qg:on-end runs as it arrives. Stepped here
# with the tweens, and rolled back with them.
var travels: Array = []   # {target, cells (the middles, the start first), i, t, step, caller, on_end}


func _ready() -> void:
	process_physics_priority = -50   # before the things' own tick


func add(target: Node2D, property: String, to, seconds: float, trans: int, ease: int, repeat: int, yoyo: bool,
		from = null, caller: Object = null, on_end: String = "") -> void:
	_base(target)   # its own size, before any tween changes it
	for rec in tweens.duplicate():
		if rec["target"] == target and rec["property"] == property:
			tweens.erase(rec)
	if from == null:
		from = read(target, property)
	elif property != "tint":
		from = float(from)
	tweens.append({"target": target, "property": property, "from": from,
		"to": to if property == "tint" else float(to),
		"ticks": maxi(1, int(round(seconds * Q.TICK_RATE))), "t": 0, "trans": trans, "ease": ease,
		"repeat": repeat, "yoyo": yoyo, "caller": caller, "on_end": on_end})
	target.set_meta("q_tweened", true)


func travel(target: Node2D, cells: Array, step: int, caller: Object = null, on_end: String = "") -> void:
	for rec in travels.duplicate():
		if rec["target"] == target:
			travels.erase(rec)   # a new travel replaces the one it was on
	travels.append({"target": target, "cells": cells, "i": 1, "t": 0, "step": maxi(1, step), "caller": caller,
		"on_end": on_end})


# Where the travels under way end: no other travel ends there too.
func travel_ends() -> Array:
	return travels.map(func(rec): return rec["cells"][-1])


func _step_travels() -> void:
	for rec in travels.duplicate():
		if not travels.has(rec):
			continue
		var target = rec["target"]
		if not is_instance_valid(target) or target.is_queued_for_deletion():
			travels.erase(rec)
			continue
		if rec["i"] < rec["cells"].size():
			rec["t"] += 1
			target.position = (rec["cells"][rec["i"] - 1] as Vector2).lerp(rec["cells"][rec["i"]], float(rec["t"]) / rec["step"])
			if rec["t"] >= rec["step"]:
				rec["i"] += 1
				rec["t"] = 0
			if rec["i"] < rec["cells"].size():
				continue
		travels.erase(rec)
		var caller = rec["caller"]
		if rec["on_end"] != "" and is_instance_valid(caller) and caller.has_method(rec["on_end"]):
			caller.call(rec["on_end"], target, null)


func _physics_process(_delta: float) -> void:
	_step_travels()
	# a copy: a tween's qg:on-end may start another (it plays from the next tick)
	for rec in tweens.duplicate():
		if not tweens.has(rec):
			continue   # replaced by a handler of a tween stepped before it this tick
		if not is_instance_valid(rec["target"]) or rec["target"].is_queued_for_deletion():
			tweens.erase(rec)
			continue
		rec["t"] += 1
		write(rec["target"], rec["property"], Tween.interpolate_value(rec["from"], rec["to"] - rec["from"],
			float(rec["t"]), float(rec["ticks"]), rec["trans"], rec["ease"]))
		if rec["t"] < rec["ticks"]:
			continue
		if rec["repeat"] == 0:
			tweens.erase(rec)
			var caller = rec["caller"]
			if rec["on_end"] != "" and is_instance_valid(caller) and caller.has_method(rec["on_end"]):
				caller.call(rec["on_end"], rec["target"], null)
			continue
		if rec["repeat"] > 0:
			rec["repeat"] -= 1
		rec["t"] = 0
		if rec["yoyo"]:
			var f = rec["from"]
			rec["from"] = rec["to"]
			rec["to"] = f
		else:
			write(rec["target"], rec["property"], rec["from"])


static func _picture(node: Node2D) -> Node2D:
	var sprite = node.get_node_or_null("Sprite")
	return sprite if sprite is Node2D else node


# Its picture's own size (its scale=), kept as the first tween finds it: a scale is relative to it.
static func _base(node: Node2D) -> Vector2:
	if not node.has_meta("q_base_scale"):
		node.set_meta("q_base_scale", _picture(node).scale)
	var base: Vector2 = node.get_meta("q_base_scale")
	return Vector2(maxf(base.x, 0.0001), maxf(base.y, 0.0001))


static func read(node: Node2D, prop: String):
	match prop:
		"tint":
			var m := _picture(node).modulate
			return Color(m.r, m.g, m.b)
		"x":
			return node.position.x
		"y":
			return node.position.y
		"rotation":
			return _picture(node).rotation_degrees
		"scale", "scale-x":
			return _picture(node).scale.x / _base(node).x
		"scale-y":
			return _picture(node).scale.y / _base(node).y
		"alpha":
			return node.modulate.a
	return 0.0


static func write(node: Node2D, prop: String, v) -> void:
	match prop:
		"tint":
			var pic := _picture(node)
			pic.modulate = Color(v.r, v.g, v.b, pic.modulate.a)
		"x":
			node.position.x = v
		"y":
			node.position.y = v
		"rotation":
			_picture(node).rotation_degrees = v
		"scale":
			_picture(node).scale = _base(node) * v
		"scale-x":
			_picture(node).scale.x = _base(node).x * v
		"scale-y":
			_picture(node).scale.y = _base(node).y * v
		"alpha":
			node.modulate.a = v


# For the rollback: the tweens as far as they have got, and the looks of what
# they touched (a tween done, or not yet started, leaves its mark on them).
# Things by their path from the scene; the caller as "scene" or "P".
const LOOKS := ["rotation", "scale", "scale-x", "scale-y", "alpha", "tint"]


func q_save() -> Dictionary:
	var scene := get_parent()
	var recs := []
	for rec in tweens:
		if not is_instance_valid(rec["target"]):
			continue
		var r: Dictionary = rec.duplicate()
		r["target"] = scene.get_path_to(rec["target"])
		r["caller"] = "P" if rec["caller"] == P else "scene"
		recs.append(r)
	var looks := {}
	for n in _touched(scene):
		var l := {}
		for prop in LOOKS:
			l[prop] = read(n, prop)
		looks[scene.get_path_to(n)] = l
	var ways := []
	for rec in travels:
		if is_instance_valid(rec["target"]):
			var r: Dictionary = rec.duplicate()
			r["target"] = scene.get_path_to(rec["target"])
			r["caller"] = "P" if rec["caller"] == P else "scene"
			ways.append(r)
	return {"tweens": recs, "looks": looks, "travels": ways}


func q_load(d: Dictionary) -> void:
	var scene := get_parent()
	tweens.clear()
	for r in d["tweens"]:
		var target := scene.get_node_or_null(r["target"])
		if target == null:
			continue
		var rec: Dictionary = r.duplicate()
		rec["target"] = target
		rec["caller"] = P if r["caller"] == "P" else scene
		tweens.append(rec)
	for path in d["looks"]:
		var n := scene.get_node_or_null(path)
		if n is Node2D:
			for prop in LOOKS:
				write(n, prop, d["looks"][path][prop])
	travels.clear()
	for r in d.get("travels", []):
		var target := scene.get_node_or_null(r["target"])
		if target == null:
			continue
		var rec: Dictionary = r.duplicate()
		rec["target"] = target
		rec["caller"] = P if r["caller"] == "P" else scene
		travels.append(rec)


static func _touched(scene: Node) -> Array:
	var out := []
	for n in scene.get_children():
		if n is Node2D and n.has_meta("q_tweened"):
			out.append(n)
	return out
