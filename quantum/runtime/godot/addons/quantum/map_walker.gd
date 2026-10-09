extends Node2D
# The walker on a world map (qg:character controller="map"): stands on a
# qg:map-node; a direction press sends it along a qg:map-path to the
# neighbour that way, if the path is open (its `requires` scene is in the
# game's `cleared`); "jump" on a node with a scene enters that scene.

const Animator := preload("res://addons/quantum/animator.gd")

var at: String = ""            # the node it stands on (or left)
var going_to: String = ""      # the node it glides to, or ""
var speed: float = 60.0
var nodes: Dictionary = {}     # name -> {x, y, scene}
var paths: Array = []          # [{from, to, requires}]
var animator: Node = null
var _scene: Node = null
var _target: Vector2 = Vector2.ZERO


func setup(spec: Dictionary, map_nodes: Dictionary, map_paths: Array, scene: Node, sprite: Sprite2D) -> void:
	speed = float(spec.get("speed", 60.0))
	nodes = map_nodes
	paths = map_paths
	_scene = scene
	add_to_group("q_named")
	name = spec["id"]
	animator = Animator.new()
	animator.name = "Animator"
	animator.setup(sprite, spec.get("animations", {}))
	add_child(animator)
	animator.play("idle")


func place(node_name: String) -> void:
	if not nodes.has(node_name):
		node_name = nodes.keys()[0] if nodes.size() > 0 else ""
	at = node_name
	going_to = ""
	if at != "":
		position = Vector2(nodes[at]["x"], nodes[at]["y"])


func quantum_node_state() -> Dictionary:
	return {"at": at, "going_to": going_to}


func _open(path: Dictionary) -> bool:
	var requires = path.get("requires")
	if requires == null:
		return true
	var cleared = G.get("cleared")
	return cleared is Array and requires in cleared


func _neighbour(dir: Vector2) -> String:
	var best := ""
	var best_dot := 0.5
	var here := Vector2(nodes[at]["x"], nodes[at]["y"])
	for p in paths:
		var other := ""
		if p["from"] == at:
			other = p["to"]
		elif p["to"] == at:
			other = p["from"]
		else:
			continue
		if not _open(p):
			continue
		var there := Vector2(nodes[other]["x"], nodes[other]["y"])
		var dot := (there - here).normalized().dot(dir)
		if dot > best_dot:
			best_dot = dot
			best = other
	return best


func _physics_process(delta: float) -> void:
	if going_to != "":
		var step := speed * delta
		if position.distance_to(_target) <= step:
			position = _target
			at = going_to
			going_to = ""
			animator.play("idle")
		else:
			position += (_target - position).normalized() * step
		return
	if at == "":
		return
	var dir := Vector2.ZERO
	if Input.is_action_just_pressed("right"):
		dir = Vector2.RIGHT
	elif Input.is_action_just_pressed("left"):
		dir = Vector2.LEFT
	elif Input.is_action_just_pressed("up"):
		dir = Vector2.UP
	elif Input.is_action_just_pressed("down"):
		dir = Vector2.DOWN
	if dir != Vector2.ZERO:
		var next := _neighbour(dir)
		if next != "":
			going_to = next
			_target = Vector2(nodes[next]["x"], nodes[next]["y"])
			var sprite := get_node_or_null("Sprite")
			if sprite != null:
				sprite.flip_h = dir.x < 0
			animator.play("walk")
		return
	if Input.is_action_just_pressed("jump"):
		var scene_name = nodes[at].get("scene")
		if scene_name != null and scene_name != "":
			G.map_at = at
			Q.goto_scene(_scene, scene_name)
