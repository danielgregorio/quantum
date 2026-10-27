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
const Picture := preload("res://addons/quantum/picture.gd")
const Shuttle := preload("res://addons/quantum/shuttle.gd")
const Timer_ := preload("res://addons/quantum/timer.gd")
const Hud := preload("res://addons/quantum/hud.gd")
const Tilemap := preload("res://addons/quantum/tilemap.gd")
const Zone := preload("res://addons/quantum/zone.gd")
const Cursor := preload("res://addons/quantum/cursor.gd")
const Looks := preload("res://addons/quantum/looks.gd")
const FighterBody := preload("res://addons/quantum/fighter_body.gd")
const Menu := preload("res://addons/quantum/menu.gd")
const GridBody := preload("res://addons/quantum/grid_body.gd")
const PointerBody := preload("res://addons/quantum/pointer_body.gd")
const Dialogue := preload("res://addons/quantum/dialogue.gd")
const BehaviorBody := preload("res://addons/quantum/behavior_body.gd")
const Camera := preload("res://addons/quantum/camera.gd")

static var _textures: Dictionary = {}
const OVERLAY_LAYER := 50   # a qg:overlay's canvas layers go this far above the scene's (HUD 1, menus 10, touch 30)


static func build(game: Dictionary, scene_spec: Dictionary) -> Node2D:
	var scene: Node2D = QuantumScene.new()
	scene.set_script(load(scene_spec["script"]))
	scene.q_spec = scene_spec
	scene.q_game = game
	scene.q_seed = int(scene_spec.get("seed", 0))
	Q.make_buses(game.get("buses", []))
	Q.load_sounds(game.get("sounds", {}))
	Q.particles_spec = game.get("particles", {})

	var bg := ColorRect.new()
	bg.name = "Background"
	bg.color = Color(scene_spec.get("background", "#000000"))
	bg.size = Vector2(16384, 16384)
	bg.position = Vector2(-8192, -8192)
	bg.z_index = -100
	var over: bool = scene_spec.has("overlay")
	if over:
		# a qg:overlay: its background is a shade over the scene under it, on a layer above that scene's own
		var shade := CanvasLayer.new()
		shade.name = "Shade"
		shade.layer = OVERLAY_LAYER
		bg.color.a = float(scene_spec["overlay"].get("shade", 0.6))
		bg.mouse_filter = Control.MOUSE_FILTER_STOP   # a click on the shade does not reach the scene under it
		shade.add_child(bg)
		scene.add_child(shade)
	else:
		scene.add_child(bg)
	# y-sort="true": what stands lower is drawn in front (the tilemap stays under all of it)
	scene.y_sort_enabled = bool(scene_spec.get("y_sort", false))
	var clock: Node = load("res://addons/quantum/clock.gd").new()
	clock.name = "Clock"   # the scene's ticks, its qg:afters and qg:whens, stepped first (clock.gd)
	scene.add_child(clock)
	var tweens: Node = load("res://addons/quantum/tween.gd").new()
	tweens.name = "Tweens"   # the scene's qg:tweens, stepped before its things (tween.gd)
	scene.add_child(tweens)

	scene.q_on_input = scene_spec.get("on_input", {})
	scene.q_on_select = scene_spec.get("on_select", {})
	Q.apply_gd(scene, scene_spec.get("gd"))
	scene.q_on_death = scene_spec.get("on_death", {})
	scene.q_on_release = scene_spec.get("on_release", {})
	scene.q_sequences = scene_spec.get("sequences", [])
	scene.q_on_event = scene_spec.get("on_event", {})
	scene.q_on_refused = scene_spec.get("on_refused", [])
	scene.q_on_screen = scene_spec.get("on_screen", [])
	if scene_spec.get("ambient") != null:   # a dark scene: what no qg:light reaches is this colour
		var dark := CanvasModulate.new()
		dark.name = "Ambient"
		dark.color = Color(str(scene_spec["ambient"]))
		scene.add_child(dark)
	var tilemap: Node = null
	var characters: Dictionary = {}
	var exits: Dictionary = {}
	var cameras: Array = []
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
				tilemap = Tilemap.build(node_spec, game["sheets"][node_spec["tileset"]], _texture, game["sheets"])
				if scene.y_sort_enabled:
					tilemap.z_index = -10
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
					_animation_ends(walker, node_spec, scene)
					Q.apply_gd(walker, node_spec.get("gd"))
					characters[node_spec["id"]] = walker
					scene.add_child(walker)
				else:
					if node_spec.get("if") != null and not scene.call(node_spec["if"]):
						continue
					var body := _character(node_spec, game, scene)
					_animation_ends(body, node_spec, scene)
					looks(body, node_spec, game, scene)
					if node_spec.get("on_screen") != null:
						body.set_meta("q_on_screen", node_spec["on_screen"])
					Q.apply_gd(body, node_spec.get("gd"))
					characters[node_spec["id"]] = body
					scene.add_child(body)
			"instance":
				if node_spec.get("if") != null and not scene.call(node_spec["if"]):
					continue
				if node_spec.get("name") != null and Q.gone(str(scene_spec["name"]), str(node_spec["name"])):
					continue   # picked up or opened before: it stays gone
				var made := instance(game, scene, node_spec["prefab"], Vector2(node_spec["x"], node_spec["y"]))
				if node_spec.get("name") != null:
					made.name = node_spec["name"]
					made.set_meta("q_named", true)
				if node_spec.get("state") != null and made.has_method("become"):
					made.become(str(node_spec["state"]))   # a Tiled object's state property
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
				if node_spec.get("id") != null:
					cursor.name = node_spec["id"]   # read by its id: aim.x
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
			"parallax":
				# Parallax2D: scroll 0 stays on the screen, 1 moves with the level; it keeps the
				# screen's top, so a camera that rises or falls does not move it up or down
				var sheet: Dictionary = game["sheets"][node_spec["sheet"]]
				var back := Parallax2D.new()
				back.scroll_scale = Vector2(float(node_spec.get("scroll", 0.0)), 0.0)
				back.z_index = -90
				var picture := _sprite(_texture(sheet), sheet["tile"], int(node_spec["frame"]))
				picture.centered = false
				picture.position = Vector2(0, float(node_spec.get("y", 0.0)))
				back.add_child(picture)
				if node_spec.get("repeat", true):
					back.repeat_size = Vector2(float(sheet["tile"][0]), 0)
					back.repeat_times = 3
				Q.apply_gd(back, node_spec.get("gd"))
				scene.add_child(back)
			"sprite":
				var sheet: Dictionary = game["sheets"][node_spec["sheet"]]
				var picture := _sprite(_texture(sheet), sheet["tile"], int(node_spec["frame"]))
				picture.position = Vector2(node_spec["x"], node_spec["y"])
				if node_spec.get("frame_method") != null:
					picture.set_script(Picture)
					picture.follow(scene, node_spec["frame_method"])
				Q.apply_gd(picture, node_spec.get("gd"))
				scene.add_child(picture)
			"light":
				var light := PointLight2D.new()
				light.set_script(load("res://addons/quantum/light.gd"))
				light.setup(node_spec)
				light.position = Vector2(node_spec["x"], node_spec["y"])
				scene.add_child(light)
			"emitter":
				var fx: CPUParticles2D = load("res://addons/quantum/particles.gd").make(
					game["particles"][node_spec["particles"]], float(node_spec.get("width", 0.0)))
				fx.one_shot = false
				fx.position = Vector2(node_spec["x"], node_spec["y"])
				Q.apply_gd(fx, node_spec.get("gd"))
				scene.add_child(fx)
			"exit":
				var exit := Exit.new()
				exit.setup(node_spec, scene)
				Q.apply_gd(exit, node_spec.get("gd"))
				scene.add_child(exit)
				exits[node_spec["name"]] = exit
			"camera":
				cameras.append(node_spec)   # made last: where its characters stand, after an arrival
			"mirror":
				var mirror: Node2D = load("res://addons/quantum/mirror.gd").new()
				mirror.setup(node_spec, scene, game)
				scene.add_child(mirror)
				scene.q_mirrors.append(mirror)
			"label":
				if node_spec.get("if") != null and not scene.call(node_spec["if"]):
					continue
				var label: Node2D = Looks.new()
				label.position = Vector2(node_spec["x"], node_spec["y"])
				label.setup({"labels": [{"method": node_spec["method"], "size": node_spec.get("size", 8),
					"color": node_spec.get("color", "#ffffff")}]}, scene, game)
				Q.apply_gd(label, node_spec.get("gd"))
				scene.add_child(label)
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
	if over:
		for c in scene.get_children():
			if c is CanvasLayer and c.name != "Shade":
				c.layer += OVERLAY_LAYER   # its HUD, menus and dialogues over the shade
		return scene
	# on a touch screen: the game's buttons and sticks, and this scene's
	var touch: Array = game.get("touch", []) + scene_spec.get("touch", [])
	if not touch.is_empty():
		var pads = load("res://addons/quantum/touch.gd").new()
		pads.setup(touch)
		scene.add_child(pads)
	# Arriving through an exit: the character stands in the exit it was
	# sent to, which stays disarmed until it walks out of it.
	var arrive_at = G.get("_q_arrive_at")
	if arrive_at != null and arrive_at != "" and exits.has(arrive_at):
		for c in characters.values():
			if c is CharacterBody2D:
				c.position = exits[arrive_at].position
		exits[arrive_at].disarm()
	G.set("_q_arrive_at", "")
	for e in exits.values():   # nor does starting in one (a door the room starts at)
		for c in characters.values():
			if c is CharacterBody2D and e.holds(c.position):
				e.disarm()
	var by_player := []   # qg:camera player=: a view each (split.gd)
	for node_spec in cameras:
		var cam := Camera.new()
		cam.setup(node_spec, characters)
		if "me" in node_spec.get("follow", []):
			cam.set_meta("q_follow_me", true)   # the player's entity in the world: its mirror gives it the node
		cam.scene_node = scene
		if node_spec.get("bounds", "tilemap") == "tilemap" and tilemap != null:
			var size: Vector2 = tilemap.pixel_size()
			cam.limit_left = 0
			cam.limit_top = 0
			cam.limit_right = int(size.x)
			cam.limit_bottom = int(size.y)
		Q.apply_gd(cam, node_spec.get("gd"))
		if node_spec.get("player") != null:
			cam.player = int(node_spec["player"])
			if cam.targets.is_empty():
				cam.free()   # it follows no one here: a player who is not playing has no view
			else:
				by_player.append(cam)
			continue
		scene.add_child(cam)
		scene.q_camera = cam
	if not by_player.is_empty():
		var split: CanvasLayer = load("res://addons/quantum/split.gd").new()
		var screen := Vector2(float(scene_spec.get("width", 256)), float(scene_spec.get("height", 224)))
		scene.q_camera = split.build(scene, by_player, screen, Q.net_player() if Q.external_input else 0)
		scene.q_views = split.views
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
	looks(thing, prefab, game, P)
	if prefab.get("on_screen") != null:
		thing.set_meta("q_on_screen", prefab["on_screen"])
	var hitbox: Node = thing if thing is Area2D else thing.get_node_or_null("Hitbox")   # an item is its own area
	if prefab.get("on_separate") != null and hitbox is Area2D:
		Q.watch_separate(hitbox, thing, prefab["on_separate"], P)
	if deferred:   # made by the game as it runs (qg:spawn), not placed with the scene
		Q.event("spawn", {"what": str(prefab.get("tag", prefab_name)), "x": snappedf(at.x, 0.1), "y": snappedf(at.y, 0.1)})
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
	elif node_spec["controller"] == "pointer":
		body = PointerBody.new()
	elif node_spec["controller"] == "behavior":
		body = BehaviorBody.new()
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
	if node_spec.get("on_separate") != null:
		Q.watch_separate(sensor, body, node_spec["on_separate"], scene)
	return body


# How a character or a thing looks besides its frame: upside down (flip-v=), its draw layer
# (layer=), and what a Looks node keeps up every tick (labels, visible=, particles=, trail=, lights).
static func looks(node: Node2D, spec: Dictionary, game: Dictionary, caller: Object) -> void:
	var sprite = node.get_node_or_null("Sprite")
	if spec.get("flip_v", false) and sprite is Sprite2D:
		sprite.flip_v = true
	if spec.get("layer") != null:
		node.z_index = int(spec["layer"])
	for key in ["labels", "bars", "visible", "particles", "trail", "lights"]:
		if spec.get(key) != null:
			var keeper: Node2D = Looks.new()
			keeper.setup(spec, caller, game, node)
			node.add_child(keeper)
			return


# A character's qg:on-animation-end handlers, which are the scene's.
static func _animation_ends(body: Node, node_spec: Dictionary, scene: Node) -> void:
	var animator = body.get_node_or_null("Animator")
	if animator != null:
		animator.ends = node_spec.get("on_animation_end", [])
		animator.caller = scene


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
	var src := Q.src_of(sheet)   # the language's own picture, when it has one (qg:asset)
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
