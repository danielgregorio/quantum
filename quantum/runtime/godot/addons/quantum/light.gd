extends PointLight2D
# A qg:light: a soft round glow of radius= pixels, color= and energy=, that
# flickers by flicker= as a flame does. In a scene with ambient= (a
# CanvasModulate), it is what can be seen; with shadows="true", the solid
# tiles stop it (their occluders, made by tilemap.gd). Only seen: the game's
# state never reads it. The flicker follows the game's ticks and where the
# light is, so a replay's frames are the same every time.

const SIZE := 256   # the glow's picture, scaled to the radius

static var _glow: Texture2D = null

var _energy: float = 1.0
var _flicker: float = 0.0
var _phase: float = 0.0


func setup(spec: Dictionary) -> void:
	name = "Light"
	texture = glow()
	texture_scale = float(spec.get("radius", 64.0)) * 2.0 / SIZE
	color = Color(str(spec.get("color", "#ffffff")))
	_energy = float(spec.get("energy", 1.0))
	energy = _energy
	_flicker = float(spec.get("flicker", 0.0))
	shadow_enabled = bool(spec.get("shadows", false))
	shadow_filter = Light2D.SHADOW_FILTER_PCF5
	shadow_filter_smooth = 1.5


static func glow() -> Texture2D:
	if _glow == null:
		var fade := Gradient.new()
		fade.set_color(0, Color(1, 1, 1, 1))
		fade.set_color(1, Color(1, 1, 1, 0))
		fade.add_point(0.5, Color(1, 1, 1, 0.55))
		var picture := GradientTexture2D.new()
		picture.gradient = fade
		picture.fill = GradientTexture2D.FILL_RADIAL
		picture.fill_from = Vector2(0.5, 0.5)
		picture.fill_to = Vector2(0.5, 0.0)
		picture.width = SIZE
		picture.height = SIZE
		_glow = picture
	return _glow


func _ready() -> void:
	_phase = fmod(global_position.x * 0.137 + global_position.y * 0.071, TAU)
	set_physics_process(_flicker > 0.0)


func _physics_process(_delta: float) -> void:
	var t := float(Engine.get_physics_frames())
	var wave := 0.6 * sin(t * 0.21 + _phase) + 0.4 * sin(t * 0.53 + _phase * 2.0)   # -1 to 1
	energy = _energy * (1.0 - _flicker * 0.5 * (1.0 - wave))
