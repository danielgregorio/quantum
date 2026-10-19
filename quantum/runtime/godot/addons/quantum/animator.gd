extends Node
# Cycles a Sprite2D's frames from a qg:animation table, by physics ticks,
# so a replay sees the same frames. `play(name)` switches animation; the
# same name again does nothing.
#
# An animation with loop="false" plays once and stays on its last frame;
# as it ends, the owner's qg:on-animation-end handlers of that name run.
# `force(name)` is qg:play-animation: the body's own choice (idle, walk...)
# waits until the forced one ends; a looping one holds until the next
# qg:play-animation (name="" gives the body its own animations back).

var sprite: Sprite2D = null
var animations: Dictionary = {}   # name -> {frames: [..], fps: f, loop: false when it plays once}
var current: String = ""
var locked := false               # a qg:play-animation is playing
var ends: Array = []              # qg:on-animation-end: [{name, handler}]
var caller: Object = null         # where the handlers are: the scene, or P for a prefab's
var _ticks: float = 0.0
var _index: int = 0
var _done := false                # a one-shot has ended: it stays on its last frame


func setup(sprite_: Sprite2D, animations_: Dictionary) -> void:
	sprite = sprite_
	animations = animations_


# For the rollback.
func q_save() -> Dictionary:
	return {"a": animations, "c": current, "t": _ticks, "i": _index, "fr": sprite.frame,
		"fh": sprite.flip_h, "fv": sprite.flip_v, "l": locked, "d": _done}


func q_load(d: Dictionary) -> void:
	animations = d["a"]
	current = d["c"]
	_ticks = d["t"]
	_index = d["i"]
	sprite.frame = d["fr"]
	sprite.flip_h = d["fh"]
	sprite.flip_v = d["fv"]
	locked = d.get("l", false)
	_done = d.get("d", false)


func has(name_: String) -> bool:
	return animations.has(name_)


# The body's own choice, each tick: nothing while a qg:play-animation plays.
func play(name_: String) -> void:
	if locked or name_ == current or not animations.has(name_):
		return
	_start(name_)


# qg:play-animation: from its first frame, even if it is the one playing.
func force(name_: String) -> void:
	if name_ == "":
		locked = false
		return
	if not animations.has(name_):
		return
	locked = true
	_start(name_)


func _start(name_: String) -> void:
	current = name_
	_index = 0
	_ticks = 0.0
	_done = false
	sprite.frame = int(animations[current]["frames"][0])


func _physics_process(_delta: float) -> void:
	if current == "" or _done:
		return
	var anim: Dictionary = animations[current]
	var frames: Array = anim["frames"]
	var once: bool = not anim.get("loop", true)
	if frames.size() < 2 and not once:
		return
	_ticks += float(anim.get("fps", 8.0)) / Q.TICK_RATE
	while _ticks >= 1.0:
		_ticks -= 1.0
		if once and _index == frames.size() - 1:
			_done = true
			locked = false
			_ended(current)
			return
		_index = (_index + 1) % frames.size()
		sprite.frame = int(frames[_index])


func _ended(name_: String) -> void:
	var owner_ := get_parent()
	Q.event("animation-end", {"who": Q.who(owner_), "animation": name_})
	if caller == null:
		return
	for h in ends:
		if h["name"] == name_ and caller.has_method(h["handler"]):
			caller.call(h["handler"], owner_, null)
