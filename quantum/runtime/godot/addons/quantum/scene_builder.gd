extends RefCounted
# Builds a scene's node tree from its entry in game.json.
#
# Textures come through Q.texture: Godot's import in an exported game, the
# image file itself in a project never imported (a headless replay).

const QuantumScene := preload("res://addons/quantum/quantum_scene.gd")
const PlatformerBody := preload("res://addons/quantum/platformer_body.gd")
const Item := preload("res://addons/quantum/item.gd")
const Thing := preload("res://addons/quantum/thing.gd")
const Block := preload("res://addons/quantum/block.gd")
const MapWalker := preload("res://addons/quantum/map_walker.gd")
const TopdownBody := preload("res://addons/quantum/topdown_body.gd")
const Exit := preload("res://addons/quantum/exit.gd")
const ShipBody := preload("res://addons/quantum/ship_body.gd")
const Spawner := preload("res://addons/quantum/spawner.gd")
const Shuttle := preload("res://addons/quantum/shuttle.gd")
const Timer_ := preload("res://addons/quantum/timer.gd")
const Hud := preload("res://addons/quantum/hud.gd")
const Tilemap := preload("res://addons/quantum/tilemap.gd")
const Zone := preload("res://addons/quantum/zone.gd")
const Cursor := preload("res://addons/quantum/cursor.gd")
const FighterBody := preload("res://addons/quantum/fighter_body.gd")
const Menu := preload("res://addons/quantum/menu.gd")
const GridBody := preload("res://addons/quantum/grid_body.gd")
const Dialogue := preload("res://addons/quantum/dialogue.gd")

static var _textures: Dictionary = {}


static func build(game: Dictionary, scene_spec: Dictionary) -> Node2D:
	var scene: Node2D = QuantumScene.new()
	scene.set_script(load(scene_spec["script"]))
	scene.q_spec = scene_spec
	scene.q_game = game
	scene.q_seed = int(scene_spec.get("seed", 0))
	Q.load_sounds(game.get("sounds", {}))

	var bg := ColorRect.new()
	bg.name = "Background"
	bg.color = Color(scene_spec.get("background", "#000000"))
	bg.size = Vector2(16384, 16384)
	bg.position = Vector2(-8192, -8192)
	bg.z_index = -100
	scene.add_child(bg)

	scene.q_on_input = scene_spec.get("on_input", {})
	scene.q_on_select = scene_spec.get("on_select", {})
	Q.apply_gd(scene, scene_spec.get("gd"))
	scene.q_on_death = scene_spec.get("on_death", {})
	var tilemap: Node = null
	var characters: Dictionary = {}
	var exits: Dictionary = {}
	var map_nodes: Dictionary = {}
	var map_paths: Array = scene_spec.get("map_paths", [])
	for node_spec in scene_spec["nodes"]:
		if node_spec["kind"] == "map-node":
			map_nodes[node_spec["name"]] = node_spec
	for p in map_paths:
		var line := Line2D.new()
		line.width = 3.0
		line.default_color = Color(1, 1, 1, 0.6)
		line.add_point(Vector2(map_nodes[p["from"]]["x"], map_nodes[p["from"]]["y"]))
		line.add_point(Vector2(map_nodes[p["to"]]["x"], map_nodes[p["to"]]["y"]))
		scene.add_child(line)
	for node_spec in scene_spec["nodes"]:
		match node_spec["kind"]:
			"map-node":
				var sheet: Dictionary = game["sheets"][node_spec["sheet"]]
				var marker := _sprite(_texture(sheet), sheet["tile"], int(node_spec["frame"]))
				marker.name = node_spec["name"]
				marker.position = Vector2(node_spec["x"], node_spec["y"])
				Q.apply_gd(marker, node_spec.get("gd"))
				scene.add_child(marker)
			"tilemap":
				tilemap = Tilemap.build(node_spec, game["sheets"][node_spec["tileset"]], _texture)
				for layer in tilemap.get_children():
					Q.apply_gd(layer, node_spec.get("gd"))
				scene.add_child(tilemap)
				scene.q_fall_y = tilemap.pixel_size().y + 64.0
			"character":
				if node_spec["controller"] == "map":
					var walker := MapWalker.new()
					var sheet: Dictionary = game["sheets"][node_spec["sheet"]]
					var sprite := _sprite(_texture(sheet), sheet["tile"], int(node_spec["frame"]))
					walker.add_child(sprite)
					walker.setup(node_spec, map_nodes, map_paths, scene, sprite)
					var start: String = ""
					if node_spec.get("at_method") != null:
						start = str(scene.call(node_spec["at_method"]))
					walker.place(start)
					Q.apply_gd(walker, node_spec.get("gd"))
					characters[node_spec["id"]] = walker
					scene.add_child(walker)
				else:
					var body := _character(node_spec, game, scene)
					Q.apply_gd(body, node_spec.get("gd"))
					characters[node_spec["id"]] = body
					scene.add_child(body)
			"instance":
				if node_spec.get("if") != null and not scene.call(node_spec["if"]):
					continue
				var made := instance(game, scene, node_spec["prefab"], Vector2(node_spec["x"], node_spec["y"]))
				if node_spec.get("name") != null:
					made.name = node_spec["name"]
					made.set_meta("q_named", true)
				Q.apply_gd(made, node_spec.get("gd"))
			"timer":
				var timer := Timer_.new()
				timer.setup(node_spec, scene)
				Q.apply_gd(timer, node_spec.get("gd"))
				scene.add_child(timer)
			"spawner":
				var spawner := Spawner.new()
				spawner.setup(node_spec)
				Q.apply_gd(spawner, node_spec.get("gd"))
				scene.add_child(spawner)
			"cursor":
				var cursor := Cursor.new()
				cursor.setup(node_spec, scene)
				if node_spec.get("sheet") != null:
					var sheet: Dictionary = game["sheets"][node_spec["sheet"]]
					cursor.add_child(_sprite(_texture(sheet), sheet["tile"], int(node_spec["frame"])))
				cursor.z_index = 50
				Q.apply_gd(cursor, node_spec.get("gd"))
				scene.add_child(cursor)
				scene.q_cursors.append(cursor)
			"path":
				scene.q_paths[node_spec["name"]] = node_spec["points"]
			"zone":
				var zone := Zone.new()
				zone.setup(node_spec)
				Q.apply_gd(zone, node_spec.get("gd"))
				scene.add_child(zone)
			"sprite":
				var sheet: Dictionary = game["sheets"][node_spec["sheet"]]
				var picture := _sprite(_texture(sheet), sheet["tile"], int(node_spec["frame"]))
				picture.position = Vector2(node_spec["x"], node_spec["y"])
				Q.apply_gd(picture, node_spec.get("gd"))
				scene.add_child(picture)
			"exit":
				var exit := Exit.new()
				exit.setup(node_spec, scene)
				Q.apply_gd(exit, node_spec.get("gd"))
				scene.add_child(exit)
				exits[node_spec["name"]] = exit
			"camera":
				var cam := Camera2D.new()
				cam.name = "Camera"
				cam.position_smoothing_enabled = false
				if node_spec.get("bounds", "tilemap") == "tilemap" and tilemap != null:
					var size: Vector2 = tilemap.pixel_size()
					cam.limit_left = 0
					cam.limit_top = 0
					cam.limit_right = int(size.x)
					cam.limit_bottom = int(size.y)
				Q.apply_gd(cam, node_spec.get("gd"))
				var target: Node = characters.get(node_spec["follow"])
				if target != null:
					target.add_child(cam)
				else:
					scene.add_child(cam)
				scene.q_camera = cam
			"menu":
				var menu := Menu.new()
				menu.setup(node_spec, scene)
				Q.apply_gd(menu, node_spec.get("gd"))
				scene.add_child(menu)
				# the pointer is the player's qg:cursor; without one, a hidden one that only follows the mouse
				var has_cursor := false
				for other in scene_spec["nodes"]:
					if other["kind"] == "cursor" and int(other.get("player", 1)) == int(node_spec.get("player", 1)):
						has_cursor = true
				if not has_cursor:
					var pointer := Cursor.new()
					pointer.setup({"player": node_spec.get("player", 1), "step": 0.0}, scene)
					scene.add_child(pointer)
			"dialogue":
				var box := Dialogue.new()
				box.setup(node_spec, scene)
				scene.add_child(box)
			"hud":
				var hud := Hud.new()
				hud.setup(node_spec, scene)
				Q.apply_gd(hud, node_spec.get("gd"))
				scene.add_child(hud)
	# Arriving through an exit: the character stands in the exit it was
	# sent to, which stays disarmed until it walks out of it.
	var arrive_at = G.get("_q_arrive_at")
	if arrive_at != null and arrive_at != "" and exits.has(arrive_at):
		for c in characters.values():
			if c is CharacterBody2D:
				c.position = exits[arrive_at].position
		exits[arrive_at].disarm()
	G.set("_q_arrive_at", "")
	return scene


# A prefab instance in the scene; qg:instance, qg:spawn and qg:swap use it.
# From a collision handler (deferred), the node joins the tree at the end
# of the frame: physics refuses new shapes while it reports touches.
static func instance(game: Dictionary, scene: Node, prefab_name: String, at: Vector2,
		deferred: bool = false) -> Node2D:
	var prefab: Dictionary = game["prefabs"][prefab_name]
	var sheet: Dictionary = game["sheets"][prefab["sheet"]]
	var thing: Node2D
	if prefab.get("ai") == "shuttle":
		thing = Shuttle.new()
	elif prefab.get("ai") != null:
		thing = Thing.new()
	elif prefab.get("solid", false):
		thing = Block.new()
	else:
		thing = Item.new()
	thing.setup(prefab_name, prefab, _texture(sheet), sheet["tile"])
	thing.position = at
	Q.apply_gd(thing, prefab.get("gd"))
	if deferred:
		scene.call_deferred("add_child", thing)
	else:
		scene.add_child(thing)
	return thing


static func _character(node_spec: Dictionary, game: Dictionary, scene: Node) -> CharacterBody2D:
	var body: CharacterBody2D
	if node_spec["controller"] == "topdown":
		body = TopdownBody.new()
	elif node_spec["controller"] == "ship":
		body = ShipBody.new()
	elif node_spec["controller"] == "fighter":
		body = FighterBody.new()
	elif node_spec["controller"] == "grid":
		body = GridBody.new()
	else:
		body = PlatformerBody.new()
	body.name = node_spec["id"]
	body.collision_layer = 1
	body.collision_mask = 1
	body.add_to_group("q_named")
	body.position = Vector2(node_spec["x"], node_spec["y"])
	body.setup(node_spec)
	var sheet: Dictionary = game["sheets"][node_spec["sheet"]]
	var sprite := _sprite(_texture(sheet), sheet["tile"], int(node_spec["frame"]))
	sprite.scale = Vector2.ONE * float(node_spec.get("scale", 1.0))
	body.add_child(sprite)
	var shape := CollisionShape2D.new()
	shape.name = "Shape"
	var rect := RectangleShape2D.new()
	rect.size = Vector2(node_spec["hitbox"][0], node_spec["hitbox"][1])
	shape.shape = rect
	body.add_child(shape)
	# What it touches: an Area2D two pixels larger each side, so a solid
	# thing the body rests on or bumps (which it cannot overlap) is seen.
	var sensor := Area2D.new()
	sensor.name = "Sensor"
	sensor.monitorable = false
	var sensor_shape := CollisionShape2D.new()
	sensor_shape.name = "Shape"
	var sensor_rect := RectangleShape2D.new()
	sensor_rect.size = rect.size + Vector2(4, 4)
	sensor_shape.shape = sensor_rect
	sensor.add_child(sensor_shape)
	body.add_child(sensor)
	body.wire(sensor, node_spec, scene, sprite)
	return body


static func _sprite(texture: Texture2D, tile: Array, frame: int) -> Sprite2D:
	var sprite := Sprite2D.new()
	sprite.name = "Sprite"
	sprite.texture = texture
	sprite.hframes = max(1, int(texture.get_width()) / int(tile[0]))
	sprite.vframes = max(1, int(texture.get_height()) / int(tile[1]))
	sprite.frame = frame
	return sprite


static func forget_textures() -> void:
	_textures.clear()


static func _texture(sheet: Dictionary) -> Texture2D:
	var src: String = sheet["src"]
	if _textures.has(src):
		return _textures[src]
	var texture := Q.texture(src)
	if texture == null:
		push_error("quantum: cannot load the image " + src)
		var image := Image.create(16, 16, false, Image.FORMAT_RGBA8)
		image.fill(Color.MAGENTA)
		texture = ImageTexture.create_from_image(image)
	_textures[src] = texture
	return texture
