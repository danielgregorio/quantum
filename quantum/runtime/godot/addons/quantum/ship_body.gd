extends CharacterBody2D
# The ship (qg:character controller="ship"): moves in eight directions at
# `speed`, kept inside the scene (bounds="scene"), and shoots fire_prefab
# above itself every fire_every ticks while fire_action is held. Touches
# fire qg:on-collision as for the other controllers, re-firing after the
# cooldown while the thing is still there.

const Animator := preload("res://addons/quantum/animator.gd")

var speed: float = 120.0
var bounds: bool = true
var axis: String = "both"
var fire_action: String = ""
var fire_prefab: String = ""
var fire_every: int = 10
var fire_sound: String = ""
var hitbox_size: Vector2 = Vector2(14, 14)
var spawn_point: Vector2 = Vector2.ZERO
var animator: Node = null
var state: String = ""
var player: int = 1

var _handlers: Array = []
var _cooldowns: Dictionary = {}
var _scene: Node = null
var _ticks: int = 0
var _fire_in: int = 0


func setup(spec: Dictionary) -> void:
	player = int(spec.get("player", 1))
	speed = float(spec.get("speed", speed))
	bounds = spec.get("bounds") != "none"
	axis = str(spec.get("axis", "both"))
	fire_action = str(spec.get("fire_action", "")) if spec.get("fire_action") != null else ""
	fire_prefab = str(spec.get("fire_prefab", "")) if spec.get("fire_prefab") != null else ""
	fire_every = int(spec.get("fire_every", 10))
	fire_sound = str(spec.get("fire_sound", "")) if spec.get("fire_sound") != null else ""
	hitbox_size = Vector2(spec["hitbox"][0], spec["hitbox"][1])
	motion_mode = CharacterBody2D.MOTION_MODE_FLOATING
	collision_mask = 0
	spawn_point = position


func wire(sensor: Area2D, spec: Dictionary, scene: Node, sprite: Sprite2D) -> void:
	_handlers = spec.get("on_collision", [])
	_scene = scene
	sensor.area_entered.connect(_touch)
	animator = Animator.new()
	animator.name = "Animator"
	animator.setup(sprite, spec.get("animations", {}))
	add_child(animator)
	animator.play("idle")


func respawn() -> void:
	position = spawn_point
	velocity = Vector2.ZERO


func _touch(area: Area2D) -> void:
	if not area.has_method("quantum_tag"):
		return
	var tag: String = area.quantum_tag()
	var other: Node = area.quantum_owner() if area.has_method("quantum_owner") else area
	for h in _handlers:
		if h["with"] == tag:
			_fire_handler(h, other)


func _still_touching() -> void:
	var sensor := get_node_or_null("Sensor")
	if sensor == null:
		return
	for area in sensor.get_overlapping_areas():
		if not area.has_method("quantum_tag"):
			continue
		var tag: String = area.quantum_tag()
		var other: Node = area.quantum_owner() if area.has_method("quantum_owner") else area
		for h in _handlers:
			if h["with"] == tag and int(h.get("cooldown", 0)) > 0 and _cooldowns.get(h["handler"], -1) <= _ticks:
				_fire_handler(h, other)


func _fire_handler(h: Dictionary, other: Node) -> bool:
	var name_: String = h["handler"]
	var cooldown := int(h.get("cooldown", 0))
	if cooldown > 0 and _cooldowns.get(name_, -1) > _ticks:
		return false
	if cooldown > 0:
		_cooldowns[name_] = _ticks + cooldown
	if _scene.has_method(name_):
		_scene.call(name_, self, other)
	return true


func _physics_process(delta: float) -> void:
	_ticks += 1
	# analog: a stick's strength scales the speed; a key is 1.0
	var dir := Vector2.ZERO
	if axis != "vertical":
		dir.x = Q.strength(_a("right")) - Q.strength(_a("left"))
	if axis != "horizontal":
		dir.y = Q.strength(_a("down")) - Q.strength(_a("up"))
	if dir.length() > 1.0:
		dir = dir.normalized()
	position += dir * speed * delta
	if bounds and "q_spec" in _scene:
		var w := float(_scene.q_spec.get("width", 256))
		var h := float(_scene.q_spec.get("height", 224))
		position.x = clampf(position.x, hitbox_size.x / 2.0, w - hitbox_size.x / 2.0)
		position.y = clampf(position.y, hitbox_size.y / 2.0, h - hitbox_size.y / 2.0)
	_still_touching()

	if _fire_in > 0:
		_fire_in -= 1
	if fire_action != "" and fire_prefab != "" and Q.held(_a(fire_action)) and _fire_in == 0:
		_fire_in = fire_every
		Q.spawn_at(_scene, fire_prefab, position + Vector2(0, -hitbox_size.y / 2.0 - 4.0))
		if fire_sound != "":
			Q.play(fire_sound)


# The input action of this player: "up" for player 1, "p2_up" for player 2.
func _a(action: String) -> String:
	return action if player == 1 else "p%d_%s" % [player, action]
