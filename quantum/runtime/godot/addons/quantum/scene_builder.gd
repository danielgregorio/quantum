extends RefCounted
# Builds a scene's node tree from its entry in game.json.
#
# Textures are loaded from the image files themselves (Image.load_from_file),
# not through Godot's import, so a headless run needs no import step and the
# same files serve the editor, the replay and the export.

const QuantumScene := preload("res://addons/quantum/quantum_scene.gd")
const PlatformerBody := preload("res://addons/quantum/platformer_body.gd")
const Item := preload("res://addons/quantum/item.gd")
const Thing := preload("res://addons/quantum/thing.gd")
const Block := preload("res://addons/quantum/block.gd")
const Hud := preload("res://addons/quantum/hud.gd")
const Tilemap := preload("res://addons/quantum/tilemap.gd")

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

	var tilemap: Node = null
	var characters: Dictionary = {}
	for node_spec in scene_spec["nodes"]:
		match node_spec["kind"]:
			"tilemap":
				tilemap = Tilemap.build(node_spec, game["sheets"][node_spec["tileset"]], _texture)
				scene.add_child(tilemap)
				scene.q_fall_y = tilemap.pixel_size().y + 64.0
			"character":
				var body := _character(node_spec, game, scene)
				characters[node_spec["id"]] = body
				scene.add_child(body)
			"instance":
				instance(game, scene, node_spec["prefab"], Vector2(node_spec["x"], node_spec["y"]))
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
				var target: Node = characters.get(node_spec["follow"])
				if target != null:
					target.add_child(cam)
				else:
					scene.add_child(cam)
				scene.q_camera = cam
			"hud":
				var hud := Hud.new()
				hud.setup(node_spec, scene)
				scene.add_child(hud)
	return scene


# A prefab instance in the scene; qg:instance, qg:spawn and qg:swap use it.
# From a collision handler (deferred), the node joins the tree at the end
# of the frame: physics refuses new shapes while it reports touches.
static func instance(game: Dictionary, scene: Node, prefab_name: String, at: Vector2,
		deferred: bool = false) -> Node2D:
	var prefab: Dictionary = game["prefabs"][prefab_name]
	var sheet: Dictionary = game["sheets"][prefab["sheet"]]
	var thing: Node2D
	if prefab.get("ai") != null:
		thing = Thing.new()
	elif prefab.get("solid", false):
		thing = Block.new()
	else:
		thing = Item.new()
	thing.setup(prefab_name, prefab, _texture(sheet), int(sheet["tile"]))
	thing.position = at
	if deferred:
		scene.call_deferred("add_child", thing)
	else:
		scene.add_child(thing)
	return thing


static func _character(node_spec: Dictionary, game: Dictionary, scene: Node) -> CharacterBody2D:
	var body := PlatformerBody.new()
	body.name = node_spec["id"]
	body.collision_layer = 1
	body.collision_mask = 1
	body.add_to_group("q_named")
	body.position = Vector2(node_spec["x"], node_spec["y"])
	body.setup(node_spec)
	var sheet: Dictionary = game["sheets"][node_spec["sheet"]]
	var sprite := _sprite(_texture(sheet), int(sheet["tile"]), int(node_spec["frame"]))
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


static func _sprite(texture: Texture2D, tile: int, frame: int) -> Sprite2D:
	var sprite := Sprite2D.new()
	sprite.name = "Sprite"
	sprite.texture = texture
	sprite.hframes = max(1, int(texture.get_width()) / tile)
	sprite.vframes = max(1, int(texture.get_height()) / tile)
	sprite.frame = frame
	return sprite


static func _texture(sheet: Dictionary) -> Texture2D:
	var src: String = sheet["src"]
	if _textures.has(src):
		return _textures[src]
	var image := Image.load_from_file(ProjectSettings.globalize_path("res://" + src))
	if image == null:
		push_error("quantum: cannot load the image " + src)
		image = Image.create(16, 16, false, Image.FORMAT_RGBA8)
		image.fill(Color.MAGENTA)
	var texture := ImageTexture.create_from_image(image)
	_textures[src] = texture
	return texture
