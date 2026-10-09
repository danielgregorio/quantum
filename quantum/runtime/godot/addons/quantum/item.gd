extends Area2D
# A prefab placed in the scene (qg:instance): a sprite with a tag that
# collisions see (qg:on-collision with="coin").

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
	add_child(sprite)
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
