extends AnimatableBody2D
# A moving platform (qg:prefab solid="true" ai="shuttle"): goes dx, dy
# from where it is placed and back, every `period` ticks, carrying what
# stands on it (sync_to_physics). Its Hitbox carries the tag.

var prefab_name: String = ""
var tag: String = ""
var dx: float = 0.0
var dy: float = 0.0
var period: int = 240
var _origin: Vector2 = Vector2.ZERO
var _ticks: int = 0


func setup(name_: String, prefab: Dictionary, texture: Texture2D, tile: int) -> void:
	prefab_name = name_
	tag = prefab["tag"]
	name = name_
	add_to_group("q_thing")
	collision_layer = 1
	collision_mask = 0
	sync_to_physics = true
	dx = float(prefab.get("dx", 0.0))
	dy = float(prefab.get("dy", 0.0))
	period = maxi(2, int(prefab.get("period", 240)))
	var sprite := Sprite2D.new()
	sprite.name = "Sprite"
	sprite.texture = texture
	sprite.hframes = max(1, int(texture.get_width()) / tile)
	sprite.vframes = max(1, int(texture.get_height()) / tile)
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


func _ready() -> void:
	_origin = position


func quantum_tag() -> String:
	return tag


func quantum_destroy() -> void:
	remove_from_group("q_thing")
	set_deferred("collision_layer", 0)
	queue_free()


# There and back along a triangle wave, so it never jumps.
func _physics_process(_delta: float) -> void:
	_ticks = (_ticks + 1) % period
	var half := period / 2.0
	var t := _ticks / half
	if t > 1.0:
		t = 2.0 - t
	position = _origin + Vector2(dx, dy) * t
