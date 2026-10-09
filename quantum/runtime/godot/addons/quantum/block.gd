extends StaticBody2D
# A solid prefab instance (qg:prefab solid="true"): characters stand on it
# and bump it from below. Its Hitbox area carries the tag collisions see.


var prefab_name: String = ""
var tag: String = ""


func setup(name_: String, prefab: Dictionary, texture: Texture2D, tile: Array) -> void:
	prefab_name = name_
	tag = prefab["tag"]
	name = name_
	add_to_group("q_thing")
	collision_layer = 1
	collision_mask = 0
	var sprite := Sprite2D.new()
	sprite.name = "Sprite"
	sprite.texture = texture
	sprite.hframes = max(1, int(texture.get_width()) / int(tile[0]))
	sprite.vframes = max(1, int(texture.get_height()) / int(tile[1]))
	sprite.frame = int(prefab.get("frame", 0))
	add_child(sprite)
	var rect := RectangleShape2D.new()
	rect.size = Vector2(prefab["hitbox"][0], prefab["hitbox"][1])
	var shape := CollisionShape2D.new()
	shape.shape = rect
	shape.one_way_collision = bool(prefab.get("one_way", false))
	add_child(shape)
	var hitbox := Area2D.new()
	hitbox.name = "Hitbox"
	hitbox.set_script(load("res://addons/quantum/hitbox.gd"))
	var hit_shape := CollisionShape2D.new()
	hit_shape.shape = rect
	hitbox.add_child(hit_shape)
	add_child(hitbox)


func quantum_tag() -> String:
	return tag


func quantum_destroy() -> void:
	remove_from_group("q_thing")
	var hitbox := get_node_or_null("Hitbox")
	if hitbox != null:
		hitbox.set_deferred("monitorable", false)
	set_deferred("collision_layer", 0)
	queue_free()
