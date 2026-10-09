extends Node
# Cycles a Sprite2D's frames from a qg:animation table, by physics ticks,
# so a replay sees the same frames. `play(name)` switches animation; the
# same name again does nothing.

var sprite: Sprite2D = null
var animations: Dictionary = {}   # name -> {frames: [..], fps: f}
var current: String = ""
var _ticks: float = 0.0
var _index: int = 0


func setup(sprite_: Sprite2D, animations_: Dictionary) -> void:
	sprite = sprite_
	animations = animations_


func has(name_: String) -> bool:
	return animations.has(name_)


func play(name_: String) -> void:
	if name_ == current or not animations.has(name_):
		return
	current = name_
	_index = 0
	_ticks = 0.0
	sprite.frame = int(animations[current]["frames"][0])


func _physics_process(_delta: float) -> void:
	if current == "":
		return
	var anim: Dictionary = animations[current]
	var frames: Array = anim["frames"]
	if frames.size() < 2:
		return
	_ticks += float(anim.get("fps", 8.0)) / Engine.physics_ticks_per_second
	while _ticks >= 1.0:
		_ticks -= 1.0
		_index = (_index + 1) % frames.size()
		sprite.frame = int(frames[_index])
