extends CharacterBody2D
# The top-down controller (qg:character controller="topdown"): walks in
# eight directions at `speed`, faces the last direction, and swings in
# front of itself on attack_action for attack_frames ticks — what the
# swing reaches fires the qg:on-hit handlers. Touches fire qg:on-collision
# as for the platformer, without sides. Deterministic: everything in
# _physics_process at the fixed tick.

const Animator := preload("res://addons/quantum/animator.gd")

var speed: float = 70.0
var attack_action: String = ""
var attack_reach: float = 16.0
var attack_frames: int = 12
var attack_sound: String = ""
var hitbox_size: Vector2 = Vector2(14, 14)
var facing: Vector2 = Vector2.DOWN
var animator: Node = null
var state: String = ""
var player: int = 1

var _handlers: Array = []
var _hits: Array = []
var _cooldowns: Dictionary = {}
var _scene: Node = null
var _ticks: int = 0
var _swing: Area2D = null
var _swing_shape: CollisionShape2D = null
var _swinging: int = 0
var _hit_this_swing: Array = []


func setup(spec: Dictionary) -> void:
	player = int(spec.get("player", 1))
	speed = float(spec.get("speed", speed))
	attack_action = str(spec.get("attack_action", "")) if spec.get("attack_action") != null else ""
	attack_reach = float(spec.get("attack_reach", attack_reach))
	attack_frames = int(spec.get("attack_frames", attack_frames))
	attack_sound = str(spec.get("attack_sound", "")) if spec.get("attack_sound") != null else ""
	hitbox_size = Vector2(spec["hitbox"][0], spec["hitbox"][1])
	motion_mode = CharacterBody2D.MOTION_MODE_FLOATING


func wire(sensor: Area2D, spec: Dictionary, scene: Node, sprite: Sprite2D) -> void:
	_handlers = spec.get("on_collision", [])
	_hits = spec.get("on_hit", [])
	_scene = scene
	sensor.area_entered.connect(_on_area_entered)
	animator = Animator.new()
	animator.name = "Animator"
	animator.setup(sprite, spec.get("animations", {}))
	add_child(animator)
	animator.play("idle")
	if attack_action != "":
		_swing = Area2D.new()
		_swing.name = "Swing"
		_swing.monitorable = false
		_swing.collision_mask = 1 | 2
		_swing_shape = CollisionShape2D.new()
		var rect := RectangleShape2D.new()
		rect.size = Vector2(attack_reach, attack_reach)   # resized to the facing on each swing
		_swing_shape.shape = rect
		_swing_shape.disabled = true
		_swing.add_child(_swing_shape)
		add_child(_swing)
		_swing.area_entered.connect(_on_swing_reached)


func quantum_node_state() -> Dictionary:
	return {"facing": [int(facing.x), int(facing.y)]}


func respawn() -> void:
	velocity = Vector2.ZERO


func _on_area_entered(area: Area2D) -> void:
	_touch(area)


# A touch fires its handlers on entering; a handler with a cooldown fires
# again while the thing is still there, each time the cooldown runs out
# (a monster that sits on you keeps hurting).
func _touch(area: Area2D) -> void:
	if not area.has_method("quantum_tag"):
		return
	var tag: String = area.quantum_tag()
	var other: Node = area.quantum_owner() if area.has_method("quantum_owner") else area
	for h in _handlers:
		if h["with"] == tag:
			_fire(h, other)


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
				_fire(h, other)


func _on_swing_reached(area: Area2D) -> void:
	if _swinging <= 0 or not area.has_method("quantum_tag"):
		return
	var tag: String = area.quantum_tag()
	var other: Node = area.quantum_owner() if area.has_method("quantum_owner") else area
	if other in _hit_this_swing:
		return
	_hit_this_swing.append(other)
	for h in _hits:
		if h["with"] == tag and _scene.has_method(h["handler"]):
			_scene.call(h["handler"], self, other)


func _fire(h: Dictionary, other: Node) -> bool:
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
	var dir := Vector2.ZERO
	if Input.is_action_pressed(_a("right")):
		dir.x += 1
	if Input.is_action_pressed(_a("left")):
		dir.x -= 1
	if Input.is_action_pressed(_a("down")):
		dir.y += 1
	if Input.is_action_pressed(_a("up")):
		dir.y -= 1
	if dir != Vector2.ZERO:
		facing = dir.normalized()
		var sprite := get_node_or_null("Sprite")
		if sprite != null and dir.x != 0:
			sprite.flip_h = dir.x < 0
	velocity = dir.normalized() * speed
	move_and_slide()
	_still_touching()

	if _swinging > 0:
		_swinging -= 1
		if _swinging == 0:
			_swing_shape.set_deferred("disabled", true)
	elif attack_action != "" and Input.is_action_just_pressed(_a(attack_action)):
		_swinging = attack_frames
		_hit_this_swing = []
		# The swing: `reach` deep in front of the body, and as wide as the
		# body plus half the reach, so a thing coming in at an angle is met.
		var along := facing.abs()
		var half := Vector2(hitbox_size.x / 2.0 * along.x + hitbox_size.y / 2.0 * along.y, 0).x
		if along.x > 0.0 and along.y > 0.0:
			half = hitbox_size.length() / 2.0
		_swing.position = facing * (half + attack_reach / 2.0)
		var wide := maxf(hitbox_size.x, hitbox_size.y) + attack_reach / 2.0
		var size := Vector2(attack_reach, wide) if abs(facing.x) >= abs(facing.y) else Vector2(wide, attack_reach)
		if along.x > 0.0 and along.y > 0.0:
			size = Vector2(wide, wide)
		_swing_shape.shape.set_deferred("size", size)
		_swing_shape.set_deferred("disabled", false)
		if attack_sound != "":
			Q.play(attack_sound)

	if animator != null:
		if dir != Vector2.ZERO and animator.has("walk"):
			animator.play("walk")
		elif animator.has("idle"):
			animator.play("idle")


# The input action of this player: "up" for player 1, "p2_up" for player 2.
func _a(action: String) -> String:
	return action if player == 1 else "p%d_%s" % [player, action]
