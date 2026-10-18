extends Node
# The root of every Quantum game: reads game.json, registers the inputs and
# builds the first scene. The scene tree it builds is the whole game; the
# compiled scripts (scripts/*.gd) only hold the game's logic.

const SceneBuilder := preload("res://addons/quantum/scene_builder.gd")
const Lockstep := preload("res://addons/quantum/lockstep.gd")
const Rollback := preload("res://addons/quantum/rollback.gd")
const WebPlay := preload("res://addons/quantum/web_play.gd")
const Fade := preload("res://addons/quantum/fade.gd")

var spec: Dictionary = {}
var current_scene: Node = null
var lockstep: Node = null


func _ready() -> void:
	var f := FileAccess.open("res://game.json", FileAccess.READ)
	if f == null:
		push_error("quantum: game.json is missing")
		return
	spec = JSON.parse_string(f.get_as_text())
	_register_inputs(spec.get("inputs", {}))
	if OS.has_feature("web"):
		add_child(WebPlay.new())   # window.quantumPlay: an agent plays the exported game (web_play.py)
	_languages(spec.get("languages", {}))
	# qg:multiplayer, with --q-host=PORT or --q-join=HOST:PORT: the game waits
	# for every player, and the local keys only reach it through the lockstep
	var host := ""
	var port := -1
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--q-host="):
			port = int(a.substr(9))
		elif a.begins_with("--q-join="):
			var address := a.substr(9)
			if address.contains("://"):   # a relay's URL: wss://host/game/room
				host = address
				port = 0
			else:
				var parts: PackedStringArray = address.split(":")
				host = parts[0]
				port = int(parts[1]) if parts.size() > 1 else -1
		elif a.begins_with("--q-relay="):
			port = int(a.substr(10))
			relay_override = true
		elif a.begins_with("--q-port="):
			port_override = int(a.substr(9))
		elif a.begins_with("--q-transport="):
			transport_override = a.substr(14)
		elif a.begins_with("--q-latency="):
			latency_override = int(a.substr(12))
	if spec.has("multiplayer") and (port > 0 or (port == 0 and host != "")):
		_start_network(host, port).from_command_line = true
		return
	go_to_scene(spec["initial"])


# qg:language: --q-lang=pt, else the web page's ?lang=pt, else the system's
# language, when the game has it; else the game's own texts.
func _languages(langs: Dictionary) -> void:
	var wanted := ""
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--q-lang="):
			wanted = a.substr(9)
	if wanted == "":
		wanted = str(Q.url_param("lang", ""))
	if wanted == "":
		wanted = OS.get_locale()
	for code in langs.keys():
		var t := Translation.new()
		t.locale = code
		var phrases: Dictionary = langs[code].get("phrases", {})
		for text in phrases.keys():
			t.add_message(text, phrases[text])
		TranslationServer.add_translation(t)
	Q.languages = langs.keys()
	if langs.has(wanted):
		Q.lang = wanted
	elif langs.has(wanted.split("_")[0]):
		Q.lang = wanted.split("_")[0]
	else:
		Q.lang = ""
	TranslationServer.set_locale(Q.lang if Q.lang != "" else "en")


# Overrides for tests (several games on one machine): --q-port=N, --q-transport=websocket.
var port_override: int = -1
var transport_override: String = ""
var latency_override: int = 0
var relay_override: bool = false   # --q-relay=PORT: quantum relay's seatless host


func _start_network(host: String, port: int) -> Node:
	if lockstep != null:
		lockstep.leave()
		remove_child(lockstep)
		lockstep.queue_free()
	var mp: Dictionary = spec["multiplayer"].duplicate()
	if transport_override != "":
		mp["transport"] = transport_override
	lockstep = Rollback.new() if int(mp.get("rollback", 0)) > 0 else Lockstep.new()
	lockstep.latency_ms = latency_override
	lockstep.relay = relay_override
	if relay_override:
		mp["transport"] = "websocket"   # browsers reach a relay
	add_child(lockstep)
	lockstep.setup(mp, self, host, port_override if port_override > 0 else port)
	return lockstep


# qg:host / qg:join / qg:leave, from a scene (Q.net_host...).
func net_host(port: int) -> void:
	_start_network("", port)


func net_join(address: String) -> void:
	address = address.strip_edges()
	if address.contains("://"):   # a relay's URL: wss://host/game/room
		_start_network(address, 0)
		return
	var parts := address.split(":")
	var port := int(parts[1]) if parts.size() > 1 else 7777
	_start_network(parts[0], port)


func net_leave() -> void:
	if lockstep != null:
		lockstep.leave()
		remove_child(lockstep)
		lockstep.queue_free()
		lockstep = null


func net_status() -> String:
	return lockstep.status if lockstep != null else "offline"


func net_players() -> int:
	return lockstep.connected_players if lockstep != null else 0


func net_player() -> int:
	return lockstep.player if lockstep != null else 0


func _q_lockstep_ready() -> void:
	go_to_scene(str(spec["multiplayer"].get("start", spec["initial"])))


func _register_inputs(inputs: Dictionary) -> void:
	for action in inputs.keys():
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for key in inputs[action]:
			if key is Dictionary and key.has("joy_button"):
				var jb := InputEventJoypadButton.new()
				jb.button_index = int(key["joy_button"])
				jb.device = int(key.get("device", 0))
				InputMap.action_add_event(action, jb)
			elif key is Dictionary and key.has("mouse_button"):
				var mb := InputEventMouseButton.new()
				mb.button_index = int(key["mouse_button"])
				InputMap.action_add_event(action, mb)
			elif key is Dictionary and key.has("joy_axis"):
				var ja := InputEventJoypadMotion.new()
				ja.axis = int(key["joy_axis"])
				ja.axis_value = float(key["value"])
				ja.device = int(key.get("device", 0))
				InputMap.action_add_event(action, ja)
			else:
				var ev := InputEventKey.new()
				ev.physical_keycode = OS.find_keycode_from_string(str(key))
				InputMap.action_add_event(action, ev)


func go_to_scene(scene_name: String, fade: float = 0.0) -> void:
	if not spec["scenes"].has(scene_name):
		push_error("quantum: no scene named " + scene_name)
		return
	if current_scene != null:
		if current_scene.name == scene_name and current_scene.is_queued_for_deletion():
			return
		remove_child(current_scene)
		current_scene.queue_free()
		current_scene = null
	var scene_spec: Dictionary = spec["scenes"][scene_name]
	current_scene = SceneBuilder.build(spec, scene_spec)
	current_scene.name = scene_name
	add_child(current_scene)
	Q.web_report("quantumScene", scene_name)
	Q.event("scene", {"name": scene_name})
	Q.music(scene_spec.get("music"))
	if fade > 0.0:
		_fade_in(fade)
	if G.has_method("_q_save"):
		G._q_save()
	if scene_spec.get("save", false):
		Q.save_game(current_scene)


func _fade_in(seconds: float) -> void:
	var old := get_node_or_null("Fade")
	if old != null:
		remove_child(old)
		old.queue_free()
	var fade := Fade.new()
	add_child(fade)
	fade.start(seconds)


func _exit_tree() -> void:
	if G.has_method("_q_save"):
		G._q_save()
	SceneBuilder.forget_textures()   # the static cache holds loaded resources: let them go with the game
