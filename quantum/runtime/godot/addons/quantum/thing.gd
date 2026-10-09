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


func _ground_ahead() -> bool:
	var space := get_world_2d().direct_space_state
	var from := global_position + Vector2(direction * hitbox_size.x / 2.0, 0)
	var to := from + Vector2(0, hitbox_size.y / 2.0 + 4.0)
	var query := PhysicsRayQueryParameters2D.create(from, to)
	query.exclude = [get_rid()]
	return not space.intersect_ray(query).is_empty()
