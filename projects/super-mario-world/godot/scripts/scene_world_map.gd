extends Node2D

# Map data
var map_nodes: Dictionary = {"start": {"x": 32.0, "y": 180.0, "scene": "", "locked": false}, "yoshi-island-1": {"x": 80.0, "y": 180.0, "scene": "yoshi-island-1", "locked": false}, "yoshi-island-2": {"x": 128.0, "y": 160.0, "scene": "yoshi-island-2", "locked": true}, "castle-1": {"x": 200.0, "y": 140.0, "scene": "castle-1", "locked": true}}

var map_paths: Array = [{"from": "start", "to": "yoshi-island-1", "unlock": ""}, {"from": "yoshi-island-1", "to": "yoshi-island-2", "unlock": "yoshi-island-1-cleared"}, {"from": "yoshi-island-2", "to": "castle-1", "unlock": "yoshi-island-2-cleared"}]

var current_node: String = "start"
var _mario_sprite: Sprite2D
var _moving: bool = false

func _ready():
	SceneManager.current_scene_name = "world-map"
	QuantumBridge.register_sprite("map-bg", $"map-bg")
	QuantumBridge.register_sprite("mario", $mario)

	_mario_sprite = $Mario if has_node("Mario") else null
	if _mario_sprite and map_nodes.has(current_node):
		var node_info = map_nodes[current_node]
		_mario_sprite.position = Vector2(node_info["x"], node_info["y"])

func _input(event: InputEvent):
	if _moving:
		return
	if event.is_action_pressed("ui_accept"):
		_enter_node()
	elif event.is_action_pressed("ui_right"):
		_try_move("right")
	elif event.is_action_pressed("ui_left"):
		_try_move("left")
	elif event.is_action_pressed("ui_up"):
		_try_move("up")
	elif event.is_action_pressed("ui_down"):
		_try_move("down")

func _enter_node():
	var node_info = map_nodes.get(current_node, {})
	var scene_name = node_info.get("scene", "")
	if scene_name != "" and not node_info.get("locked", false):
		SceneManager.transition_to(scene_name, "iris-in", 0.5)

func _try_move(direction: String):
	var neighbors = _get_neighbors(current_node)
	var best_node = ""
	var best_dist = INF
	var current_pos = _get_node_pos(current_node)
	for neighbor in neighbors:
		var neighbor_pos = _get_node_pos(neighbor)
		var delta = neighbor_pos - current_pos
		var valid = false
		match direction:
			"right": valid = delta.x > 0 and abs(delta.x) >= abs(delta.y)
			"left": valid = delta.x < 0 and abs(delta.x) >= abs(delta.y)
			"up": valid = delta.y < 0 and abs(delta.y) >= abs(delta.x)
			"down": valid = delta.y > 0 and abs(delta.y) >= abs(delta.x)
		if valid:
			var dist = delta.length()
			if dist < best_dist:
				best_dist = dist
				best_node = neighbor
	if best_node != "":
		_move_to(best_node)

func _move_to(target_node: String):
	_moving = true
	var target_pos = _get_node_pos(target_node)
	if _mario_sprite:
		var tween = create_tween()
		tween.tween_property(_mario_sprite, "position", target_pos, 0.2)
		await tween.finished
	current_node = target_node
	_moving = false

func _get_neighbors(node_id: String):
	var neighbors = []
	for path in map_paths:
		var unlocked = true
		if path.has("unlock") and path["unlock"] != "":
			unlocked = SceneManager.get_state(path["unlock"], false)
		if not unlocked:
			continue
		if path["from"] == node_id:
			neighbors.append(path["to"])
		elif path["to"] == node_id:
			neighbors.append(path["from"])
	return neighbors

func _get_node_pos(node_id: String):
	if map_nodes.has(node_id):
		var info = map_nodes[node_id]
		return Vector2(info["x"], info["y"])
	return Vector2.ZERO
