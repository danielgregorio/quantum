extends RefCounted
# qg:particles: named effects made from a preset and a few overrides, never
# the 68 knobs of CPUParticles2D. qg:emit plays one once where a thing is;
# qg:emitter keeps one going in the scene (rain over it, a fire on a spot).
# They are only seen: nothing in the game's state depends on them, so a
# replay and every peer of a networked game play the same game whatever
# the particles do.
#
#   puff      a soft ring of dots, once (a landing, a pop)
#   sparks    fast bright bits that fall (a hit, a coin)
#   smoke     slow grey that rises and fades
#   dust      a low spray to the sides (a step, a skid)
#   fire      flickering orange that rises (keep it going: qg:emitter)
#   rain      lines that fall across the emitter's width
#   snow      flakes that drift down across the width
#   confetti  colours that burst up and tumble down (a win)
#   stars     twinkles that grow and fade where they are (a pick-up)

const PRESETS := {
	"puff": {"amount": 12, "lifetime": 0.45, "one_shot": true, "explosiveness": 1.0, "spread": 180.0,
			"speed": [30.0, 70.0], "gravity": [0.0, 0.0], "size": [2.0, 3.0], "color": "#ffffff", "fade": true},
	"sparks": {"amount": 16, "lifetime": 0.5, "one_shot": true, "explosiveness": 1.0, "spread": 180.0,
			"speed": [80.0, 160.0], "gravity": [0.0, 300.0], "size": [1.0, 2.0], "color": "#ffd34d", "fade": true},
	"smoke": {"amount": 14, "lifetime": 1.2, "one_shot": true, "explosiveness": 0.6, "spread": 30.0,
			"direction": [0.0, -1.0], "speed": [15.0, 35.0], "gravity": [0.0, -20.0], "size": [3.0, 6.0],
			"color": "#8a8a8a", "fade": true, "grow": true},
	"dust": {"amount": 10, "lifetime": 0.4, "one_shot": true, "explosiveness": 1.0, "spread": 40.0,
			"direction": [0.0, -1.0], "speed": [20.0, 50.0], "gravity": [0.0, 120.0], "size": [1.5, 3.0],
			"color": "#c8b48c", "fade": true},
	"fire": {"amount": 40, "lifetime": 0.8, "one_shot": false, "explosiveness": 0.0, "spread": 25.0,
			"direction": [0.0, -1.0], "speed": [25.0, 55.0], "gravity": [0.0, -40.0], "size": [3.0, 6.0],
			"color": "#ff8a2a", "fade": true, "shrink": true},
	"rain": {"amount": 60, "lifetime": 0.8, "one_shot": false, "explosiveness": 0.0, "spread": 2.0,
			"direction": [0.1, 1.0], "speed": [260.0, 320.0], "gravity": [0.0, 0.0], "size": [1.0, 1.0],
			"color": "#9fc4ff", "streak": true, "width": true},
	"snow": {"amount": 40, "lifetime": 3.0, "one_shot": false, "explosiveness": 0.0, "spread": 20.0,
			"direction": [0.0, 1.0], "speed": [15.0, 30.0], "gravity": [0.0, 5.0], "size": [1.5, 2.5],
			"color": "#ffffff", "width": true},
	"confetti": {"amount": 40, "lifetime": 1.4, "one_shot": true, "explosiveness": 1.0, "spread": 50.0,
			"direction": [0.0, -1.0], "speed": [120.0, 220.0], "gravity": [0.0, 260.0], "size": [2.0, 3.0],
			"color": "#ffffff", "rainbow": true, "spin": true},
	"stars": {"amount": 8, "lifetime": 0.6, "one_shot": true, "explosiveness": 0.8, "spread": 180.0,
			"speed": [15.0, 40.0], "gravity": [0.0, 0.0], "size": [2.0, 4.0], "color": "#fff6a8",
			"fade": true, "grow": true},
}


# A CPUParticles2D for the declaration (preset, with its overrides). `width`:
# for rain and snow, how wide a band they fall across (pixels).
static func make(spec: Dictionary, width: float = 0.0) -> CPUParticles2D:
	var p: Dictionary = PRESETS[spec["preset"]].duplicate()
	for k in ["amount", "lifetime", "color"]:
		if spec.get(k) != null:
			p[k] = spec[k]
	if spec.get("speed") != null:
		var s := float(spec["speed"])
		p["speed"] = [s * 0.7, s * 1.3]
	if spec.get("size") != null:
		var z := float(spec["size"])
		p["size"] = [z * 0.7, z * 1.3]
	var e := CPUParticles2D.new()
	e.amount = maxi(1, int(p["amount"]))
	e.lifetime = float(p["lifetime"])
	e.one_shot = bool(p["one_shot"])
	e.explosiveness = float(p["explosiveness"])
	e.spread = float(p["spread"])
	var d: Array = p.get("direction", [0.0, 0.0])
	e.direction = Vector2(d[0], d[1])
	e.initial_velocity_min = float(p["speed"][0])
	e.initial_velocity_max = float(p["speed"][1])
	e.gravity = Vector2(p["gravity"][0], p["gravity"][1])
	e.scale_amount_min = float(p["size"][0])
	e.scale_amount_max = float(p["size"][1])
	e.color = Color(str(p["color"]))
	if p.get("fade", false) or p.get("rainbow", false):
		var ramp := Gradient.new()
		ramp.set_color(0, Color(e.color, 1.0))
		ramp.set_color(1, Color(e.color, 0.0))
		e.color_ramp = ramp
	if p.get("rainbow", false):
		var hues := Gradient.new()
		hues.set_color(0, Color.from_hsv(0.0, 0.7, 1.0))
		hues.set_color(1, Color.from_hsv(0.99, 0.7, 1.0))
		hues.add_point(0.33, Color.from_hsv(0.33, 0.7, 1.0))
		hues.add_point(0.66, Color.from_hsv(0.66, 0.7, 1.0))
		e.color_initial_ramp = hues
	if p.get("grow", false) or p.get("shrink", false):
		var curve := Curve.new()
		curve.add_point(Vector2(0.0, 0.3 if p.get("grow", false) else 1.0))
		curve.add_point(Vector2(1.0, 1.0 if p.get("grow", false) else 0.1))
		e.scale_amount_curve = curve
	if p.get("spin", false):
		e.angular_velocity_min = -360.0
		e.angular_velocity_max = 360.0
	if p.get("streak", false):
		e.scale_amount_min = 1.0
		e.scale_amount_max = 1.0
		var line := Image.create(1, 6, false, Image.FORMAT_RGBA8)
		line.fill(Color.WHITE)
		e.texture = ImageTexture.create_from_image(line)   # a drop is a short line, not a dot
	if p.get("width", false) and width > 0.0:
		e.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
		e.emission_rect_extents = Vector2(width / 2.0, 1.0)
	e.emitting = true
	return e
