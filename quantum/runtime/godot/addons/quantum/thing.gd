extends CharacterBody2D
# A prefab instance that moves (qg:prefab ai=). Its Hitbox (an Area2D)
# carries the tag collisions see, and reports what it touches to the
# prefab's own qg:on-collision handlers (in P).
#
# ai: patrol walks under gravity and turns at walls (and edges);
# wander and chase are top-down; fly goes straight along `heading` and is
# gone after `lifetime` ticks or off-screen; sway goes side to side across
# the scene. health is taken by qg:damage: on-damage runs while it lives,
# on-death when it reaches 0, then it goes. States (qg:state) change its
# frame, speed and fire-every.

const Animator := preload("res://addons/quantum/animator.gd")

var prefab_name: String = ""
var tag: String = ""
var speed: float = 30.0
var direction: int = -1
var turns_at_edge: bool = false
var gravity: float = 900.0
var hitbox_size: Vector2 = Vector2(16, 16)
var animator: Node = null
var ai: String = "patrol"
var sight: float = 80.0
var heading: Vector2 = Vector2.DOWN
var lifetime: int = 0
var accel: float = 0.0
var spawn_point: Vector2 = Vector2.ZERO
var health: int = 1
var fire_prefab: String = ""
var fire_every: int = 0
var fire_sound: String = ""
var state: String = ""

var _heading: Vector2 = Vector2.ZERO
var _rethink: int = 0
var _scene: Node = null
var _age: int = 0
var _fire_in: int = 0
var _handlers: Array = []
var _cooldowns: Dictionary = {}
var _on_damage: String = ""
var _on_death: String = ""
var _states: Dictionary = {}
var _base: Dictionary = {}
var _dead: bool = false
var _ticks: int = 0


func setup(name_: String, prefab: Dictionary, texture: Texture2D, tile: Array) -> void:
	prefab_name = name_
	tag = prefab["tag"]
	name = name_
	add_to_group("q_thing")
	# Layer 2: things collide with the tiles (mask 1) but not with the
	# characters, whose bodies only see layer 1; touching is the areas' job.
	collision_layer = 2
	collision_mask = 1
	speed = float(prefab.get("speed", 30.0))
	ai = str(prefab.get("ai", "patrol"))
	sight = float(prefab.get("sight", 80.0))
	if ai != "patrol":
		motion_mode = CharacterBody2D.MOTION_MODE_FLOATING
	if ai == "fly" or ai == "sway":
		collision_mask = 0   # through everything: a shot or a drone is stopped by nothing
	direction = -1 if prefab.get("direction", "left") == "left" else 1
	turns_at_edge = prefab.get("turns_at", "wall") == "edge"
	gravity = float(prefab.get("gravity", 900.0))
	hitbox_size = Vector2(prefab["hitbox"][0], prefab["hitbox"][1])
	var h = prefab.get("heading", [0.0, 1.0])
	heading = Vector2(h[0], h[1]) if h is Array else Vector2.DOWN
	accel = float(prefab.get("accel", 0.0))
	lifetime = int(prefab.get("lifetime", 0))
	health = int(prefab.get("health", 1))
	fire_prefab = str(prefab.get("fire_prefab", "")) if prefab.get("fire_prefab") != null else ""
	fire_every = int(prefab.get("fire_every", 0)) if prefab.get("fire_every") != null else 0
	fire_sound = str(prefab.get("fire_sound", "")) if prefab.get("fire_sound") != null else ""
	_fire_in = fire_every
	_handlers = prefab.get("on_collision", [])
	_on_damage = str(prefab.get("on_damage", "")) if prefab.get("on_damage") != null else ""
	_on_death = str(prefab.get("on_death", "")) if prefab.get("on_death") != null else ""
	_states = prefab.get("states", {})
	_base = {"frame": int(prefab.get("frame", 0)), "speed": speed, "fire_every": fire_every, "heading": heading}

	var sprite := Sprite2D.new()
	sprite.name = "Sprite"
	sprite.texture = texture
	sprite.hframes = max(1, int(texture.get_width()) / int(tile[0]))
	sprite.vframes = max(1, int(texture.get_height()) / int(tile[1]))
	sprite.frame = int(prefab.get("frame", 0))
	add_child(sprite)

	var rect := RectangleShape2D.new()
	rect.size = hitbox_size
	var shape := CollisionShape2D.new()
	shape.shape = rect
	add_child(shape)

	var hitbox := Area2D.new()
	hitbox.name = "Hitbox"
	hitbox.set_script(load("res://addons/quantum/hitbox.gd"))
	hitbox.collision_layer = 1
	hitbox.collision_mask = 1
	var hit_shape := CollisionShape2D.new()
	hit_shape.shape = rect
	hitbox.add_child(hit_shape)
	add_child(hitbox)
	if _handlers.size() > 0:
		hitbox.area_entered.connect(_on_hitbox_entered)

	animator = Animator.new()
	animator.name = "Animator"
	animator.setup(sprite, prefab.get("animations", {}))
	add_child(animator)
	animator.play("walk")
	if prefab.get("initial_state") != null:
		become(str(prefab["initial_state"]))


func _ready() -> void:
	spawn_point = position


func quantum_tag() -> String:
	return tag


# qg:respawn target="other": back where it was placed, as it was declared.
func respawn() -> void:
	position = spawn_point
	velocity = Vector2.ZERO
	heading = _base["heading"]
	speed = float(_base["speed"])
	_age = 0


# qg:deflect axis=: the heading's x or y the other way (a bounce).
func deflect_axis(axis: String) -> void:
	if axis == "x":
		heading.x = -heading.x
	else:
		heading.y = -heading.y


# qg:deflect dx= dy=: a new heading.
func deflect_to(dx: float, dy: float) -> void:
	var v := Vector2(dx, dy)
	if v.length() > 0.0:
		heading = v.normalized()


func quantum_destroy() -> void:
	_dead = true
	remove_from_group("q_thing")
	var hitbox := get_node_or_null("Hitbox")
	if hitbox != null:
		hitbox.set_deferred("monitorable", false)
		hitbox.set_deferred("monitoring", false)
	queue_free()


# qg:damage: health down; on-damage while it lives, on-death at 0.
func take_damage(amount: int) -> void:
	if _dead:
		return
	health -= amount
	if health > 0:
		if _on_damage != "" and P.has_method(_on_damage):
			P.call(_on_damage, self, null)
		return
	_dead = true
	if _on_death != "" and P.has_method(_on_death):
		P.call(_on_death, self, null)
	var scene := get_parent()
	if scene != null and scene.has_method("q_thing_died"):
		scene.q_thing_died(self)
	quantum_destroy()


# qg:become: one of the prefab's states.
func become(name_: String) -> void:
	if not _states.has(name_) or name_ == state:
		return
	state = name_
	var st: Dictionary = _states[name_]
	var sprite: Sprite2D = get_node_or_null("Sprite")
	if sprite != null:
		sprite.frame = int(st.get("frame", _base["frame"]))
	speed = float(st["speed"]) if st.get("speed") != null else float(_base["speed"])
	fire_every = int(st["fire_every"]) if st.get("fire_every") != null else int(_base["fire_every"])
	if animator != null and st.get("animations", {}).size() > 0:
		animator.animations = st["animations"]
		animator.current = ""
		animator.play("walk")


func _on_hitbox_entered(area: Area2D) -> void:
	if _dead or not area.has_method("quantum_tag"):
		return
	var other_tag: String = area.quantum_tag()
	var other: Node = area.quantum_owner() if area.has_method("quantum_owner") else area
	if other == self:
		return
	for h in _handlers:
		if h["with"] != other_tag:
			continue
		var cooldown := int(h.get("cooldown", 0))
		if cooldown > 0 and _cooldowns.get(h["handler"], -1) > _ticks:
			continue
		if cooldown > 0:
			_cooldowns[h["handler"]] = _ticks + cooldown
		if P.has_method(h["handler"]):
			P.call(h["handler"], self, other)


func _physics_process(delta: float) -> void:
	if _dead:
		return
	_ticks += 1
	_age += 1
	match ai:
		"wander":
			_wander()
		"chase":
			_chase()
		"fly":
			_fly(delta)
		"sway":
			_sway(delta)
		_:
			_patrol(delta)
	_fire()


func _fire() -> void:
	if fire_prefab == "" or fire_every <= 0 or _scene_of() == null:
		return
	_fire_in -= 1
	if _fire_in > 0:
		return
	_fire_in = fire_every
	var below := position + Vector2(0, hitbox_size.y / 2.0 + 4.0) * (-1.0 if heading == Vector2.UP else 1.0)
	Q.spawn_at(_scene_of(), fire_prefab, below)
	if fire_sound != "":
		Q.play(fire_sound)


func _scene_of() -> Node:
	if _scene == null:
		_scene = get_parent()
	return _scene


func _patrol(delta: float) -> void:
	velocity.y = minf(velocity.y + gravity * delta, 300.0)
	velocity.x = direction * speed
	move_and_slide()
	if is_on_wall():
		direction = -direction
	elif turns_at_edge and is_on_floor() and not _ground_ahead():
		direction = -direction
	_face(direction)


# Top-down: a new heading every 30-90 ticks, from the scene's seeded
# random source, so the same seed gives the same wandering.
func _wander() -> void:
	var scene := _scene_of()
	if _rethink <= 0:
		var rng: RandomNumberGenerator = scene.rng if "rng" in scene else RandomNumberGenerator.new()
		var angle := rng.randf_range(0.0, TAU)
		_heading = Vector2(cos(angle), sin(angle))
		_rethink = rng.randi_range(30, 90)
	_rethink -= 1
	velocity = _heading * speed
	move_and_slide()
	if get_slide_collision_count() > 0:
		_rethink = 0
	_face(velocity.x)


# Top-down: goes for the nearest named character within sight.
func _chase() -> void:
	var target: Node2D = null
	var best := sight
	for n in get_tree().get_nodes_in_group("q_named"):
		if n is Node2D and n.get_parent() == get_parent():
			var d := global_position.distance_to((n as Node2D).global_position)
			if d < best:
				best = d
				target = n
	if target == null:
		velocity = Vector2.ZERO
		return
	velocity = (target.global_position - global_position).normalized() * speed
	move_and_slide()
	_face(velocity.x)


# Straight along the heading; gone when old or out of the scene.
func _fly(delta: float) -> void:
	speed += accel * delta
	position += heading * speed * delta
	if lifetime > 0 and _age >= lifetime:
		quantum_destroy()
		return
	var scene := _scene_of()
	if scene != null and "q_spec" in scene:
		var w := float(scene.q_spec.get("width", 256))
		var h := float(scene.q_spec.get("height", 224))
		if position.x < -32.0 or position.x > w + 32.0 or position.y < -32.0 or position.y > h + 32.0:
			quantum_destroy()


# Side to side across the scene, turning at its edges.
func _sway(delta: float) -> void:
	var scene := _scene_of()
	var w := 256.0
	if scene != null and "q_spec" in scene:
		w = float(scene.q_spec.get("width", 256))
	position.x += direction * speed * delta
	if position.x < hitbox_size.x:
		position.x = hitbox_size.x
		direction = 1
	elif position.x > w - hitbox_size.x:
		position.x = w - hitbox_size.x
		direction = -1
	_face(direction)


func _face(vx: float) -> void:
	var sprite := get_node_or_null("Sprite")
	if sprite != null and vx != 0.0:
		sprite.flip_h = vx > 0


func _ground_ahead() -> bool:
	var space := get_world_2d().direct_space_state
	var from := global_position + Vector2(direction * hitbox_size.x / 2.0, 0)
	var to := from + Vector2(0, hitbox_size.y / 2.0 + 4.0)
	var query := PhysicsRayQueryParameters2D.create(from, to)
	query.exclude = [get_rid()]
	return not space.intersect_ray(query).is_empty()
