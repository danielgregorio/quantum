extends Area2D
# A prefab placed in the scene (qg:instance): a sprite with a tag that
# collisions see (qg:on-collision with="coin"), playing its "walk"
# animation when it has one (a coin that spins).

const Animator := preload("res://addons/quantum/animator.gd")

var prefab_name: String = ""
var tag: String = ""


func setup(name_: String, prefab: Dictionary, texture: Texture2D, tile: Array) -> void:
	prefab_name = name_
	tag = prefab["tag"]
	name = name_
	add_to_group("q_thing")
	var sprite := Sprite2D.new()
	sprite.name = "Sprite"
	sprite.texture = texture
	sprite.hframes = max(1, int(texture.get_width()) / int(tile[0]))
	sprite.vframes = max(1, int(texture.get_height()) / int(tile[1]))
	sprite.frame = int(prefab.get("frame", 0))
	sprite.scale = Vector2.ONE * float(prefab.get("scale", 1.0))
	add_child(sprite)
	if not prefab.get("animations", {}).is_empty():
		var animator := Animator.new()
		animator.name = "Animator"
		animator.setup(sprite, prefab["animations"])
		add_child(animator)
		animator.play("walk")
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(prefab["hitbox"][0], prefab["hitbox"][1])
	shape.shape = rect
	add_child(shape)


func quantum_tag() -> String:
	return tag


func quantum_destroy() -> void:
	# Out of the physics world at once, so the same tick cannot touch it twice.
	set_deferred("monitorable", false)
	remove_from_group("q_thing")
	queue_free()
