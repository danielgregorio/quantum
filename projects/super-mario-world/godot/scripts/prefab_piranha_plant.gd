extends Node2D

@export var emerge_height: float = 24.0
@export var wait_time: float = 2.0
@export var emerge_speed: float = 1.5
@export var safe_distance: float = 32.0

var _emerged: bool = false
var _emerging: bool = false
var _retracting: bool = false
var _timer: float = 0.0
var _base_y: float = 0.0
var _current_offset: float = 0.0
var _player_near: bool = false

var _anim_timer: float = 0.0
var _anim_frames: Array = [0, 1]
var _anim_idx: int = 0
var _anim_speed: float = 0.20

func _ready():
	_base_y = position.y

func _process(delta: float):
	# Check player proximity (safe zone)
	_check_player_proximity()

	# Timer-based emerge/retract cycle
	_timer += delta

	if not _emerged and not _emerging:
		# Waiting to emerge
		if _timer >= wait_time and not _player_near:
			_emerging = true
			_timer = 0.0

	if _emerging:
		_current_offset = min(_current_offset + emerge_speed * delta * 60.0, emerge_height)
		position.y = _base_y - _current_offset
		if _current_offset >= emerge_height:
			_emerged = true
			_emerging = false
			_timer = 0.0

	if _emerged and not _retracting:
		if _timer >= wait_time:
			_retracting = true
			_timer = 0.0

	if _retracting:
		_current_offset = max(_current_offset - emerge_speed * delta * 60.0, 0.0)
		position.y = _base_y - _current_offset
		if _current_offset <= 0.0:
			_emerged = false
			_retracting = false
			_timer = 0.0

	# Animate sprite
	_anim_timer += delta
	if _anim_timer >= _anim_speed:
		_anim_timer = 0.0
		_anim_idx = (_anim_idx + 1) % _anim_frames.size()
		if has_node("Sprite2D"):
			$Sprite2D.frame = _anim_frames[_anim_idx]

func _check_player_proximity():
	_player_near = false
	var players = get_tree().get_nodes_in_group("player")
	if players.size() > 0:
		var dist = abs(players[0].global_position.x - global_position.x)
		_player_near = dist < safe_distance

func die():
	QuantumEventBus.emit_event("enemy-killed", {"other": self})
	queue_free()
