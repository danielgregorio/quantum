extends CharacterBody2D
# A character made of parts (qg:character controller="behavior" holding a
# qg:behavior): each part is a small rule, and the body is what they add up
# to. A platformer is gravity, walk and jump; a top-down walker is walk on
# both axes; a flapping bird is gravity and a jump that works in the air; a
# ship that comes back round the screen is walk and wrap.
#
#   gravity      pulls down: strength= pixels/s², max-fall= the speed it falls at most
#   walk         left/right (and up/down with axis="both") set the speed; accel= eases it
#   jump         a press on the floor (or in the air, air= times) leaps height= pixels;
#                let go while rising, the leap is cut short (variable=)
#   keep-inside  the scene's edges stop it
#   wrap         past an edge of the scene, it comes back on the other side
#   face         its picture turns the way it goes (by="velocity") or is pushed (by="input")
#
# Each tick has the same order, whatever order the parts are written in:
# walk and jump read the keys, gravity pulls, the body moves, then
# keep-inside, wrap and face. It is the platformer controller's order, so
# gravity, walk and jump with its numbers make the same platformer, to the
# pixel.
#
# qg:velocity (an action) sets its speed from the game's rules, and
# `me.vx`, `me.vy`, `me.on_floor` read it, so a rule no part covers (a dash,
# a knock-back, a wind) is written in the game, not in the runtime.
#
# Touches fire qg:on-collision as for the platformer: side="top" when it
# lands on the thing, "bottom" when it hits it from below; a handler with a
# cooldown fires again while the thing is still there.

const Animator := preload("res://addons/quantum/animator.gd")
const TileSense := preload("res://addons/quantum/tile_sense.gd")
const ICE_ACCEL := 200.0   # on ice the walk speed comes and goes this slowly, pixels/s²

var parts: Dictionary = {}   # part name -> its attributes
var hitbox_size: Vector2 = Vector2(14, 14)
var spawn_point: Vector2 = Vector2.ZERO
var animator: Node = null
var state: String = ""
var player: int = 1
var facing: int = 1

var vx: float:
	get:
		return velocity.x
var vy: float:
	get:
		return velocity.y
var on_floor: bool:
	get:
		return is_on_floor()

var _states: Dictionary = {}
var _base_animations: Dictionary = {}
var _base_frame: int = 0
var _handlers: Array = []
var _cooldowns: Dictionary = {}   # handler name -> tick it may fire again
var _scene: Node = null
var _ticks: int = 0
var _on_fall: String = ""
var _fell: bool = false
var _coyote: int = 0              # ticks a jump still works after leaving the floor
var _airs: int = 0                # jumps left in the air
var _jump_speed: float = 0.0
var _jump_was_held: bool = false
var _leaping: bool = false        # rising from a jump or a bounce: letting go cuts it
var _moving: Vector2 = Vector2.ZERO   # the velocity of the last move: the side of a touch
var _tiles := TileSense.new()   # the kinds of the tiles about it (qg:tile kind=), its qg:on-tile handlers
var _about := {"in": "", "under": "", "touching": []}
var _climbing := false


func setup(spec: Dictionary) -> void:
	player = int(spec.get("player", 1))
	for p in spec.get("behavior", []):
		parts[p["part"]] = p
	hitbox_size = Vector2(spec["hitbox"][0], spec["hitbox"][1])
	if parts.has("jump"):
		var j: Dictionary = parts["jump"]
		_jump_speed = float(j["speed"]) if j.get("speed") != null else _speed_for_height(float(j["height"]))
	# with gravity it stands on floors; without, it floats (a top-down walker, a ship)
	if parts.has("gravity"):
		floor_snap_length = 4.0
	else:
		motion_mode = CharacterBody2D.MOTION_MODE_FLOATING
	spawn_point = position


func wire(sensor: Area2D, spec: Dictionary, scene: Node, sprite: Sprite2D) -> void:
	_handlers = spec.get("on_collision", [])
	_tiles.setup(spec, scene)
	_on_fall = str(spec.get("on_fall", "")) if spec.get("on_fall") != null else ""
	_scene = scene
	sensor.area_entered.connect(_on_area_entered)
	_base_animations = spec.get("animations", {})
	_base_frame = int(spec.get("frame", 0))
	_states = spec.get("states", {})
	animator = Animator.new()
	animator.name = "Animator"
	animator.setup(sprite, _base_animations)
	add_child(animator)
	animator.play("idle")
	if spec.get("initial_state") != null:
		become(str(spec["initial_state"]))


func quantum_node_state() -> Dictionary:
	return {"state": state} if state != "" else {}


func respawn() -> void:
	position = spawn_point
	velocity = Vector2.ZERO
	_fell = false


func set_checkpoint(at: Vector2) -> void:
	spawn_point = Vector2(at.x, at.y - 2.0)


func bounce(height: float) -> void:
	velocity.y = -_speed_for_height(height)
	_coyote = 0
	_leaping = true   # as a jump: held, the bounce goes higher


# qg:velocity: the speed the game's rules give it (null keeps that axis as it is).
func set_velocity_from_rules(x, y) -> void:
	if x != null:
		velocity.x = float(x)
	if y != null:
		velocity.y = float(y)
		_leaping = false   # thrown, not leaping: letting go of jump does not cut it


# One of the qg:states: its hitbox, its frame, its animations (the
# character's own where the state has none).
func become(name_: String) -> void:
	if not _states.has(name_) or name_ == state:
		return
	state = name_
	var st: Dictionary = _states[name_]
	var old_h := hitbox_size.y
	hitbox_size = Vector2(st["hitbox"][0], st["hitbox"][1])
	# Deferred: a state change comes from a collision handler, while
	# physics refuses shape changes.
	var shape := get_node_or_null("Shape")
	if shape != null:
		shape.shape.set_deferred("size", hitbox_size)
	var sensor_shape := get_node_or_null("Sensor/Shape")
	if sensor_shape != null:
		sensor_shape.shape.set_deferred("size", hitbox_size + Vector2(4, 4))
	if parts.has("gravity"):
		position.y -= (hitbox_size.y - old_h) / 2.0   # the feet stay where they were
	var sprite: Sprite2D = get_node_or_null("Sprite")
	if sprite != null:
		sprite.frame = int(st.get("frame", _base_frame))
	if animator != null:
		var anims: Dictionary = _base_animations.duplicate()
		for k in st.get("animations", {}).keys():
			anims[k] = st["animations"][k]
		animator.animations = anims
		animator.current = ""


func _physics_process(delta: float) -> void:
	_ticks += 1
	_about = _tiles.sense(self, hitbox_size, _ticks)
	if parts.has("gravity") and _ladder():
		_moving = velocity
		move_and_slide()
		_animate()
		_still_touching()
		return
	if parts.has("walk"):
		_walk(parts["walk"], delta)
	if parts.has("jump"):
		_jump(parts["jump"])
	if parts.has("gravity"):
		_gravity(parts["gravity"], delta)
	_moving = velocity
	move_and_slide()
	if parts.has("keep-inside"):
		_keep_inside()
	if parts.has("wrap"):
		_wrap()
	if parts.has("face"):
		_face(parts["face"])
	_animate()
	_still_touching()
	if _on_fall != "" and not _fell and _scene != null and _scene.has_method("q_fall_line"):
		if position.y > _scene.q_fall_line():
			_fell = true
			_scene.call(_on_fall, self, null)


func _walk(p: Dictionary, delta: float) -> void:
	var both: bool = p["axis"] == "both"
	var dir := Vector2(Q.strength(_a("right")) - Q.strength(_a("left")), 0.0)
	if both:
		dir.y = Q.strength(_a("down")) - Q.strength(_a("up"))
		if dir.length() > 1.0:
			dir = dir.normalized()   # no faster on a diagonal
	var target := dir * float(p["speed"]) * (0.6 if _about["in"] == "water" else 1.0)
	var accel := float(p["accel"])
	if _about["under"] == "ice" and is_on_floor() or not parts.has("gravity") and _about["in"] == "ice":
		accel = ICE_ACCEL if accel <= 0.0 else minf(accel, ICE_ACCEL)   # sliding
	if accel > 0.0:
		velocity.x = move_toward(velocity.x, target.x, accel * delta)
		if both:
			velocity.y = move_toward(velocity.y, target.y, accel * delta)
	else:
		velocity.x = target.x
		if both:
			velocity.y = target.y


func _jump(p: Dictionary) -> void:
	if is_on_floor():
		_coyote = maxi(int(p["coyote"]), 1)   # standing, a jump works whatever coyote= says
		_airs = int(p["air"])
	elif _coyote > 0:
		_coyote -= 1
	if not Q.tapped(_a(str(p["action"]))):
		return
	if _about["in"] == "water":
		velocity.y = -_jump_speed * 0.65   # in water a jump is a stroke, as often as it is pressed
		return
	if _coyote > 0:
		_coyote = 0
	elif _airs > 0:
		_airs -= 1
	else:
		return
	velocity.y = -_jump_speed
	_leaping = true
	if p.get("sound") != null:
		Q.play(str(p["sound"]))


# Gravity, and a leap let go while rising: three times the pull (cut=0), or
# the rise multiplied by cut= once.
func _gravity(p: Dictionary, delta: float) -> void:
	var g := float(p["strength"])
	var fall_max := float(p["max_fall"])
	if velocity.y >= 0.0:
		_leaping = false
	if _about["in"] == "water":   # water holds it up: it sinks slowly
		g *= 0.25
		fall_max *= 0.35
	elif parts.has("jump"):
		var j: Dictionary = parts["jump"]
		var holding := Q.held(_a(str(j["action"])))
		if bool(j["variable"]) and _leaping and not holding:
			if float(j["cut"]) <= 0.0:
				g *= 3.0
			elif _jump_was_held:
				velocity.y *= float(j["cut"])
		_jump_was_held = holding
	velocity.y = minf(velocity.y + g * delta, fall_max)


# A body with gravity on a ladder: up or down takes hold of it, left and right
# sidle, no gravity; at its top it stops; the jump part's action lets go with a
# jump. True while it climbs (the tick's velocity is set).
func _ladder() -> bool:
	var climb := Q.strength(_a("down")) - Q.strength(_a("up"))
	if not (_about["in"] == "ladder" or (_about["under"] == "ladder" and climb > 0.0)):
		_climbing = false
	elif climb != 0.0:
		_climbing = true
	if not _climbing:
		return false
	var speed := float(parts["walk"]["speed"]) if parts.has("walk") else 60.0
	var dir := Q.strength(_a("right")) - Q.strength(_a("left"))
	velocity = Vector2(dir * speed * 0.5, climb * speed * 0.6)
	var map := _scene.get_node_or_null("Tilemap") if _scene != null else null
	if climb < 0.0 and map != null and map.kind_at(position - Vector2(0, 2)) != "ladder":
		velocity.y = 0.0
	if parts.has("jump") and Q.tapped(_a(str(parts["jump"]["action"]))):
		_climbing = false
		velocity.y = -_jump_speed
		_leaping = true
	_coyote = 0
	return true


# The take-off speed that peaks at `height` pixels under the gravity part:
# gravity pulls before the move, so it is g*dt/2 + sqrt((g*dt/2)^2 + 2*g*h).
func _speed_for_height(height: float) -> float:
	var g := float(parts["gravity"]["strength"]) if parts.has("gravity") else 900.0
	var half_step := g / (2.0 * Q.TICK_RATE)
	return half_step + sqrt(half_step * half_step + 2.0 * g * height)


func _scene_size() -> Vector2:
	if _scene != null and "q_spec" in _scene:
		return Vector2(float(_scene.q_spec.get("width", 256)), float(_scene.q_spec.get("height", 224)))
	return Vector2(256, 224)


func _keep_inside() -> void:
	var size := _scene_size()
	var half := hitbox_size / 2.0
	var x := clampf(position.x, half.x, size.x - half.x)
	var y := clampf(position.y, half.y, size.y - half.y)
	if x != position.x:
		velocity.x = 0.0
	if y != position.y:
		velocity.y = 0.0
	position = Vector2(x, y)


func _wrap() -> void:
	var size := _scene_size()
	position = Vector2(fposmod(position.x, size.x), fposmod(position.y, size.y))


func _face(p: Dictionary) -> void:
	var dx := velocity.x
	if p["by"] == "input":
		dx = Q.strength(_a("right")) - Q.strength(_a("left"))
	if not is_zero_approx(dx):
		facing = 1 if dx > 0.0 else -1
	var sprite := get_node_or_null("Sprite")
	if sprite != null:
		sprite.flip_h = facing < 0


func _animate() -> void:
	if animator == null:
		return
	var grounded := not parts.has("gravity") or is_on_floor()
	if not grounded and velocity.y > 0.0 and animator.has("fall"):
		animator.play("fall")
	elif not grounded and animator.has("jump"):
		animator.play("jump")
	elif velocity.length() > 0.1 and animator.has("walk"):
		animator.play("walk")
	elif animator.has("idle"):
		animator.play("idle")


func _on_area_entered(area: Area2D) -> void:
	if not area.has_method("quantum_tag"):
		return
	var tag: String = area.quantum_tag()
	var other: Node = area.quantum_owner() if area.has_method("quantum_owner") else area
	Q.touched(self, other)
	var on_top := _is_on_top_of(other)
	var from_below := _is_below(other)
	var matched := false
	for h in _handlers:
		var side: String = h.get("side", "any")
		if h["with"] == tag and ((side == "top" and on_top) or (side == "bottom" and from_below)):
			if _fire(h, other):
				matched = true
	if matched:
		return
	for h in _handlers:
		if h["with"] == tag and h.get("side", "any") == "any":
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
			if h["with"] == tag and h.get("side", "any") == "any" and int(h.get("cooldown", 0)) > 0 \
					and _cooldowns.get(h["handler"], -1) <= _ticks:
				_fire(h, other)


func _fire(h: Dictionary, other: Node) -> bool:
	var name_: String = h["handler"]
	var cooldown := int(h.get("cooldown", 0))
	if cooldown > 0 and _cooldowns.get(name_, -1) > _ticks:
		return false
	if cooldown > 0:
		_cooldowns[name_] = _ticks + cooldown
	if _scene.has_method(name_):
		Q.event("touch", {"who": String(name), "with": Q.who(other)})
		_scene.call(name_, self, other)
	return true


# Hitting it from below: rising, with the head below its middle.
func _is_below(other: Node) -> bool:
	if not (other is Node2D):
		return false
	var head := global_position.y - hitbox_size.y / 2.0
	return _moving.y < 0.0 and head >= (other as Node2D).global_position.y - 2.0


# Landing on it: falling, with the feet above its middle.
func _is_on_top_of(other: Node) -> bool:
	if not (other is Node2D):
		return false
	var feet := global_position.y + hitbox_size.y / 2.0
	return _moving.y > 0.0 and feet <= (other as Node2D).global_position.y + 2.0


# The input action of this player: "up" for player 1, "p2_up" for player 2.
func _a(action: String) -> String:
	return action if player == 1 else "p%d_%s" % [player, action]
