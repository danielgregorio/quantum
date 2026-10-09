extends CharacterBody2D
# A prefab instance that moves (qg:prefab ai="patrol"): walks at `speed`,
# turns at walls, and at edges when turns_at is "edge". Gravity keeps it on
# the ground. Its Hitbox (an Area2D) carries the tag collisions see.

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
var _heading: Vector2 = Vector2.ZERO
var _rethink: int = 0
var _scene: Node = null


func setup(name_: String, prefab: Dictionary, texture: Texture2D, tile: int) -> void:
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
	direction = -1 if prefab.get("direction", "left") == "left" else 1
	turns_at_edge = prefab.get("turns_at", "wall") == "edge"
	gravity = float(prefab.get("gravity", 900.0))
	hitbox_size = Vector2(prefab["hitbox"][0], prefab["hitbox"][1])

	var sprite := Sprite2D.new()
	sprite.name = "Sprite"
	sprite.texture = texture
	sprite.hframes = max(1, int(texture.get_width()) / tile)
	sprite.vframes = max(1, int(texture.get_height()) / tile)
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
	var hit_shape := CollisionShape2D.new()
	hit_shape.shape = rect
	hitbox.add_child(hit_shape)
	add_child(hitbox)

	animator = Animator.new()
	animator.name = "Animator"
	animator.setup(sprite, prefab.get("animations", {}))
	add_child(animator)
	animator.play("walk")


func quantum_tag() -> String:
	return tag


func quantum_destroy() -> void:
	remove_from_group("q_thing")
	var hitbox := get_node_or_null("Hitbox")
	if hitbox != null:
		hitbox.set_deferred("monitorable", false)
	queue_free()


func _physics_process(delta: float) -> void:
	match ai:
		"wander":
			_wander()
		"chase":
			_chase()
		_:
			_patrol(delta)


func _patrol(delta: float) -> void:
	velocity.y = minf(velocity.y + gravity * delta, 300.0)
	velocity.x = direction * speed
	move_and_slide()
	if is_on_wall():
		direction = -direction
	elif turns_at_edge and is_on_floor() and not _ground_ahead():
		direction = -direction
	var sprite := get_node_or_null("Sprite")
	if sprite != null:
		sprite.flip_h = direction > 0


# Top-down: a new heading every 30-90 ticks, from the scene's seeded
# random source, so the same seed gives the same wandering.
func _wander() -> void:
	if _scene == null:
		_scene = get_parent()
	if _rethink <= 0:
		var rng: RandomNumberGenerator = _scene.rng if "rng" in _scene else RandomNumberGenerator.new()
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
