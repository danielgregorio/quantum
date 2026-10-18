extends Node
# The play protocol in a web build: the browser bridge (PLAN_PLAY_PROTOCOL.md).
# A page, or Playwright driving it (quantum/runtime/web_play.py), reads what
# the game shows and presses its actions, on the exported game itself:
#
#   window.quantumPlay.observe()   then window.quantumObservation: a JSON
#                                  string, the observation of the play
#                                  protocol (tick, scene, state, screen,
#                                  music, and the events since the last one)
#   window.quantumPlay.press("right"), .release("right")
#   window.quantumPlay.trace(true) the runtime records its events (Q.event)
#
# The game runs at its own speed: this is the real-time mode, where `tick`
# is the physics frames since the game started. A JavaScript callback cannot
# hand back a value, so observe() leaves its answer in a window property.

var _callbacks: Array = []   # held, or JavaScript would call freed callables
var _first_frame: int = 0


func _ready() -> void:
	name = "WebPlay"
	process_physics_priority = -2000   # before Q samples the input, so a press counts on this tick
	_first_frame = Engine.get_physics_frames()
	var window = JavaScriptBridge.get_interface("window")
	if window == null:
		return
	var api = JavaScriptBridge.create_object("Object")
	for method in ["observe", "press", "release", "trace"]:
		var cb = JavaScriptBridge.create_callback(Callable(self, "_js_" + method))
		_callbacks.append(cb)
		api[method] = cb
	window.quantumPlay = api


func _physics_process(_delta: float) -> void:
	var q := get_node_or_null("/root/Q")
	if q != null:
		q.event_tick = tick()


func tick() -> int:
	return Engine.get_physics_frames() - _first_frame


func _js_observe(_args) -> void:
	var window = JavaScriptBridge.get_interface("window")
	window.quantumObservation = JSON.stringify(observation())


func _js_press(args) -> void:
	if args.size() > 0 and InputMap.has_action(str(args[0])):
		Input.action_press(str(args[0]))


func _js_release(args) -> void:
	if args.size() > 0 and InputMap.has_action(str(args[0])):
		Input.action_release(str(args[0]))


func _js_trace(args) -> void:
	var q := get_node_or_null("/root/Q")
	if q != null:
		q.tracing = args.size() == 0 or bool(args[0])
		q.events.clear()


# What a player knows by looking, as godot_play.gd's observation: the scene
# and its state, the screen's views, what is heard, the actions held; and
# the events since the last observation.
func observation() -> Dictionary:
	var obs := {"tick": tick(), "scene": "", "state": {}, "screen": [], "held": [], "controls": []}
	var game := get_parent()
	for n in _walk(game):
		if n.has_method("quantum_state") and n.has_method("q_pause"):
			obs["scene"] = String(n.name)
			obs["state"] = n.quantum_state()
		if n.has_method("quantum_view"):
			var v: Dictionary = n.quantum_view()
			if not v.is_empty():
				obs["screen"].append(v)
	for a in InputMap.get_actions():
		var name_ := String(a)
		if name_.begins_with("ui_") or name_.begins_with("raw_"):
			continue
		obs["controls"].append(name_)
		if Input.is_action_pressed(name_):
			obs["held"].append(name_)
	var q := get_node_or_null("/root/Q")
	if q != null:
		if "music_playing" in q and q.music_playing != "":
			obs["music"] = q.music_playing
		if q.tracing:
			obs["events"] = q.events.duplicate()
			q.events.clear()
	return obs


func _walk(n: Node) -> Array:
	var out := [n]
	for c in n.get_children():
		out += _walk(c)
	return out
