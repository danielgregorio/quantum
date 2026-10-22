extends Node
# Q: the helpers the compiled scripts call. An autoload (project.godot),
# so every script sees `Q`.
#
# Where GDScript's operators differ from Quantum's expression semantics
# (quantum/core/expressions.py), the compiler emits one of these instead.

var _sounds: Dictionary = {}   # name -> AudioStreamPlayer
# qg:cursor: where each player points, {player: Vector2}, in scene pixels.
# raw_cursor is the local pointer before the lockstep (the mouse, or the
# replay tape's "cursor" events); under lockstep it travels with the input
# and lands in cursors[p] on every peer; alone it is cursors[player] at once.
var cursors: Dictionary = {}
var raw_cursor: Vector2 = Vector2.ZERO
var tape_cursor = null   # the replay tape's pointer (Vector2), instead of the mouse
var tape_mouse = null    # where the mouse was, as a watched session is played again (godot_watch.gd)
var mouse_seen = null    # where the cursors last saw the mouse, which godot_watch.gd records
var sounds_played: Array = []  # names, in order — the replay harness reads it

# --- the input of the tick ---
# Every action is read once per physics tick, here, before any node of the
# game runs (Q is an autoload, first in the tree, and runs at the lowest
# priority); the runtime asks Q, never Input. So a tick's input is a value:
# the lockstep and the rollback set it themselves (external_input), and the
# rollback can replay old ticks with their input in one frame.
var _now: Dictionary = {}    # action -> strength (0..1), only the pressed ones
var _prev: Dictionary = {}
var _for: Dictionary = {}    # action -> the ticks it has been held, up to this one
var _for_prev: Dictionary = {}
var external_input: bool = false


# `/` in Quantum is a float division, whatever the operands.
static func div(a, b):
	return float(a) / float(b)


# `//` floors, like Python.
static func floordiv(a, b):
	return floori(float(a) / float(b))


# `%` follows the divisor's sign, like Python.
static func mod(a, b):
	return fposmod(float(a), float(b))


# `str()` as Quantum writes a number: 7, not 7.0, for a whole one.
static func to_str(v) -> String:
	if v is float and v == floorf(v) and absf(v) < 1e15:
		return str(int(v))
	return str(v)


# `len()` of a string, an array or a dictionary.
static func len(v) -> int:
	if v is String:
		return (v as String).length()
	if v is Array or v is Dictionary:
		return v.size()
	return 0


# `sort(list)`, `sort(list, true)`: a sorted copy, as the Core's sort (numbers
# before texts when they are mixed, as Python cannot compare them at all).
static func sort(v, reverse: bool = false) -> Array:
	var out: Array = (v as Array).duplicate() if v is Array else []
	out.sort_custom(func(a, b): return _before(b, a) if reverse else _before(a, b))
	return out


static func _before(a, b) -> bool:
	var na := a is int or a is float
	var nb := b is int or b is float
	if na != nb:
		return na
	return a < b


# sin(), cos() of an angle in degrees, and atan2(y, x) the angle of a direction
# in degrees: 0 to the right, 90 down (the screen's y grows downwards), as a
# picture's rotation.
static func atan2_deg(y: float, x: float) -> float:
	return rad_to_deg(atan2(y, x))


# `a[start:end]` of a string or an array, like Python (null: from the start / to the end).
static func slice(v, start, end):
	var n: int = v.length() if v is String else v.size()
	var s: int = 0 if start == null else int(start)
	var e: int = n if end == null else int(end)
	if s < 0:
		s = maxi(0, n + s)
	if e < 0:
		e = maxi(0, n + e)
	s = mini(s, n)
	e = mini(e, n)
	if e <= s:
		return "" if v is String else []
	if v is String:
		return (v as String).substr(s, e - s)
	return (v as Array).slice(s, e)


# gd: attributes: properties of the Godot node a tag became, as game.json
# carries them ({name: {type, value}}), set as they are — nothing is
# interpreted here; the compiler checked them against Godot's reference.
static func apply_gd(node: Node, gd) -> void:
	if gd == null:
		return
	for name_ in gd.keys():
		var entry: Dictionary = gd[name_]
		var v = entry["value"]
		match str(entry["type"]):
			"Vector2": v = Vector2(v[0], v[1])
			"Vector2i": v = Vector2i(int(v[0]), int(v[1]))
			"Color": v = Color(v)
			"int": v = int(v)
			"float": v = float(v)
		node.set(name_, v)


# --- events, for the play protocol (PLAN_PLAY_PROTOCOL.md) ---
# What happened, as a player would notice it: a touch, a hit, a thing made or
# gone, a sound, a scene, a line said. Recorded only while a play session
# traces (godot_play.gd sets `tracing`); otherwise each call is one check.
var tracing: bool = false
var events: Array = []
var events_dropped: int = 0
var event_tick: int = 0


static func event(kind: String, data: Dictionary = {}) -> void:
	var q = (Engine.get_main_loop() as SceneTree).root.get_node_or_null("Q")
	if q == null or not q.tracing or q.resimulating:
		return
	if q.events.size() >= 500:
		q.events_dropped += 1
		return
	var e := data.duplicate()
	e["kind"] = kind
	e["tick"] = q.event_tick
	q.events.append(e)


# How an event names a node: a character or a named thing by its name, a thing by its tag.
static func who(node) -> String:
	node = _thing(node)
	if node == null:
		return ""
	if node.is_in_group("q_named") or node.has_meta("q_named"):
		return String(node.name)
	if "tag" in node:
		return str(node.tag)
	return String(node.name)


# Removes a thing from the scene at the end of the tick.
static func destroy(node) -> void:
	node = _thing(node)
	if node == null:
		return
	if node is Node2D:
		event("destroy", {"what": who(node), "x": snappedf(node.position.x, 0.1), "y": snappedf(node.position.y, 0.1)})
	if node.has_method("quantum_destroy"):
		node.quantum_destroy()
	else:
		node.queue_free()


# Throws a character up `height` pixels (qg:bounce).
static func bounce(node, height: float) -> void:
	node = _thing(node)
	if node != null and node.has_method("bounce"):
		node.bounce(height)


# Puts a character back where it started the scene (qg:respawn).
static func respawn(node) -> void:
	node = _thing(node)
	if node != null and node.has_method("respawn"):
		node.respawn()


# qg:deflect on a flying thing.
static func deflect_axis(node, axis: String) -> void:
	node = _thing(node)
	if node != null and node.has_method("deflect_axis"):
		node.deflect_axis(axis)


static func deflect_to(node, dx: float, dy: float) -> void:
	node = _thing(node)
	if node != null and node.has_method("deflect_to"):
		node.deflect_to(dx, dy)


# random(a, b) in an expression: a float in [a, b] from the scene's seeded
# source, so the same seed gives the same game. `ctx` is the scene script
# (self in its handlers) or P (a prefab handler): then the current scene's.
static func random(ctx, a: float, b: float) -> float:
	var scene = ctx
	if ctx == null or not ("rng" in ctx):
		var scenes: Array = Engine.get_main_loop().get_nodes_in_group("q_scene")
		scene = scenes[0] if scenes.size() > 0 else null
	if scene == null:
		return a
	return scene.rng.randf_range(a, b)


# qg:put: a thing or a character moved to a point.
static func put(node, x: float, y: float) -> void:
	node = _thing(node)
	if node != null and node is Node2D:
		(node as Node2D).position = Vector2(x, y)


# Sets the speed of a character made of parts (qg:velocity); null keeps an axis.
static func velocity(node, x, y) -> void:
	node = _thing(node)
	if node != null and node.has_method("set_velocity_from_rules"):
		node.set_velocity_from_rules(x, y)


# qg:play-animation: an animation of a thing or a character, from its first frame.
static func play_animation(node, name_: String) -> void:
	node = _thing(node)
	var animator = node.get_node_or_null("Animator") if node != null else null
	if animator != null:
		animator.force(name_)


# Changes a character to one of its states (qg:become).
static func become(node, state: String) -> void:
	node = _thing(node)
	if node != null and node.has_method("become"):
		node.become(state)


# qg:emit: a qg:particles effect, once, where a thing is (offset dx, dy).
# Only seen: the game's state does not depend on it.
var particles_spec: Dictionary = {}   # the game's qg:particles, by name (scene_builder sets it)


static func emit(node, name_: String, dx: float = 0.0, dy: float = 0.0) -> void:
	node = _thing(node)
	var q := _q_node()
	if node == null or not (node is Node2D) or q == null or not q.particles_spec.has(name_):
		return
	var scene := (node as Node).get_parent()
	if scene == null:
		return
	var fx: CPUParticles2D = load("res://addons/quantum/particles.gd").make(q.particles_spec[name_])
	fx.position = (node as Node2D).position + Vector2(dx, dy)
	if fx.one_shot:
		fx.finished.connect(fx.queue_free)
	else:
		# a continuing effect, emitted once: it plays for a while and goes
		scene.get_tree().create_timer(fx.lifetime * 2.0).timeout.connect(fx.queue_free)
		scene.get_tree().create_timer(fx.lifetime).timeout.connect(func(): fx.emitting = false)
	scene.call_deferred("add_child", fx)
	event("emit", {"particles": name_})


# qg:emit text=: a text that floats up from a thing and fades (a damage number,
# +10). Only seen: the rollback's ticks run again show none.
static func emit_text(node, text: String, color: String, size: int, dx: float = 0.0, dy: float = 0.0) -> void:
	node = _thing(node)
	var q := _q_node()
	if node == null or not (node is Node2D) or (q != null and q.resimulating):
		return
	var scene := (node as Node).get_parent()
	if scene == null:
		return
	var label := Label.new()
	label.text = translate(text)   # a word in the player's language, as a HUD's is
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", Color(color))
	label.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.8))
	label.add_theme_constant_override("outline_size", 2)
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.size = Vector2(80, size + 6)
	label.position = (node as Node2D).position + Vector2(dx, dy) - label.size / 2.0
	label.z_index = 30
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	scene.call_deferred("add_child", label)
	var rise := scene.create_tween()
	rise.tween_property(label, "position:y", label.position.y - 14.0, 0.8)
	rise.parallel().tween_property(label, "modulate:a", 0.0, 0.8).set_delay(0.3)
	rise.tween_callback(label.queue_free)
	event("emit", {"text": text})


# qg:beam: a line between two things for a while, following them. Only seen.
static func beam(ctx, a, b, seconds: float, color: String, width: float) -> void:
	a = _thing(a)
	b = _thing(b)
	var q := _q_node()
	var scene := _current_scene(ctx)
	if scene == null or not (a is Node2D) or not (b is Node2D) or (q != null and q.resimulating):
		return
	var line: Line2D = load("res://addons/quantum/beam.gd").new()
	line.setup(a, b, int(round(seconds * TICK_RATE)), Color(color), width)
	scene.call_deferred("add_child", line)
	event("beam", {"from": who(a), "to": who(b)})


# hovered(): the thing under a player's qg:cursor, or null. The cursor's
# point travels with the input, so it is the same on every machine.
static func hovered(ctx, player: int):
	var scene := _current_scene(ctx)
	if scene == null or not "q_cursors" in scene:
		return null
	for cursor in scene.q_cursors:
		if is_instance_valid(cursor) and cursor.player == player:
			var at: Dictionary = cursor.where()
			return thing_at(scene, "", at["x"], at["y"])
	return null


# qg:rumble: the player's joypad shakes, and a phone in the hand. Felt only:
# nothing in the game depends on it. Over the network only the machine of that
# player's seat feels it, on its own pad; on one machine, player N's is the
# Nth pad connected.
static func rumble(player: int, strength: float, seconds: float) -> void:
	var q = (Engine.get_main_loop() as SceneTree).root.get_node_or_null("Q")
	event("rumble", {"player": player, "strength": strength, "seconds": seconds})
	if q == null or q.resimulating:
		return
	var pad := player - 1
	if q.external_input:
		if net_player() != player:
			return
		pad = 0
	var pads := Input.get_connected_joypads()
	var k := clampf(strength, 0.0, 1.0)
	if pad >= 0 and pad < pads.size():
		Input.start_joy_vibration(pads[pad], k, k, seconds)
	if OS.has_feature("mobile") and pad == 0:
		Input.vibrate_handheld(int(seconds * 1000.0), k)


# qg:camera-to: the scene's camera goes to a thing or a point, stays, and comes
# back to what it follows (camera.gd); the scene waits meanwhile, when asked.
static func camera_to(ctx, to, zoom: float, seconds: float, hold: float, pause_: bool) -> void:
	var scene := _current_scene(ctx)
	var cams: Array = scene.q_cameras() if scene != null and scene.has_method("q_cameras") else []
	if cams.is_empty() or not cams[0].has_method("show_point"):
		return
	var at: Vector2
	if to is Vector2:
		at = to
	else:
		to = _thing(to)
		if to == null or not (to is Node2D):
			return
		at = (to as Node2D).position
	for cam in cams:   # every player's view shows it (the first pauses the scene, and resumes it)
		cam.show_point(scene, at, zoom, int(round(seconds * TICK_RATE)), int(round(hold * TICK_RATE)), pause_)
	event("camera", {"x": snappedf(at.x, 0.1), "y": snappedf(at.y, 0.1)})


# qg:attach: `thing` is carried by `carrier`, dx,dy from it (carried.gd). While
# carried it touches nothing and nothing touches it, and it stands in no cell.
static func attach(thing, carrier, dx: float, dy: float) -> void:
	thing = _thing(thing)
	carrier = _thing(carrier)
	if not alive(thing) or not alive(carrier) or thing == carrier or not (thing is Node2D) or not (carrier is Node2D):
		return
	if thing.has_meta("q_carrier"):
		detach(thing)
	var link = carrier.get_node_or_null("Carried")
	if link == null:
		link = load("res://addons/quantum/carried.gd").new()
		carrier.add_child(link)
	link.carried.append([thing, Vector2(dx, dy)])
	thing.set_meta("q_carrier", carrier)
	_quiet(thing, true)
	(thing as Node2D).position = (carrier as Node2D).position + Vector2(dx, dy)
	event("attach", {"what": who(thing), "to": who(carrier)})


# qg:detach: a carried thing is put down where it is, and touches again.
static func detach(thing) -> void:
	thing = _thing(thing)
	if thing == null or not thing.has_meta("q_carrier"):
		return
	var carrier = thing.get_meta("q_carrier")
	if is_instance_valid(carrier):
		var link = carrier.get_node_or_null("Carried")
		if link != null:
			link.carried = link.carried.filter(func(e): return e[0] != thing)
	thing.remove_meta("q_carrier")
	_quiet(thing, false)
	event("detach", {"what": who(thing)})


static func detach_all(carrier, tag: String) -> void:
	carrier = _thing(carrier)
	var link = carrier.get_node_or_null("Carried") if carrier != null else null
	if link == null:
		return
	for entry in link.carried.duplicate():
		if is_instance_valid(entry[0]) and entry[0].has_method("quantum_tag") and entry[0].quantum_tag() == tag:
			detach(entry[0])


# carrying(me, 'key'): the first thing of that tag it carries, or null.
static func carrying(carrier, tag: String):
	carrier = _thing(carrier)
	var link = carrier.get_node_or_null("Carried") if carrier != null and carrier is Node else null
	if link == null:
		return null
	for entry in link.carried:
		if alive(entry[0]) and entry[0].has_method("quantum_tag") and entry[0].quantum_tag() == tag:
			return entry[0]
	return null


# A carried thing's areas and body touch nothing (and back): deferred, as a touch may be carrying it.
static func _quiet(thing: Node, on: bool) -> void:
	var areas := []
	if thing is Area2D:
		areas.append(thing)
	var hitbox = thing.get_node_or_null("Hitbox")
	if hitbox is Area2D:
		areas.append(hitbox)
	for area in areas:
		area.set_deferred("monitoring", not on and area.get_meta("q_monitoring", area.monitoring))
		area.set_deferred("monitorable", not on and area.get_meta("q_monitorable", area.monitorable))
		if on:
			area.set_meta("q_monitoring", area.monitoring)
			area.set_meta("q_monitorable", area.monitorable)
	if thing is CollisionObject2D and not (thing is Area2D):
		if on:
			thing.set_meta("q_layers", [thing.collision_layer, thing.collision_mask])
			thing.set_deferred("collision_layer", 0)
			thing.set_deferred("collision_mask", 0)
		elif thing.has_meta("q_layers"):
			var layers: Array = thing.get_meta("q_layers")
			thing.set_deferred("collision_layer", layers[0])
			thing.set_deferred("collision_mask", layers[1])


# qg:spawn heading=: the way a flying thing just placed goes (and faces).
static func headed(node, x: float, y: float):
	if node != null and is_instance_valid(node) and node.has_method("deflect_to"):
		node.deflect_to(x, y)
	return node


# The side of `other` a toucher hit, judged from where the two are: left when it
# is to the right of the toucher (hit from its left), right, top when the toucher
# is above it (landing on it), bottom. Their hitboxes weigh the two axes.
static func side_of(me: Node2D, other: Node2D) -> String:
	var a: Vector2 = me.get("hitbox_size") if me.get("hitbox_size") != null else Vector2(16, 16)
	var b: Vector2 = other.get("hitbox_size") if other.get("hitbox_size") != null else Vector2(16, 16)
	var d := other.global_position - me.global_position
	var nx := d.x / maxf(1.0, (a.x + b.x) / 2.0)
	var ny := d.y / maxf(1.0, (a.y + b.y) / 2.0)
	if absf(nx) >= absf(ny):
		return "left" if nx > 0.0 else "right"
	return "top" if ny > 0.0 else "bottom"


# qg:tween: a property of a thing, eased to a value over so many seconds of
# ticks (tween.gd). A new tween of the same property replaces the old one.
const TRANS := {"linear": Tween.TRANS_LINEAR, "sine": Tween.TRANS_SINE, "quad": Tween.TRANS_QUAD,
		"cubic": Tween.TRANS_CUBIC, "back": Tween.TRANS_BACK, "bounce": Tween.TRANS_BOUNCE,
		"elastic": Tween.TRANS_ELASTIC}
const EASE := {"in": Tween.EASE_IN, "out": Tween.EASE_OUT, "in-out": Tween.EASE_IN_OUT}


static func tween(node, property: String, to, seconds: float, trans: String, ease: String,
		repeat: int = 0, yoyo: bool = false, from = null, caller: Object = null, on_end: String = "") -> void:
	node = _thing(node)
	if node == null or not (node is Node2D):
		return
	var scene := _current_scene(node)
	var runner = scene.get_node_or_null("Tweens") if scene != null else null
	if runner == null:
		return
	runner.add(node, property, to, seconds, TRANS[trans], EASE[ease], repeat, yoyo, from, caller, on_end)
	event("tween", {"property": property, "to": to.to_html(false) if to is Color else to})


# qg:travel: a thing goes to `to` (a cursor's cell, or beside a thing) by the
# cheapest way over the scene's tilemap (qg:tile cost=), round the things and
# characters on it and the ends of the other travels, as far as `budget` pays
# for (-1: all the way), a cell every `step` ticks; then its qg:on-end runs,
# `me` the traveller. With no way, it stays and its qg:on-end runs at once.
static func travel(node, to, budget, step: int, caller: Object = null, on_end: String = "") -> void:
	node = _thing(node)
	if not (node is Node2D):
		return
	var scene := _current_scene(node)
	var map = scene.get_node_or_null("Tilemap") if scene != null else null
	var runner = scene.get_node_or_null("Tweens") if scene != null else null
	if map == null or runner == null:
		return
	var from: Vector2i = map.cell_of(node.position)
	var goal = _place_of(to)
	var cells := [node.position]
	if goal != null:
		var dest: Vector2i = map.cell_of(goal)
		var avoid := _occupied(scene, map, node)
		for c in runner.travel_ends():
			avoid[map.cell_of(c)] = true
		var beside: bool = avoid.has(dest)   # a thing there: up to it
		var way: Array = map.path(from, dest, 4096, avoid)
		if beside and not way.is_empty():
			way.pop_back()
		var spent := 0
		for i in range(1, way.size()):
			spent += map.cost_at(way[i])
			if budget != null and float(budget) >= 0 and spent > float(budget):
				break
			cells.append(map.centre_of(way[i]))
	event("travel", {"who": who(node), "cells": cells.size() - 1})
	runner.travel(node, cells, step, caller, on_end)


# cost(a, b): what the cheapest way from where a stands to where b is costs
# (qg:tile cost=, round the things on the way); INF when there is none.
static func cost(ctx, a, b) -> float:
	var scene := _current_scene(ctx)
	var map = scene.get_node_or_null("Tilemap") if scene != null else null
	var from = _place_of(a)
	var to = _place_of(b)
	if map == null or from == null or to == null:
		return INF
	var mover = _thing(a)
	var avoid := _occupied(scene, map, mover if mover is Node2D else null)
	avoid.erase(map.cell_of(to))
	var c: int = map.path_cost(map.cell_of(from), map.cell_of(to), avoid)
	return INF if c < 0 else float(c)


# Where a thing, a character or a cursor is: a point of the scene, or null.
static func _place_of(v):
	if v is Dictionary:
		return Vector2(float(v.get("x", 0.0)), float(v.get("y", 0.0))) if v.has("x") else null
	v = _thing(v)
	return (v as Node2D).position if v is Node2D and not v.is_queued_for_deletion() else null


# The cells the things and characters of a scene stand in, but one's.
static func _occupied(scene: Node, map, but) -> Dictionary:
	var out := {}
	for n in scene.get_children():
		if n == but or not (n is Node2D) or n.is_queued_for_deletion() or n.has_meta("q_carrier"):
			continue
		if n.is_in_group("q_thing") or n is CharacterBody2D:
			out[map.cell_of(n.position)] = true
	return out


# qg:after: a method of the caller (the scene script, or P) run so many ticks
# from now, with the values its names have now (clock.gd).
static func after(caller: Object, ticks, method: String, args: Array, name_: String = "") -> void:
	var clock = _clock(caller)
	if clock != null:
		clock.after(caller, int(round(float(ticks))), method, args, name_)
		event("after", {"ticks": int(round(float(ticks))), "name": name_})


# ticks(): how many ticks the scene has played (not while paused).
static func ticks(ctx) -> int:
	var clock = _clock(ctx)
	return clock.tick if clock != null else 0


static func _clock(ctx) -> Node:
	var scene := _current_scene(ctx)
	return scene.get_node_or_null("Clock") if scene != null else null


# Places a prefab where `at` is, offset (qg:spawn).
static func spawn(ctx: Node, prefab: String, at, dx: float, dy: float) -> Node:
	var scene := _current_scene(ctx)
	if scene == null:
		return null
	at = _thing(at)
	if at == null or not (at is Node2D):
		return null
	var builder = load("res://addons/quantum/scene_builder.gd")
	return builder.instance(scene.q_game, scene, prefab, (at as Node2D).position + Vector2(dx, dy), true)


# qg:spawn at="path": at the start of the scene's path, which an ai="path" thing then follows.
static func spawn_on_path(ctx: Node, prefab: String, path_name: String) -> Node:
	var scene := _current_scene(ctx)
	if scene == null:
		return null
	var paths: Dictionary = scene.q_paths if "q_paths" in scene else {}
	if not paths.has(path_name):
		return null
	var points: Array = paths[path_name]
	var builder = load("res://addons/quantum/scene_builder.gd")
	var made = builder.instance(scene.q_game, scene, prefab, Vector2(points[0][0], points[0][1]), true)
	if made != null and "path_points" in made:
		made.path_points = points
	return made


# --- what the players carry (qg:item): G.q_items, G.q_gone ---

# held(item) in an expression: how many the players hold.
static func items_held(item: String) -> int:
	return int(G.q_items.get(item, 0)) if "q_items" in G else 0


# qg:give: up to the item's max= (0: no limit).
static func give_item(item: String, amount: int = 1) -> void:
	if not ("q_items" in G) or not G.Q_ITEMS.has(item):
		return
	var most := int(G.Q_ITEMS[item]["max"])
	var now := items_held(item) + amount
	G.q_items[item] = mini(now, most) if most > 0 else now
	event("item", {"item": item, "held": int(G.q_items[item])})


# qg:take: not below 0.
static func take_item(item: String, amount: int = 1) -> void:
	if not ("q_items" in G) or not G.Q_ITEMS.has(item):
		return
	G.q_items[item] = maxi(0, items_held(item) - amount)
	event("item", {"item": item, "held": int(G.q_items[item])})


# qg:reset-items: a new game. Each item back to its start=, and the gone things come back.
static func reset_items() -> void:
	if not ("q_items" in G):
		return
	for item in G.Q_ITEMS:
		G.q_items[item] = int(G.Q_ITEMS[item]["start"])
	G.q_gone.clear()
	event("item", {"item": "", "held": 0})


# A named thing picked up or opened stays gone: the scene leaves it out when it is built again.
static func gone(scene_name: String, name_: String) -> bool:
	return "q_gone" in G and G.q_gone.has(scene_name + "/" + name_)


static func _gone(node: Node) -> void:
	if node.has_meta("q_named") and node.get_parent() != null:
		G.q_gone.append(String(node.get_parent().name) + "/" + String(node.name))


# What a character's touch does before its own handlers: it picks up a thing
# that gives= an item, and opens one that opens-with= an item it holds (or
# runs the thing's on-locked).
static func touched(body: Node, other) -> void:
	other = _thing(other)
	if other == null or other.is_queued_for_deletion() or not ("q_items" in G):
		return
	if "gives" in other and other.gives != "":
		var spec: Dictionary = G.Q_ITEMS.get(other.gives, {})
		if int(spec.get("max", 0)) > 0 and items_held(other.gives) >= int(spec["max"]):
			return   # they hold the most: it stays where it is
		give_item(other.gives, other.amount)
		event("pickup", {"who": who(body), "item": other.gives, "held": items_held(other.gives)})
		if spec.get("sound") != null and _q_node() != null:
			_q_node().play(str(spec["sound"]))
		if spec.get("particles") != null:
			emit(other, str(spec["particles"]))
		_gone(other)
		destroy(other)
	elif "opens_with" in other and other.opens_with != "":
		if items_held(other.opens_with) > 0:
			if not other.keeps:
				take_item(other.opens_with)
			event("open", {"who": who(body), "what": who(other), "item": other.opens_with})
			_gone(other)
			destroy(other)
		elif other.on_locked != "" and P.has_method(other.on_locked):
			event("locked", {"who": who(body), "what": who(other), "item": other.opens_with})
			P.call(other.on_locked, other, body)


# count(tag): how many things of the tag are in the scene (zones are not things).
static func count(ctx: Node, tag: String) -> int:
	var scene := _current_scene(ctx)   # a prefab's handler (in P), or a function of the game there, asks too
	var n := 0
	if scene == null or not scene.is_inside_tree():   # a HUD read as the scene is built: nothing is in it yet
		return 0
	for t in scene.get_tree().get_nodes_in_group("q_thing"):
		if t.get_parent() == scene and t.quantum_tag() == tag and alive(t):
			n += 1
	return n


# qg:on-separate: when `area` stops overlapping something of a tag a handler
# names, that handler runs (the caller is the scene for a character, P for a
# prefab) with `me` the owner and `other` what it touched. Not when either is
# being destroyed (it left nothing), nor while the scene is paused (a paused
# body leaves the physics; nothing was stepped off).
static func watch_separate(area: Area2D, owner: Node, handlers: Array, caller: Object) -> void:
	area.area_exited.connect(func(other_area: Area2D) -> void:
		if not other_area.has_method("quantum_tag") or not alive(owner) or paused(owner):
			return
		var other = _thing(other_area)
		if other == owner or not alive(other):
			return
		for h in handlers:
			if h["with"] == other_area.quantum_tag() and caller.has_method(h["handler"]):
				event("separate", {"who": who(owner), "with": who(other)})
				caller.call(h["handler"], owner, other))


# me.on_floor, me.on_wall, me.on_ceiling in an expression: what the body touched as it last
# moved. A body that keeps its own (a fighter, an enemy of parts) answers for itself.
static func touching(v, what: String) -> bool:
	v = _thing(v)
	if v == null:
		return false
	if ("on_" + what) in v:
		return v.get("on_" + what) == true
	if v is CharacterBody2D:
		match what:
			"floor":
				return (v as CharacterBody2D).is_on_floor()
			"wall":
				return (v as CharacterBody2D).is_on_wall()
			"ceiling":
				return (v as CharacterBody2D).is_on_ceiling()
	return false


# A thing that is still in the game: not destroyed, and not dying (a thing whose
# health reached 0 is gone for count() and qg:for-each while its qg:on-death runs).
static func alive(n) -> bool:
	return n != null and is_instance_valid(n) and not n.is_queued_for_deletion() and n.get("_dead") != true


# qg:for-each tag=: the things of a tag in the scene, in its order, as the loop starts.
static func things(node, tag: String) -> Array:
	var scene := _current_scene(node)
	var out := []
	if scene == null:
		return out
	for t in scene.get_children():
		if t.is_in_group("q_thing") and t.quantum_tag() == tag and alive(t):
			out.append(t)
	return out


# `a.x` and `a.y` in an expression: where a thing or a character is, or a cursor's point.
static func pos_x(v):
	if v is Dictionary:
		return v.get("x")
	v = _thing(v)
	return (v as Node2D).position.x if v is Node2D else null


static func pos_y(v):
	if v is Dictionary:
		return v.get("y")
	v = _thing(v)
	return (v as Node2D).position.y if v is Node2D else null


# `a.col` and `a.row`: the cell of the scene's tilemap a thing or a character stands in (a grid walker's, the
# one it steps to), or a cursor's.
static func cell_col(v):
	if v is Dictionary:
		return v.get("col")
	var c = _cell_of(_thing(v))
	return c.x if c != null else null


static func cell_row(v):
	if v is Dictionary:
		return v.get("row")
	var c = _cell_of(_thing(v))
	return c.y if c != null else null


static func _cell_of(n):
	if not (n is Node2D):
		return null
	if n.has_method("cell"):
		return n.cell()
	var map = n.get_parent().get_node_or_null("Tilemap") if n.get_parent() != null else null
	if map != null and map.has_method("cell_of") and map.shape != "square":
		return map.cell_of(n.position)
	var tile := float(map.tile) if map != null and "tile" in map else 1.0
	return Vector2i(floori(n.position.x / tile), floori(n.position.y / tile))


# --- the game's clock: qg:time-scale, and the lockstep's catching up ---
# Slow motion is the ticks coming further apart, not a tick that does less:
# the engine runs `slow` times as many ticks a second and slows its clock as
# much, so each tick still steps 1/60 of a second and is the same tick as
# ever — on every peer, in every replay. A rejoining peer's catching up
# (lockstep.gd) multiplies in.
var slow: float = 1.0      # the game's own speed (qg:time-scale)
var slow_ticks: int = 0    # engine ticks left before it is back to 1 (0: until changed)
var catch_up: int = 1      # the lockstep's: this many times faster while a peer catches up


static func time_scale(scale: float, seconds: float = 0.0) -> void:
	var q := _q_node()
	if q == null:
		return
	q.slow = scale
	# seconds as the player sees them: at a quarter of the speed, a quarter of the ticks
	q.slow_ticks = maxi(1, int(round(seconds * TICK_RATE * scale))) if seconds > 0.0 else 0
	q.apply_clock()
	event("time-scale", {"scale": scale})


func apply_clock() -> void:
	var ticks := maxi(1, int(round(TICK_RATE * slow)))
	Engine.physics_ticks_per_second = ticks * catch_up
	Engine.time_scale = float(ticks * catch_up) / TICK_RATE
	Engine.max_physics_steps_per_frame = 8 * catch_up * maxi(1, ceili(slow))


# --- quitting: qg:quit ---
var no_quit: bool = false   # the replay harness and the play protocol: a quit is an event, not the end


static func can_quit() -> bool:
	return not OS.has_feature("web")


static func quit() -> void:
	event("quit")
	var q := _q_node()
	if not can_quit() or (q != null and q.no_quit):
		return
	(Engine.get_main_loop() as SceneTree).quit()


# nearest(from, who) in an expression, and the parts of an enemy: the
# character whose id is `who`, or thing whose tag is ("": any character), nearest
# `from` in its scene; within `within` pixels, and seen (no solid tile
# between) when `seen`. The first in the scene's order on a tie; null for none.
static func nearest(from, who: String, within: float = INF, seen: bool = false):
	from = _thing(from)
	if from == null or not (from is Node2D) or from.get_parent() == null:
		return null
	var best = null
	var best_d := within
	for n in from.get_parent().get_children():
		if n == from or not (n is Node2D) or n.is_queued_for_deletion():
			continue
		var named: bool = n.is_in_group("q_named") and (who == "" or String(n.name) == who)
		var tagged: bool = who != "" and n.is_in_group("q_thing") and n.quantum_tag() == who
		if not named and not tagged:
			continue
		var d := (from as Node2D).position.distance_to((n as Node2D).position)
		if d > within or (best != null and d >= best_d):
			continue
		if seen and not sees(from, n):
			continue
		best = n
		best_d = d
	return best


# distance(a, b): pixels between two things or characters of a scene; INF when one is gone.
static func distance(a, b) -> float:
	a = _thing(a)
	b = _thing(b)
	if a == null or b == null or not (a is Node2D) or not (b is Node2D):
		return INF
	return (a as Node2D).position.distance_to((b as Node2D).position)


# sees(a, b): no solid tile of the scene's tilemap on the line between them,
# looked at every quarter of a tile.
static func sees(a, b) -> bool:
	a = _thing(a)
	b = _thing(b)
	if a == null or b == null or not (a is Node2D) or not (b is Node2D):
		return false
	var map = a.get_parent().get_node_or_null("Tilemap") if a.get_parent() != null else null
	if map == null or not map.has_method("blocked"):
		return true
	var walls: Dictionary = map.blocked()
	var from: Vector2 = (a as Node2D).position
	var to: Vector2 = (b as Node2D).position
	var steps := ceili(from.distance_to(to) / (float(map.tile) / 4.0))
	for i in range(1, steps):
		if walls.has(map.cell_of(from.lerp(to, float(i) / steps))):
			return false
	return true


# thing_at(tag, x, y): the thing (or zone) of the tag whose box covers the point ("" for any thing), or null.
# qg:set-tile and tile_at(): a cell of the scene's tilemap (tilemap.gd).
static func set_tile(ctx: Node, col, row, n, layer: String = "") -> void:
	var scene := _current_scene(ctx)
	var map = scene.get_node_or_null("Tilemap") if scene != null else null
	if map != null and map.has_method("set_tile"):
		map.set_tile(int(col), int(row), int(n), layer)
		event("tile", {"col": int(col), "row": int(row), "tile": int(n)})


static func tile_at(ctx: Node, col, row, layer: String = "") -> int:
	var scene := _current_scene(ctx)
	var map = scene.get_node_or_null("Tilemap") if scene != null else null
	return map.tile_at(int(col), int(row), layer) if map != null and map.has_method("tile_at") else 0


# tiled('par'): a property of the scene's Tiled map (null when it has none of that name).
static func tiled(ctx, key: String):
	var scene := _current_scene(ctx)
	return scene.q_spec.get("tiled", {}).get(key) if scene != null else null


static func thing_at(ctx: Node, tag: String, x: float, y: float):
	var scene := _current_scene(ctx)
	if scene == null or not scene.is_inside_tree():
		return null
	var point := Vector2(x, y)
	for t in scene.get_tree().get_nodes_in_group("q_thing"):
		if t.get_parent() != scene or t.is_queued_for_deletion():
			continue
		if tag != "" and t.quantum_tag() != tag:
			continue
		var size: Vector2 = t.hitbox_size if "hitbox_size" in t else Vector2(16, 16)
		if Rect2((t as Node2D).position - size / 2.0, size).has_point(point):
			return t
	if tag != "":
		for z in scene.get_children():
			if z is Area2D and "tag" in z and z.tag == tag and "hitbox_size" in z:
				if Rect2((z as Node2D).position - z.hitbox_size / 2.0, z.hitbox_size).has_point(point):
					return z
	return null


# Replaces a thing with another prefab, in its place (qg:swap).
static func swap(ctx: Node, node, prefab: String) -> Node:
	var scene := _current_scene(ctx)
	if scene == null:
		return null
	node = _thing(node)
	if node == null or not (node is Node2D):
		return null
	var builder = load("res://addons/quantum/scene_builder.gd")
	var made = builder.instance(scene.q_game, scene, prefab, (node as Node2D).position, true)
	destroy(node)
	return made


# The other thing's position becomes where the character respawns (qg:checkpoint).
static func checkpoint(node, at) -> void:
	node = _thing(node)
	at = _thing(at)
	if node != null and at != null and node.has_method("set_checkpoint") and at is Node2D:
		node.set_checkpoint((at as Node2D).position)


# Takes health from a thing (qg:damage).
static func damage(node, amount: int) -> void:
	node = _thing(node)
	if node != null and node.has_method("take_damage"):
		node.take_damage(amount)
		event("damage", {"what": who(node), "amount": amount, "health": node.get("health")})
		if node.get("health") != null and int(node.get("health")) <= 0:
			event("death", {"what": who(node)})


# Places a prefab at a point of the scene, at the end of the tick.
static func spawn_at(ctx: Node, prefab: String, at: Vector2) -> Node:
	var scene := _current_scene(ctx)
	if scene == null:
		return null
	var builder = load("res://addons/quantum/scene_builder.gd")
	return builder.instance(scene.q_game, scene, prefab, at, true)


# A puff of particles where a thing is (qg:burst). Cosmetic.
static func burst(node, color: String, count: int) -> void:
	node = _thing(node)
	if node == null or not (node is Node2D):
		return
	var scene := (node as Node).get_parent()
	if scene == null:
		return
	var puff := CPUParticles2D.new()
	puff.one_shot = true
	puff.emitting = true
	puff.amount = count
	puff.lifetime = 0.5
	puff.explosiveness = 1.0
	puff.direction = Vector2.ZERO
	puff.spread = 180.0
	puff.initial_velocity_min = 30.0
	puff.initial_velocity_max = 80.0
	puff.color = Color(color)
	puff.position = (node as Node2D).position
	scene.call_deferred("add_child", puff)
	puff.finished.connect(puff.queue_free)


# Shakes the scene a thing is in (qg:shake). Cosmetic.
static func shake(node, frames: int, strength: float) -> void:
	node = _thing(node)
	if node == null:
		return
	var scene := (node as Node).get_parent()
	if scene != null and scene.has_method("q_shake"):
		scene.q_shake(frames, strength)


# qg:pause / qg:resume, and paused(): the scene the handler is in, or the
# current one (a prefab's handler).
static func _current_scene(node) -> Node:
	if node is Node and (node as Node).has_method("q_pause"):
		return node
	return (Engine.get_main_loop() as SceneTree).get_first_node_in_group("q_scene")


static func pause(node, on: bool) -> void:
	var scene := _current_scene(node)
	if scene != null and scene.q_paused == on:
		return   # a dialogue opened from another's choice: still paused, nothing happened
	event("pause" if on else "resume")
	if scene != null:
		scene.q_pause(on)


static func paused(node) -> bool:
	var scene := _current_scene(node)
	return scene != null and scene.q_paused


# qg:say: opens a qg:dialogue of the scene (it pauses the scene until its last line).
static func say(node, dialogue: String) -> void:
	var scene := _current_scene(node)
	var box = scene.get_node_or_null("Dialogue_" + dialogue) if scene != null else null
	if box != null and not box.is_open():
		box.open()


# talking(): a qg:dialogue of the scene is open.
static func talking(node) -> bool:
	var scene := _current_scene(node)
	return scene != null and scene.q_talking() != ""


# Leaves the scene for another at the end of the tick (qg:goto-scene).
static func goto_scene(ctx: Node, name_: String, fade: float = 0.0) -> void:
	var scene := _current_scene(ctx)
	if scene == null:
		return
	var game := scene.get_parent()
	if game == null or not game.has_method("go_to_scene"):
		return
	# under the rollback, a scene change waits until the tick that asked is certain
	var net = game.get("lockstep")
	if net != null and net.has_method("request_scene") and net.started:
		net.request_scene(name_, fade)
		return
	game.call_deferred("go_to_scene", name_, fade)


# The solid part of a solid prefab: its shape= polygon (from its centre), or
# its hitbox. A polygon may be concave: CollisionPolygon2D splits it.
static func solid_shape(prefab: Dictionary) -> Node2D:
	var one_way := bool(prefab.get("one_way", false))
	if prefab.get("shape") != null:
		var poly := CollisionPolygon2D.new()
		var points := PackedVector2Array()
		for p in prefab["shape"]:
			points.append(Vector2(float(p[0]), float(p[1])))
		poly.polygon = points
		poly.one_way_collision = one_way
		return poly
	var rect := RectangleShape2D.new()
	rect.size = Vector2(prefab["hitbox"][0], prefab["hitbox"][1])
	var shape := CollisionShape2D.new()
	shape.shape = rect
	shape.one_way_collision = one_way
	return shape


# A collision hands the handler a hitbox area; the thing is its owner.
static func _thing(node):
	if node == null or not is_instance_valid(node):
		return null
	if node.has_method("quantum_owner"):
		return node.quantum_owner()
	return node


# --- persistence: the q:sets with saved="true" (G calls these) ---

# Where the file goes: --persist-dir=<dir> from the command line (the
# replay harness passes a temporary one), else user://.
var persist_dir: String = ""


func _ready() -> void:
	process_physics_priority = -1000
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--persist-dir="):
			persist_dir = a.substr(14)


func _physics_process(_delta: float) -> void:
	if slow_ticks > 0:
		slow_ticks -= 1
		if slow_ticks == 0:
			slow = 1.0
			apply_clock()
			event("time-scale", {"scale": 1.0})
	if external_input:
		return
	set_input(sample_local())
	var said := _said_here
	_said_here = []
	for s in said:
		deliver_said(int(s[0]), {s[1]: s[2]}, true)


# The game's actions pressed and released again between two ticks: a quick
# click, a tap on a screen. Sampling only what is held at each tick would lose
# them; they count as pressed for the next tick.
var _taps: Dictionary = {}


func _input(event: InputEvent) -> void:
	if not event.is_pressed() or event.is_echo() or typing():
		return
	for a in InputMap.get_actions():
		var name_ := String(a)
		if not name_.begins_with("ui_") and event.is_action_pressed(name_):
			_taps[name_] = true


# This machine's keys, for the tick: what is held, with its strength, and what
# was tapped since the last tick. The lockstep sends it; alone, it is the input.
# While a text box is being typed in (qg:field), the keys type: they play nothing.
func sample_local() -> Dictionary:
	var next := {}
	if typing():
		_taps.clear()
		return next
	for a in InputMap.get_actions():
		var name_ := String(a)
		if name_.begins_with("ui_"):
			continue
		var v := Input.get_action_strength(name_)
		if v > 0.0:
			next[name_] = v
	for name_ in _taps.keys():
		if not next.has(name_):
			next[name_] = 1.0
	_taps.clear()
	return next


# A text box (qg:field) has the keyboard.
func typing() -> bool:
	var focused := get_viewport().gui_get_focus_owner() if is_inside_tree() else null
	return focused is LineEdit


# Typing, as the keyboard would, into the text box being typed in: "\n" is
# Enter. The play protocol and the replay type with it ("type" in a tape).
func type_text(text: String) -> void:
	for ch in text:
		var k := InputEventKey.new()
		if ch == "\n":
			k.keycode = KEY_ENTER
			k.physical_keycode = KEY_ENTER
		else:
			k.unicode = ch.unicode_at(0)
			k.keycode = OS.find_keycode_from_string(ch.to_upper())   # a letter's key, as a keyboard sends
			k.physical_keycode = k.keycode
		k.pressed = true
		Input.parse_input_event(k)
		var up: InputEventKey = k.duplicate()
		up.pressed = false
		Input.parse_input_event(up)


# --- qg:field shared="true": what a player sends reaches every machine ---
# The text goes with this machine's input for a tick, as its keys do: in a
# networked game, in the lockstep's frame (rollback's too), so every machine
# hands it to the field on the same tick; alone, on the next tick.
var said_out: Dictionary = {}   # field key -> text: sent here, for the next frame this machine sends
var _said_here: Array = []      # alone: [player, key, text], for the next tick


func share(key: String, text: String, player: int) -> void:
	if external_input:
		said_out[key] = text
	else:
		_said_here.append([player, key, text])


func take_said() -> Dictionary:
	var out := said_out
	said_out = {}
	return out


# The texts a player sent for this tick, to the fields they were sent from
# (if the scene still has them): the bound state, then what the field holds.
# `mine`: sent from this machine.
func deliver_said(p: int, said: Dictionary, mine: bool) -> void:
	var keys := said.keys()
	keys.sort()
	for key in keys:
		for m in get_tree().get_nodes_in_group("q_menu"):
			if m.receive(str(key), p, str(said[key]), mine):
				break


# --- qg:on-input sequence=: presses in order, in time (a special move) ---
# Every action pressed (as it goes down) is kept a while, with how many ticks
# ago it went down. A sequence holds on the tick its last step is pressed, when
# its other steps were pressed before it, in order, within so many ticks
# (other presses between them do not matter); the presses it used are used
# up, so the same ones do not make it again. A networked game starts with none
# (clear_presses): what each machine pressed while it waited is its own.
const PRESSES_KEPT := 120
var _presses: Array = []    # [ticks ago, action], oldest first


func clear_presses() -> void:
	_presses = []


func sequence(steps: Array, within: int) -> bool:
	if steps.is_empty() or not tapped(steps[-1]):
		return false
	var i := _presses.size() - 1
	while i >= 0 and not (int(_presses[i][0]) == 0 and _presses[i][1] == steps[-1]):
		i -= 1
	if i < 0:
		return false
	var used := [i]
	var k := steps.size() - 2
	var j := i - 1
	while k >= 0 and j >= 0 and int(_presses[j][0]) <= within:
		if _presses[j][1] == steps[k]:
			used.append(j)
			k -= 1
		j -= 1
	if k >= 0:
		return false
	for u in used:   # from the last: the earlier places stay where they are
		_presses.remove_at(u)
	return true


# The input of the next tick: {action: strength}, only what is pressed.
func set_input(next: Dictionary) -> void:
	for e in _presses:
		e[0] = int(e[0]) + 1
	while not _presses.is_empty() and int(_presses[0][0]) > PRESSES_KEPT:
		_presses.pop_front()
	for a in next.keys():
		if not _now.has(a):
			_presses.append([0, a])
	_prev = _now
	_now = next
	_for_prev = _for
	_for = {}
	for a in next.keys():
		_for[a] = int(_for_prev.get(a, 0)) + 1
	if OS.has_feature("web"):
		for a in next.keys():
			if not _web_pressed.has(a):
				_web_pressed[a] = true
				web_report("quantumActions", ",".join(PackedStringArray(_web_pressed.keys())))


# In a browser, what the game is doing, for a page to read: window.quantumScene
# is the scene being played and window.quantumActions every action pressed
# since the start, comma-separated. The CI's browser check
# (scripts/check-games-in-browser.py) plays the web builds with them.
var _web_pressed: Dictionary = {}


static func web_report(key: String, value: String) -> void:
	if not OS.has_feature("web"):
		return
	var window = JavaScriptBridge.get_interface("window")
	if window != null:
		window[key] = value


func held(action: String) -> bool:
	return float(_now.get(action, 0.0)) > 0.0


func tapped(action: String) -> bool:
	return float(_now.get(action, 0.0)) > 0.0 and float(_prev.get(action, 0.0)) <= 0.0


# Let go this tick (qg:on-input on="release").
func released(action: String) -> bool:
	return float(_now.get(action, 0.0)) <= 0.0 and float(_prev.get(action, 0.0)) > 0.0


func strength(action: String) -> float:
	return float(_now.get(action, 0.0))


# pressing(action, player) and the like, with the player an expression: p2_run.
static func action_of(action: String, player) -> String:
	return action if int(player) == 1 else "p%d_%s" % [int(player), action]


# pressed_for(action): the ticks it has been held, this one counted; on the
# tick it is let go, the ticks it was held; else 0.
func held_ticks(action: String) -> int:
	if _now.has(action):
		return int(_for.get(action, 0))
	return int(_for_prev.get(action, 0)) if _prev.has(action) else 0


# --- the network, from a scene: qg:host, qg:join, qg:leave, net_*() ---

static func _game() -> Node:
	return (Engine.get_main_loop() as SceneTree).root.get_node_or_null("Game")


static func net_host(port: int) -> void:
	var g := _game()
	if g != null:
		g.net_host(port)


static func net_join(address) -> void:
	var g := _game()
	if g != null:
		g.net_join(str(address))


static func net_leave() -> void:
	var g := _game()
	if g != null:
		g.net_leave()


# qg:watch: join with no seat, to watch the game the players play.
static func net_watch(address) -> void:
	var g := _game()
	if g != null:
		g.net_watch(str(address))


# qg:start-now: the host starts with the players who are there (qg:multiplayer min-players=).
static func net_start_now() -> void:
	var g := _game()
	if g != null:
		g.net_start_now()


# url_param("join", default): in a web build, the page address's ?join=...;
# elsewhere (and when the page has none) the default. A link to the game can
# so carry the room to join: pong/index.html?join=wss://relay.example/pong/ROOM.
static func url_param(name_: String, default_):
	if OS.has_feature("web"):
		var v = JavaScriptBridge.eval("new URLSearchParams(window.location.search).get(%s)" % JSON.stringify(name_))
		if v != null and str(v) != "":
			return str(v)
	return default_


# qg:language: the game's texts in the player's language. A Label, a Button
# and the dialogue translate what they show by themselves (Godot's own
# translation); tr(text) in an expression is this, for a text put together.
# The game's ticks a second (common/physics_ticks_per_second, compiler.py). The
# runtime counts in these, never in Engine.physics_ticks_per_second: a peer
# that rejoins a networked game runs the engine faster while it catches up.
const TICK_RATE := 60.0

var languages: Array = []   # the game's languages besides its own
var lang: String = ""       # the one shown; "" is the game's own
var language_names: Dictionary = {}   # each language's own name for itself (qg:language name=)
var plurals: Dictionary = {}   # lang -> {a count's word: {one:, few:, many:}} (qg:phrase one= few= many=)
var language_fonts: Dictionary = {}   # lang -> Font: the letters of its alphabet the game's fonts lack
var _fonts: Array = []        # the fonts the game draws with, which take the languages' fonts as fallbacks
var _sound_specs: Dictionary = {}   # the qg:sounds, for those with a file per language (qg:asset)


# qg:next-language: the next of the game's languages, after its own; the
# choice is kept for the next run (next to the q:sets with saved="true").
# Only what is shown changes, so a networked game is played as before.
static func next_language() -> void:
	var q := _q_node()
	if q == null or q.languages.is_empty():
		return
	var order: Array = [""] + q.languages
	set_language(order[(order.find(q.lang) + 1) % order.size()])


static func set_language(code: String) -> void:
	var q := _q_node()
	if q == null:
		return
	q.lang = code if code in q.languages else ""
	TranslationServer.set_locale(q.lang if q.lang != "" else "en")
	q.language_assets()
	var f := FileAccess.open(_language_path(), FileAccess.WRITE)
	if f != null:
		f.store_string(q.lang if q.lang != "" else "-")
		f.close()
	event("language", {"lang": q.lang})


# The language chosen in an earlier run ("" none; "-" the game's own).
static func chosen_language() -> String:
	var f := FileAccess.open(_language_path(), FileAccess.READ)
	return f.get_as_text().strip_edges() if f != null else ""


static func _language_path() -> String:
	return _persist_file("quantum-language.txt")


# language(): the name of the language shown, in that language.
static func language_name() -> String:
	var q := _q_node()
	if q == null or q.lang == "":
		return "English"
	return str(q.language_names.get(q.lang, q.lang))


static func translate(text) -> String:
	return String(TranslationServer.translate(str(text)))


# tr_n(one, other, n): a count's word in the language shown, in its form for n (1 potion, 2 potions; in
# Russian 1 зелье, 2 зелья, 5 зелий): the phrase of other's one=, few= or many=, else the phrase of one
# (the form for one) or of other (the rest).
static func translate_n(one, other, n) -> String:
	var q := _q_node()
	var lang: String = q.lang if q != null else ""
	var form := plural_form(lang, int(n))
	var forms: Dictionary = q.plurals.get(lang, {}).get(str(other), {}) if q != null else {}
	if forms.has(form):
		return str(forms[form])
	return translate(one if form == "one" else other)


# The form of a count's word in a language, for a whole number (after CLDR): one, few, many or other.
static func plural_form(lang: String, n: int) -> String:
	n = absi(n)
	match lang.split("_")[0]:
		"ru", "uk", "be":
			if n % 10 == 1 and n % 100 != 11:
				return "one"
			return "few" if n % 10 >= 2 and n % 10 <= 4 and (n % 100 < 12 or n % 100 > 14) else "many"
		"pl":
			if n == 1:
				return "one"
			return "few" if n % 10 >= 2 and n % 10 <= 4 and (n % 100 < 12 or n % 100 > 14) else "many"
		"cs", "sk":
			return "one" if n == 1 else ("few" if n >= 2 and n <= 4 else "other")
		"fr":
			return "one" if n <= 1 else "other"
		"ja", "zh", "ko", "vi", "th", "id":
			return "other"
	return "one" if n == 1 else "other"


# A file of the game as it is in the language shown (qg:asset in a qg:language), else its own: a sheet's
# or a sound's src.
static func src_of(spec: Dictionary) -> String:
	var q := _q_node()
	var srcs: Dictionary = spec.get("srcs", {})
	if q != null and srcs.has(q.lang):
		return str(srcs[q.lang])
	return str(spec["src"])


# What the language shown changes besides the texts: the font each of the game's fonts falls back on first
# for a letter it lacks, and the sounds it has its own of. The pictures are the next scene's.
func language_assets() -> void:
	var order: Array = []
	if language_fonts.has(lang):
		order.append(language_fonts[lang])
	for code in language_fonts.keys():
		if code != lang:
			order.append(language_fonts[code])
	for f in _fonts:
		f.fallbacks = order
	for name_ in _sound_specs.keys():
		if _sound_specs[name_].has("srcs") and _sounds.has(name_):
			var stream := audio(src_of(_sound_specs[name_]), bool(_sound_specs[name_].get("loop", false)))
			if stream != null:
				_sounds[name_].stream = stream


static func net_status() -> String:
	var g := _game()
	return g.net_status() if g != null else "offline"


static func net_players() -> int:
	var g := _game()
	return g.net_players() if g != null else 0


static func net_player() -> int:
	var g := _game()
	return g.net_player() if g != null else 0


# For the rollback: the input state, and back to it.
func input_state() -> Array:
	return [_now.duplicate(), _prev.duplicate(), _for.duplicate(), _for_prev.duplicate(), _presses.duplicate(true)]


func restore_input(state: Array) -> void:
	_now = state[0].duplicate()
	_prev = state[1].duplicate()
	_for = state[2].duplicate()
	_for_prev = state[3].duplicate()
	_presses = state[4].duplicate(true)


func _persist_path() -> String:
	var base := persist_dir if persist_dir != "" else "user://"
	if not base.ends_with("/"):
		base += "/"
	return base + "quantum-state.json"


func load_persisted(state: Node, names: Array) -> void:
	if names.is_empty():
		return
	var f := FileAccess.open(_persist_path(), FileAccess.READ)
	if f == null:
		return
	var data = JSON.parse_string(f.get_as_text())
	if typeof(data) != TYPE_DICTIONARY:
		return
	for n in names:
		if data.has(n):
			state.set(n, data[n])


func save_persisted(state: Node, names: Array) -> void:
	if names.is_empty():
		return
	var data := {}
	for n in names:
		data[n] = state.get(n)
	var f := FileAccess.open(_persist_path(), FileAccess.WRITE)
	if f == null:
		push_warning("quantum: cannot write " + _persist_path())
		return
	f.store_string(JSON.stringify(data))


# --- saving: qg:save, qg:continue, has_save() ---
#
# A save, next to the q:sets with saved="true": the game's state (every q:set
# of <q:application>) and the scene to come back to. The scene starts over
# when it is continued; what was in it is not kept. A networked game is not
# saved: each machine would keep its own. With slot= there are several, a
# game each (quantum-save-2.json); the last slot saved or continued is the one
# a scene with save="true" saves into. Without, the one save.

var slot = null   # the save in use: null for the one save, else its number

static func _q_node() -> Node:
	return (Engine.get_main_loop() as SceneTree).root.get_node_or_null("Q")


static func _save_path(slot_ = null) -> String:
	if slot_ == null:
		var q := _q_node()
		slot_ = q.slot if q != null else null
	return _persist_file("quantum-save.json" if slot_ == null else "quantum-save-%d.json" % int(slot_))


static func _persist_file(file: String) -> String:
	var q := _q_node()
	var base: String = q.persist_dir if q != null and q.persist_dir != "" else "user://"
	if not base.ends_with("/"):
		base += "/"
	return base + file


static func _networked(scene: Node) -> bool:
	var game := scene.get_parent() if scene != null else null
	var net = game.get("lockstep") if game != null else null
	return net != null and net.started


static func save_game(ctx: Node, at: String = "", slot_ = null) -> void:
	var scene := _current_scene(ctx)
	if scene == null:
		return
	if _networked(scene):
		return
	if slot_ != null:
		_q_node().slot = int(slot_)
	var where := at if at != "" else String(scene.name)
	var f := FileAccess.open(_save_path(), FileAccess.WRITE)
	if f == null:
		push_warning("quantum: cannot write " + _save_path())
		return
	f.store_string(JSON.stringify({"scene": where, "game": G.quantum_state()}))
	f.close()
	var q := _q_node()
	event("save", {"scene": where} if q.slot == null else {"scene": where, "slot": q.slot})


# has_save(): the save in use (the one save, or the slot last used); has_save(2): that slot.
static func has_save(slot_ = null) -> bool:
	return FileAccess.file_exists(_save_path(slot_))


static func continue_game(ctx: Node, slot_ = null) -> void:
	var scene := _current_scene(ctx)   # P too: a prefab's handler, a function of the game there
	if scene == null:
		return
	if _networked(scene) or not has_save(slot_):
		return
	if slot_ != null:
		_q_node().slot = int(slot_)
	var f := FileAccess.open(_save_path(), FileAccess.READ)
	var data = JSON.parse_string(f.get_as_text()) if f != null else null
	if typeof(data) != TYPE_DICTIONARY or typeof(data.get("game")) != TYPE_DICTIONARY:
		push_warning("quantum: the save " + _save_path() + " cannot be read")
		return
	var known: Dictionary = G.quantum_state()
	for n in data["game"]:
		if known.has(n):   # a save from an older version of the game: what it still has
			G.set(n, data["game"][n])
	event("continue", {"scene": str(data.get("scene", ""))} if slot_ == null else {"scene": str(data.get("scene", "")), "slot": int(slot_)})
	goto_scene(scene, str(data.get("scene", "")))


# --- settings: how loud each bus is, the full screen, the keys (kept between runs) ---
#
# What the player chose on an options screen, in quantum-settings.json next
# to the saves: {"volume": {bus: 0 to 100}, "fullscreen": bool, "keys":
# {action: [key, ...]}}. Only heard, seen or pressed: the game's state never
# reads it, so replays and peers are as before (the lockstep carries actions).

var settings: Dictionary = {}
var _settings_read := false


func _settings() -> Dictionary:
	if not _settings_read:
		_settings_read = true
		var f := FileAccess.open(_persist_file("quantum-settings.json"), FileAccess.READ)
		var data = JSON.parse_string(f.get_as_text()) if f != null else null
		settings = data if typeof(data) == TYPE_DICTIONARY else {}
	return settings


func _keep_settings() -> void:
	var f := FileAccess.open(_persist_file("quantum-settings.json"), FileAccess.WRITE)
	if f == null:
		push_warning("quantum: cannot write the settings")
		return
	f.store_string(JSON.stringify(settings))


# The buses of the game's sounds (qg:sound bus=), under Master, at the volumes kept.
func make_buses(names: Array) -> void:
	for bus in names:
		if AudioServer.get_bus_index(bus) < 0:
			AudioServer.add_bus()
			var i := AudioServer.bus_count - 1
			AudioServer.set_bus_name(i, bus)
			AudioServer.set_bus_send(i, "Master")
		_apply_volume(bus)
	if bool(_settings().get("fullscreen", false)):
		_apply_fullscreen(true)


# volume('music'): how loud a bus is, 0 to 100.
func volume(bus: String) -> float:
	return float(_settings().get("volume", {}).get(bus, 100.0))


func set_volume(bus: String, value: float) -> void:
	var v := clampf(value, 0.0, 100.0)
	var volumes: Dictionary = _settings().get("volume", {})
	if volumes.get(bus) == v:
		return
	volumes[bus] = v
	settings["volume"] = volumes
	_keep_settings()
	_apply_volume(bus)
	event("volume", {"bus": bus, "value": v})


func _apply_volume(bus: String) -> void:
	var i := AudioServer.get_bus_index(bus)
	if i < 0:
		return
	var v := volume(bus)
	AudioServer.set_bus_mute(i, v <= 0.0)
	AudioServer.set_bus_volume_db(i, linear_to_db(maxf(v, 0.01) / 100.0))


func fullscreen() -> bool:
	return bool(_settings().get("fullscreen", false))


func set_fullscreen(on: bool) -> void:
	_settings()["fullscreen"] = on
	_keep_settings()
	_apply_fullscreen(on)
	event("fullscreen", {"on": on})


func _apply_fullscreen(on: bool) -> void:
	if DisplayServer.get_name() == "headless":
		return
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN if on else DisplayServer.WINDOW_MODE_WINDOWED)


# qg:rebind: the action's key of that kind (a key, a mouse button, a joypad
# button) becomes `ev`; the others stay. Kept, and put back on the next run.
func rebind(action: String, ev: InputEvent) -> void:
	if not InputMap.has_action(action):
		return
	for old in InputMap.action_get_events(action):
		if old.get_class() == ev.get_class():
			InputMap.action_erase_event(action, old)
	InputMap.action_add_event(action, ev)
	var keys: Dictionary = _settings().get("keys", {})
	keys[action] = InputMap.action_get_events(action).map(func(e): return _key_entry(e)).filter(func(e): return e != null)
	settings["keys"] = keys
	_keep_settings()
	event("rebind", {"action": action, "key": key_name(action)})


# The keys kept from an earlier run, over the game's own (quantum_game.gd, as the inputs are made).
func apply_keys() -> void:
	var keys: Dictionary = _settings().get("keys", {})
	for action in keys.keys():
		if not InputMap.has_action(action):
			continue
		InputMap.action_erase_events(action)
		for entry in keys[action]:
			var ev = _key_event(entry)
			if ev != null:
				InputMap.action_add_event(action, ev)


static func _key_entry(e: InputEvent):
	if e is InputEventKey:
		return OS.get_keycode_string((e as InputEventKey).physical_keycode)
	if e is InputEventMouseButton:
		return {"mouse_button": (e as InputEventMouseButton).button_index}
	if e is InputEventJoypadButton:
		return {"joy_button": (e as InputEventJoypadButton).button_index, "device": e.device}
	if e is InputEventJoypadMotion:
		return {"joy_axis": (e as InputEventJoypadMotion).axis, "value": (e as InputEventJoypadMotion).axis_value,
			"device": e.device}
	return null


static func _key_event(entry):
	if entry is Dictionary and entry.has("mouse_button"):
		var mb := InputEventMouseButton.new()
		mb.button_index = int(entry["mouse_button"])
		return mb
	if entry is Dictionary and entry.has("joy_button"):
		var jb := InputEventJoypadButton.new()
		jb.button_index = int(entry["joy_button"])
		jb.device = int(entry.get("device", 0))
		return jb
	if entry is Dictionary and entry.has("joy_axis"):
		var ja := InputEventJoypadMotion.new()
		ja.axis = int(entry["joy_axis"])
		ja.axis_value = float(entry["value"])
		ja.device = int(entry.get("device", 0))
		return ja
	if entry is String:
		var ev := InputEventKey.new()
		ev.physical_keycode = OS.find_keycode_from_string(entry)
		return ev
	return null


# The first key of an action, as a person reads it: Space, Left mouse, Joypad 0.
static func key_name(action: String) -> String:
	if not InputMap.has_action(action):
		return ""
	for e in InputMap.action_get_events(action):
		if e is InputEventKey:
			return OS.get_keycode_string((e as InputEventKey).physical_keycode)
	for e in InputMap.action_get_events(action):
		if e is InputEventMouseButton:
			return ["", "Left mouse", "Right mouse", "Middle mouse"][clampi((e as InputEventMouseButton).button_index, 0, 3)]
		if e is InputEventJoypadButton:
			return "Joypad %d" % (e as InputEventJoypadButton).button_index
	return ""


# --- sounds (an instance method: Q is an autoload node) ---

# --- the game's files: images, sounds, fonts ---
#
# A project on disk (the editor, a replay, the tests) has the files
# themselves, read as they are: no import step needed. An exported game (the
# browser, a desktop zip) carries only Godot's imported version of each file,
# which load() finds.

static func _imported(src: String) -> Resource:
	var path := "res://" + src
	if not FileAccess.file_exists(path) and ResourceLoader.exists(path):
		return load(path)
	return null


# A frame of a sheet as a picture of its own (a HUD's qg:icon).
static func frame_texture(sheet: Dictionary, frame: int) -> Texture2D:
	var texture := texture(src_of(sheet))
	if texture == null:
		return null
	var w := int(sheet["tile"][0])
	var h := int(sheet["tile"][1])
	var cols := maxi(1, texture.get_width() / w)
	var atlas := AtlasTexture.new()
	atlas.atlas = texture
	atlas.region = Rect2((frame % cols) * w, (frame / cols) * h, w, h)
	return atlas


static func texture(src: String) -> Texture2D:
	var res := _imported(src)
	if res is Texture2D:
		return res
	var image := Image.load_from_file(ProjectSettings.globalize_path("res://" + src))
	if image == null:
		return null
	return ImageTexture.create_from_image(image)


static func audio(src: String, loop: bool) -> AudioStream:
	var stream: AudioStream = null
	var res := _imported(src)
	if res is AudioStream:
		stream = res
	elif src.ends_with(".ogg"):
		stream = AudioStreamOggVorbis.load_from_file(ProjectSettings.globalize_path("res://" + src))
	elif src.ends_with(".wav"):
		stream = AudioStreamWAV.load_from_file(ProjectSettings.globalize_path("res://" + src))
	if stream == null:
		return null
	if stream is AudioStreamOggVorbis:
		stream.loop = loop
	elif stream is AudioStreamWAV and loop:
		var wav := stream as AudioStreamWAV
		wav.loop_mode = AudioStreamWAV.LOOP_FORWARD
		wav.loop_end = wav.data.size() / max(1, 2 if wav.format == AudioStreamWAV.FORMAT_16_BITS else 1) / max(1, 2 if wav.stereo else 1)
	return stream


static func font(src: String) -> Font:
	var loaded := load_font(src)
	var q := _q_node()
	if loaded != null and q != null and not q.language_fonts.is_empty() and not q._fonts.has(loaded):
		q._fonts.append(loaded)   # a letter it lacks comes from a language's font (qg:language font=)
		q.language_assets()
	return loaded


static func load_font(src: String) -> Font:
	var res := _imported(src)
	if res is Font:
		return res
	var file := FontFile.new()
	if file.load_dynamic_font(ProjectSettings.globalize_path("res://" + src)) == OK:
		return file
	return null


# A frame that stretches to a box (box= of a qg:dialogue or a qg:menu): the first frame of a sheet with
# slice=, its corners as drawn and its edges and middle stretched; what the box holds is pad pixels
# inside its edges.
static func frame_box(sheet: Dictionary, pad: float) -> StyleBoxTexture:
	var box := StyleBoxTexture.new()
	box.texture = texture(src_of(sheet))
	box.region_rect = Rect2(0, 0, int(sheet["tile"][0]), int(sheet["tile"][1]))
	var edges: Array = sheet["slice"]
	var sides := [SIDE_LEFT, SIDE_TOP, SIDE_RIGHT, SIDE_BOTTOM]
	for i in 4:
		box.set_texture_margin(sides[i], float(edges[i]))
		box.set_content_margin(sides[i], float(edges[i]) + pad)
	return box


# Quitting while a sound plays would leave its playback, and the imported
# stream it reads, alive after the engine: stop and drop them first.
func _exit_tree() -> void:
	for player in _sounds.values():
		player.stop()
		player.stream = null
	_sounds.clear()


func load_sounds(sounds: Dictionary) -> void:
	_sound_specs = sounds
	for name_ in sounds.keys():
		var src: String = src_of(sounds[name_])
		var stream := audio(src, bool(sounds[name_].get("loop", false)))
		if stream == null:
			push_warning("quantum: cannot load the sound " + src)
			continue
		var player := AudioStreamPlayer.new()
		player.name = name_
		player.stream = stream
		if sounds[name_].get("bus") != null:
			player.bus = str(sounds[name_]["bus"])   # made by make_buses, before
		apply_gd(player, sounds[name_].get("gd"))
		add_child(player)
		_sounds[name_] = player


var resimulating: bool = false   # the rollback replays old ticks: record sounds, play none


# qg:play. Plain, the sound's own player starts it again. With a volume, a
# pitch or a vary, it plays in a voice of its own (the same sound can then
# overlap itself), freed when it has played. Only heard: the state records the
# name, and the random pitch comes from a generator of its own, never the game's.
func play(name_: String, louder: float = 0.0, pitch: float = 1.0, vary: float = 0.0, at = null) -> void:
	sounds_played.append(name_)
	at = _thing(at)
	event("sound", _heard(name_, at))
	if not resimulating:
		_voice(name_, louder, pitch, vary, at)


# The sound event: its name, and where it was when it comes from a thing (at=).
static func _heard(name_: String, at) -> Dictionary:
	if at is Node2D:
		return {"name": name_, "x": snappedf((at as Node2D).position.x, 0.1), "y": snappedf((at as Node2D).position.y, 0.1)}
	return {"name": name_}


# What is heard of a sound played: as recorded, or in a voice of its own. From
# a thing (at=, a thing's own sounds), a voice where it is in the scene: softer
# and to one side the farther it is from the middle of the screen, silent two
# screens away. Only heard.
func _voice(name_: String, louder: float, pitch: float, vary: float, at = null) -> void:
	var player: AudioStreamPlayer = _sounds.get(name_)
	if player == null:
		return
	if at is Node2D and is_instance_valid(at):
		var spot := AudioStreamPlayer2D.new()
		spot.stream = player.stream
		spot.bus = player.bus
		spot.volume_db = player.volume_db + louder
		spot.pitch_scale = maxf(0.05, pitch + (_voices.randf_range(-vary, vary) if vary > 0.0 else 0.0))
		spot.max_distance = 2.0 * float(ProjectSettings.get_setting("display/window/size/viewport_width", 256))
		spot.position = (at as Node2D).position   # the scene's own space: it stands at the origin
		add_child(spot)
		spot.play()
		var span := player.stream.get_length() if player.stream != null else 1.0
		get_tree().create_timer(span / spot.pitch_scale + 0.1).timeout.connect(spot.queue_free)
		return
	if louder == 0.0 and pitch == 1.0 and vary == 0.0:
		player.play()
		return
	var voice := AudioStreamPlayer.new()
	voice.stream = player.stream
	voice.bus = player.bus
	voice.volume_db = player.volume_db + louder
	voice.pitch_scale = maxf(0.05, pitch + (_voices.randf_range(-vary, vary) if vary > 0.0 else 0.0))
	add_child(voice)
	voice.play()
	var length := player.stream.get_length() if player.stream != null else 1.0
	get_tree().create_timer(length / voice.pitch_scale + 0.1).timeout.connect(voice.queue_free)


var _voices := RandomNumberGenerator.new()   # the pitch of a voice: heard only, so not the game's generator


# qg:play sounds=: one of several, drawn by the voices' generator (heard only);
# the state records them as written, whichever was heard.
func play_one(names: Array, louder: float = 0.0, pitch: float = 1.0, vary: float = 0.0, at = null) -> void:
	var written := ", ".join(PackedStringArray(names))
	sounds_played.append(written)
	at = _thing(at)
	event("sound", _heard(written, at))
	if not resimulating and not names.is_empty():
		_voice(names[_voices.randi_range(0, names.size() - 1)], louder, pitch, vary, at)


# qg:music: the scene's music. Another one crossfades in over `fade` seconds,
# the same one plays on, none fades it out. Only what is heard changes: the
# game's state does not know the music, so replays are as before.
var music_playing: String = ""
var _music_tweens: Array = []


func music(spec) -> void:
	var to: String = "" if spec == null else str(spec["sound"])
	if to == music_playing:
		return
	var fade: float = 1.0 if spec == null else float(spec.get("fade", 1.0))
	for t in _music_tweens:
		t.kill()
	_music_tweens.clear()
	var old: AudioStreamPlayer = _sounds.get(music_playing)
	if old != null:
		_music_to(old, -80.0, fade, true)
	music_playing = to
	event("music", {"name": to})
	var player: AudioStreamPlayer = _sounds.get(to)
	if player == null:
		return
	var db: float = float(spec.get("volume", 0.0))
	if fade <= 0.0:
		player.volume_db = db
		player.play()
		return
	player.volume_db = -80.0
	player.play()
	_music_to(player, db, fade, false)


func _music_to(player: AudioStreamPlayer, db: float, seconds: float, then_stop: bool) -> void:
	if seconds <= 0.0:
		player.volume_db = db
		if then_stop:
			player.stop()
		return
	var tween := create_tween()
	tween.tween_property(player, "volume_db", db, seconds)
	if then_stop:
		tween.tween_callback(player.stop)
	_music_tweens.append(tween)


# qg:stop: the sound is silent (the replay state records it as "-name").
func stop(name_: String) -> void:
	sounds_played.append("-" + name_)
	var player: AudioStreamPlayer = _sounds.get(name_)
	if player != null:
		player.stop()
